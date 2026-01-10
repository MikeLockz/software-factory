# Implementation Engineer

> **Goal:** Generate actual code implementations based on approved contracts using Claude Code CLI as a super-powered coding tool.

The Implementation Engineer leverages Claude Code CLI in **headless mode** as its primary implementation engine, enabling autonomous code generation with full file system access, validation, and self-correction capabilities.

---

## Overview

```mermaid
graph LR
    Contract[Approved Contract] --> Impl[Implementation Engineer]
    Impl --> |Claude Code CLI| CC[claude -p ...]
    CC --> |Reads/Writes Files| FS[File System]
    CC --> |Runs Commands| Bash[make lint/test]
    FS --> Reviewer[Review Board]
```

---

## 1. Claude Code CLI Super Tool

### 1.1 Why Claude Code CLI?

Instead of generating JSON-formatted code and manually writing files, the Implementation Engineer uses Claude Code CLI as a **super tool** that can:

- **Read and write files directly** - No JSON parsing or file writer utilities needed
- **Run validation commands** - Execute `make lint`, `make test`, etc. natively
- **Self-correct in real-time** - Fix errors as they encounter them
- **Understand project context** - Reads existing codebase automatically

### 1.2 Headless Mode Basics

```bash
# Basic usage
claude -p "Implement the user authentication endpoint from the contract"

# With allowed tools (auto-approve file operations)
claude -p "..." --allowedTools "Read,Edit,Bash"

# JSON output for structured responses
claude -p "..." --output-format json

# Streaming output for real-time progress
claude -p "..." --output-format stream-json
```

---

## 2. Implementation Engineer Node

### 2.1 Create the Node

Create `agent/nodes/implementation_engineer.py`:

```python
import subprocess
import json
from typing import Optional
from agent.state import AgentState

def run_claude_code(
    prompt: str,
    working_dir: str,
    allowed_tools: list[str] = ["Read", "Edit", "Bash"],
    output_format: str = "json"
) -> dict:
    """Execute Claude Code CLI in headless mode."""
    cmd = [
        "claude",
        "-p", prompt,
        "--allowedTools", ",".join(allowed_tools),
        "--output-format", output_format
    ]
    
    result = subprocess.run(
        cmd,
        cwd=working_dir,
        capture_output=True,
        text=True,
        timeout=300  # 5 minute timeout
    )
    
    if output_format == "json":
        return json.loads(result.stdout)
    
    return {"output": result.stdout, "error": result.stderr}


BACKEND_PROMPT = """You are implementing a backend feature for a FastAPI/Python application.

## Contract
{contract}

## Task
{task}

## Instructions
1. Read the existing codebase structure to understand patterns
2. Create Pydantic models matching the contract
3. Implement FastAPI router with CRUD endpoints
4. Add database operations using SQLAlchemy/async
5. Include proper validation and error handling
6. Run `make lint` to validate your code
7. Fix any linting errors before completing

Write all files to the appropriate locations based on project structure.
Report what files you created/modified when complete.
"""

FRONTEND_PROMPT = """You are implementing a frontend feature for a React/TypeScript application.

## Contract
{contract}

## Task
{task}

## Instructions
1. Read the existing codebase structure to understand patterns
2. Create TypeScript interfaces matching the contract
3. Build React components with proper typing
4. Implement API client hooks (React Query style)
5. Add form handling with validation
6. Include loading and error states
7. Run `pnpm lint` to validate your code
8. Fix any linting errors before completing

Write all files to the appropriate locations based on project structure.
Report what files you created/modified when complete.
"""


def implementation_engineer_node(state: AgentState) -> dict:
    """Generate code using Claude Code CLI as a super tool."""
    mode = state.get("implementation_engineer_mode", "BACKEND")
    contract = state.get("current_contract", "{}")
    work_item = state.get("current_work_item")
    task = work_item.description if work_item else state.get("task_description", "")
    working_dir = state.get("workspace_path", ".")
    
    # Select prompt based on mode
    prompt_template = BACKEND_PROMPT if mode == "BACKEND" else FRONTEND_PROMPT
    prompt = prompt_template.format(contract=contract, task=task)
    
    # Run Claude Code CLI
    result = run_claude_code(
        prompt=prompt,
        working_dir=working_dir,
        allowed_tools=["Read", "Edit", "Bash", "Write"]
    )
    
    return {
        "claude_code_result": result,
        "status": "implementation_ready"
    }
```

---

## 3. Tool Configuration

### 3.1 Allowed Tools Matrix

| Tool | Purpose | Risk Level |
|------|---------|------------|
| `Read` | Read files and directories | Safe |
| `Edit` | Modify existing files | Medium |
| `Write` | Create new files | Medium |
| `Bash` | Execute shell commands | High |

### 3.2 Secure Configuration

For production use with restricted permissions:

```python
def run_claude_code_restricted(prompt: str, working_dir: str) -> dict:
    """Run Claude Code with restricted tool access."""
    return run_claude_code(
        prompt=prompt,
        working_dir=working_dir,
        # Only allow read and edit, no bash for security
        allowed_tools=["Read", "Edit"],
        output_format="json"
    )
```

