# Prompt Engineering Guide

> **Goal:** Consistent, reliable prompts that produce structured, parseable output.

---

## Core Principles

1. **Be explicit** — State exactly what format you expect
2. **Provide examples** — Show don't tell
3. **Set boundaries** — Define what NOT to do
4. **Handle edge cases** — Instruct on ambiguous inputs

---

## 1. Prompt Template Structure

```python
PROMPT_TEMPLATE = """[ROLE]: Who is the agent?

[CONTEXT]: What are they working on?
{context_variables}

[TASK]: What should they do?

[CONSTRAINTS]: What are the rules/limits?

[OUTPUT FORMAT]: Exact expected output structure

[EXAMPLES]: (Optional) Input/output pairs
"""
```

---

## 2. Structured Output Patterns

### 2.1 JSON Output

Always be explicit about JSON structure:

```python
# ❌ Bad - vague
"Return a JSON object with the results"

# ✅ Good - explicit
"""Output ONLY valid JSON (no markdown, no explanation):
{
  "field1": "type and description",
  "field2": "type and description"
}"""
```

### 2.2 Handling Markdown Wrapping

LLMs often wrap JSON in code blocks. Always strip:

```python
import re

def clean_json_response(content: str) -> str:
    """Remove markdown code blocks from LLM output."""
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\n?", "", content)
        content = re.sub(r"\n?```$", "", content)
    return content
```

---

## 3. Prompt Patterns by Agent

### 3.1 Generator Pattern (Contractor, Coder)

```python
GENERATOR_PROMPT = """You are a {role}.

Input:
{input}

Requirements:
- Requirement 1
- Requirement 2

Generate {output_type} following this exact schema:
{schema}

Output raw JSON only. No explanations.
"""
```

### 3.2 Reviewer Pattern (Security, Compliance)

```python
REVIEWER_PROMPT = """You are a {role} reviewing {artifact_type}.

Artifact:
{artifact}

Check for:
1. Check item 1
2. Check item 2

Respond with JSON:
{
  "approved": boolean,
  "concerns": ["list of issues"],
  "suggestions": ["list of improvements"]
}

Guidelines:
- Approve if no CRITICAL issues
- Suggestions don't block approval
- Be specific about line numbers/fields
"""
```

### 3.3 Decider Pattern (Supervisor, Stack Manager)

```python
DECIDER_PROMPT = """You are deciding the next action.

Current state:
{state}

Options:
1. Option A - when to choose
2. Option B - when to choose

Respond with a single word: "OPTION_A" or "OPTION_B"
"""
```

---

## 4. Temperature Guidelines

| Agent Type | Temperature | Rationale |
|------------|-------------|-----------|
| Generators | 0.0-0.3 | Need consistent, reproducible output |
| Reviewers | 0.0 | Must be deterministic |
| PM/Creative | 0.3-0.7 | Benefit from variation |

---

## 5. Handling Edge Cases

### 5.1 Empty/Null Inputs

```python
PROMPT = """...
If the input is empty or unclear, respond with:
{
  "error": "description of what's missing",
  "needs": ["list of required information"]
}
"""
```

### 5.2 Too Large Inputs

```python
# Truncate with notice
def prepare_context(content: str, max_chars: int = 8000) -> str:
    if len(content) <= max_chars:
        return content
    return content[:max_chars] + "\n\n[TRUNCATED - showing first 8000 chars]"
```

### 5.3 Conflicting Requirements

```python
PROMPT = """...
If requirements conflict, prioritize in this order:
1. Security
2. Correctness  
3. Performance
4. Style

Note any tradeoffs in the "notes" field.
"""
```

---

## 6. Prompt Versioning

### 6.1 Store Prompts as Files

```
agent/
└── prompts/
    ├── v1/
    │   ├── contractor.txt
    │   └── security.txt
    └── v2/
        ├── contractor.txt
        └── security.txt
```

### 6.2 Load by Version

```python
import os
from pathlib import Path

PROMPT_VERSION = os.getenv("PROMPT_VERSION", "v2")

def load_prompt(name: str) -> str:
    path = Path(__file__).parent / "prompts" / PROMPT_VERSION / f"{name}.txt"
    return path.read_text()
```

---

## 7. Debugging Prompts

### 7.1 Logging

```python
import logging

logger = logging.getLogger("prompts")

def invoke_with_logging(llm, prompt: str, context: dict):
    logger.debug(f"Prompt:\n{prompt[:500]}...")
    response = llm.invoke(prompt)
    logger.debug(f"Response:\n{response.content[:500]}...")
    return response
```

### 7.2 Prompt Playground

Create `agent/tools/prompt_playground.py`:

```python
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

def test_prompt(prompt: str, model: str = "gpt-4o"):
    """Quick prompt testing."""
    llm = ChatOpenAI(model=model, temperature=0)
    response = llm.invoke(prompt)
    print(response.content)
    return response.content

if __name__ == "__main__":
    test_prompt("""
    You are a security reviewer.
    Review this contract: {"name": "User", "fields": {"email": "str"}}
    Output JSON with approved (bool) and concerns (list).
    """)
```

---

## 8. Common Mistakes

| Mistake | Problem | Fix |
|---------|---------|-----|
| "Return JSON" | May include markdown | "Output raw JSON only, no markdown" |
| No error handling | Crashes on bad output | Parse with try/except, return defaults |
| Vague criteria | Inconsistent approvals | List specific, testable checks |
| Long prompts | Context overflow | Split into focused sub-prompts |
| No examples | Ambiguous format | Include 1-2 input/output examples |
