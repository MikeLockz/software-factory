# Error Handling & Recovery

> **Goal:** Graceful degradation, automatic recovery, and clear failure reporting.

---

## 1. Error Categories

| Category | Examples | Recovery Strategy |
|----------|----------|-------------------|
| **Transient** | Rate limits, timeouts | Retry with backoff |
| **Parsing** | Invalid JSON, missing fields | Request correction |
| **Logic** | Max iterations, infinite loops | Fail gracefully |
| **External** | API down, auth failure | Alert and pause |

---

## 2. Retry Logic

### 2.1 Exponential Backoff

Create `agent/tools/retry.py`:

```python
import time
import random
from functools import wraps
from typing import TypeVar, Callable

T = TypeVar("T")

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True
):
    """Decorator for retry with exponential backoff."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        break
                    
                    delay = min(
                        base_delay * (exponential_base ** attempt),
                        max_delay
                    )
                    
                    if jitter:
                        delay *= (0.5 + random.random())
                    
                    time.sleep(delay)
            
            raise last_exception
        
        return wrapper
    return decorator

# Usage
@retry_with_backoff(max_retries=3)
def call_llm(prompt: str):
    return llm.invoke(prompt)
```

### 2.2 Rate Limit Handler

```python
from openai import RateLimitError

def safe_llm_call(llm, prompt: str, fallback: str = None):
    """Call LLM with rate limit handling."""
    try:
        return llm.invoke(prompt)
    except RateLimitError:
        if fallback:
            return fallback
        raise
```

---

## 3. Parsing Recovery

### 3.1 JSON Parsing with Fallbacks

```python
import json
from typing import Optional, Any

def safe_parse_json(content: str, default: Any = None) -> Optional[dict]:
    """Parse JSON with multiple fallback strategies."""
    # Strategy 1: Direct parse
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Strip markdown
    clean = content.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\n?", "", clean)
        clean = re.sub(r"\n?```$", "", clean)
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            pass
    
    # Strategy 3: Find JSON in content
    json_match = re.search(r'\{[\s\S]*\}', content)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    return default
```

### 3.2 Schema Validation

```python
from pydantic import BaseModel, ValidationError

def parse_with_schema(content: str, schema: type[BaseModel]) -> Optional[BaseModel]:
    """Parse JSON and validate against Pydantic schema."""
    data = safe_parse_json(content)
    if not data:
        return None
    
    try:
        return schema(**data)
    except ValidationError as e:
        # Log validation errors for debugging
        logger.warning(f"Schema validation failed: {e}")
        return None
```

---

## 4. Graph Error Handling

### 4.1 Node Error Wrapper

```python
from functools import wraps

def handle_node_errors(func):
    """Wrapper to catch and handle errors in graph nodes."""
    @wraps(func)
    def wrapper(state: AgentState) -> dict:
        try:
            return func(state)
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "error_node": func.__name__,
                "messages": state.get("messages", []) + [f"Error in {func.__name__}: {e}"]
            }
    return wrapper

# Usage
@handle_node_errors
def contractor_node(state: AgentState) -> dict:
    # ... implementation
```

### 4.2 Error Recovery Node

```python
def error_recovery_node(state: AgentState) -> dict:
    """Handle errors and decide recovery strategy."""
    error = state.get("error", "Unknown error")
    error_node = state.get("error_node", "unknown")
    retry_count = state.get("retry_count", 0)
    
    MAX_RETRIES = 2
    
    if retry_count >= MAX_RETRIES:
        # Give up
        return {
            "status": "failed",
            "messages": state.get("messages", []) + [f"Max retries exceeded for {error_node}"]
        }
    
    # Clear error and retry
    return {
        "status": "drafting",
        "error": None,
        "error_node": None,
        "retry_count": retry_count + 1
    }
```

---

## 5. External Service Recovery

### 5.1 Linear API Errors

```python
class LinearAdapter:
    def _query(self, query: str, variables: dict = None) -> dict:
        try:
            response = httpx.post(...)
            response.raise_for_status()
            return response.json()
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Linear API key invalid")
            elif e.response.status_code == 429:
                raise RateLimitError("Linear rate limit exceeded")
            raise
        
        except httpx.ConnectError:
            raise ServiceUnavailableError("Linear API unreachable")
```

### 5.2 Git Operation Recovery

```python
def safe_git_operation(operation: Callable, fallback: Callable = None):
    """Wrap git operations with error handling."""
    try:
        return operation()
    except subprocess.CalledProcessError as e:
        if "already exists" in str(e.stderr):
            # Branch exists, try checkout instead
            if fallback:
                return fallback()
        raise
```

---

## 6. Cleanup & Orphan Management

### 6.1 Branch Cleanup

Create `agent/tools/cleanup.py`:

```python
from agent.tools.git import run_git

def cleanup_orphan_branches(prefix: str = "ai/", age_days: int = 7):
    """Remove old AI-created branches that weren't merged."""
    import datetime
    
    # List remote branches
    success, output = run_git("branch", "-r", "--format=%(refname:short) %(committerdate:iso)")
    if not success:
        return
    
    now = datetime.datetime.now()
    cutoff = now - datetime.timedelta(days=age_days)
    
    for line in output.strip().split("\n"):
        parts = line.split(" ", 1)
        if len(parts) != 2:
            continue
        
        branch, date_str = parts
        if not branch.startswith(f"origin/{prefix}"):
            continue
        
        # Parse date and check age
        branch_date = datetime.datetime.fromisoformat(date_str[:19])
        if branch_date < cutoff:
            # Delete old branch
            run_git("push", "origin", "--delete", branch.replace("origin/", ""))
```

### 6.2 State Cleanup

```python
def cleanup_failed_state(issue_id: str):
    """Clean up state after a failed workflow."""
    # Delete any partial branches
    run_git("fetch", "--prune")
    
    # Update Linear issue
    adapter = LinearAdapter()
    adapter.transition_issue(issue_id, "AI: Failed")
    adapter.add_comment(issue_id, "Workflow failed and was cleaned up.")
```

---

## 7. Alerting

### 7.1 Slack Notifications

```python
import os
import httpx

def send_alert(message: str, severity: str = "warning"):
    """Send alert to Slack."""
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return
    
    emoji = {"info": "ℹ️", "warning": "⚠️", "error": "🚨"}.get(severity, "📢")
    
    httpx.post(webhook_url, json={
        "text": f"{emoji} *Software Factory Alert*\n{message}"
    })

# Usage
try:
    result = app.invoke(state)
except Exception as e:
    send_alert(f"Workflow failed for issue {issue_id}: {e}", "error")
```

---

## 8. Health Checks

```python
def health_check() -> dict:
    """Check health of all external services."""
    checks = {}
    
    # Check OpenAI
    try:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-4o")
        llm.invoke("ping")
        checks["openai"] = "ok"
    except Exception as e:
        checks["openai"] = f"error: {e}"
    
    # Check Linear
    try:
        adapter = LinearAdapter()
        adapter.get_ready_issues("ENG")
        checks["linear"] = "ok"
    except Exception as e:
        checks["linear"] = f"error: {e}"
    
    # Check Git
    success, _ = run_git("status")
    checks["git"] = "ok" if success else "error"
    
    return checks
```