### 3.3 Full Autonomy Configuration

For trusted environments:

```python
def run_claude_code_autonomous(prompt: str, working_dir: str) -> dict:
    """Run Claude Code with full autonomy."""
    return run_claude_code(
        prompt=prompt,
        working_dir=working_dir,
        allowed_tools=["Read", "Edit", "Write", "Bash", "mcp__github__*"],
        output_format="stream-json"
    )
```

---

## 4. Self-Correction Loop

### 4.1 Validation Feedback Handler

Claude Code CLI handles self-correction natively by running validation commands. However, for explicit correction loops:

```python
CORRECTION_PROMPT = """You previously attempted to implement code but there were issues.

## Original Task
{task}

## Validation/Review Errors
{errors}

## Instructions
1. Read the current state of the files
2. Identify what caused the errors
3. Fix the issues
4. Run validation again to confirm fixes
5. Report what you changed

Do not stop until all errors are resolved.
"""

def implementation_engineer_correction_node(state: AgentState) -> dict:
    """Fix code based on validation or review feedback."""
    errors = state.get("validation_errors") or state.get("review_concerns", [])
    task = state.get("task_description", "")
    working_dir = state.get("workspace_path", ".")
    
    prompt = CORRECTION_PROMPT.format(task=task, errors=errors)
    
    result = run_claude_code(
        prompt=prompt,
        working_dir=working_dir,
        allowed_tools=["Read", "Edit", "Bash"]
    )
    
    return {
        "claude_code_result": result,
        "correction_count": state.get("correction_count", 0) + 1,
        "status": "implementation_ready"
    }
```

---

## 5. Graph Integration

```python
from agent.nodes.implementation_engineer import implementation_engineer_node, implementation_engineer_correction_node

def validation_node(state: AgentState) -> dict:
    """Check if Claude Code completed successfully."""
    result = state.get("claude_code_result", {})
    
    # Check for errors in the Claude Code output
    if result.get("error"):
        return {
            "validation_status": "failed",
            "validation_errors": result.get("error"),
            "status": "needs_correction"
        }
    
    return {"validation_status": "passed", "status": "reviewing"}

# In build_graph():
workflow.add_node("implementation_engineer", implementation_engineer_node)
workflow.add_node("validation", validation_node)
workflow.add_node("implementation_engineer_correction", implementation_engineer_correction_node)

workflow.add_edge("implementation_engineer", "validation")

workflow.add_conditional_edges(
    "validation",
    lambda s: s["validation_status"],
    {
        "passed": "security_engineer",  # Continue to review
        "failed": "implementation_engineer_correction"
    }
)

# Correction loops back to validation
workflow.add_edge("implementation_engineer_correction", "validation")
```

---

## 6. Mode Switching

The Stack Manager sets the mode:

```python
def stack_manager_node(state: AgentState) -> dict:
    current_item = state.get("current_work_item")
    
    # Set mode based on work item type
    mode = {
        "CONTRACT": "CONTRACT",  # Uses contractor node
        "BACKEND": "BACKEND",
        "FRONTEND": "FRONTEND"
    }.get(current_item.type, "BACKEND")
    
    return {
        "implementation_engineer_mode": mode,
        # ... other state updates
    }
```

---

## 7. Output Formats

### 7.1 JSON Output (Recommended for Automation)

```bash
claude -p "..." --output-format json
```

Returns:

```json
{
  "result": "Implementation complete. Created 3 files...",
  "session_id": "abc123",
  "metadata": {
    "files_modified": ["src/models/user.py", "src/routers/user.py"],
    "commands_run": ["make lint"]
  }
}
```

### 7.2 Stream-JSON Output (For Real-Time Progress)

```bash
claude -p "..." --output-format stream-json
```

Returns newline-delimited JSON for real-time streaming:

```json
{"type": "thinking", "content": "Reading the contract..."}
{"type": "tool_use", "tool": "Read", "path": "src/models/"}
{"type": "tool_use", "tool": "Write", "path": "src/models/user.py"}
{"type": "result", "content": "Implementation complete."}
```

---

## 8. Advanced: Chaining with Other CLIs

Claude Code can be piped with other command-line tools:

```bash
# Pipe git diff into Claude for review
git diff | claude -p "Review these changes for issues"

# Pipe Claude's output to other tools
claude -p "Generate SQL migration" --output-format text | psql
```

---

## 9. Environment Setup

### 9.1 Prerequisites

```bash
# Install Claude Code CLI
npm install -g @anthropic-ai/claude-code

# Authenticate
claude auth login
```

### 9.2 Configuration in Docker

```dockerfile
# Install Claude Code CLI in container
RUN npm install -g @anthropic-ai/claude-code

# Set API key via environment
ENV ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
```

---

## 10. Benefits Over Manual LLM Integration

| Aspect | Manual LLM | Claude Code CLI |
|--------|-----------|-----------------|
| File Operations | Parse JSON, write manually | Native file access |
| Validation | Separate subprocess calls | Built-in via Bash tool |
| Self-Correction | Custom retry logic | Automatic within session |
| Context | Manual file reading | Automatic codebase scan |
| Complexity | High (100+ LOC) | Low (~20 LOC) |
