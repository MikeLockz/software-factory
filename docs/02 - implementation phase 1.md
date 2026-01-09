# Phase 1: The Brain (Local Prototype)

> **Goal:** Validate the "Review Board" concept with a working agent loop.

This guide provides step-by-step instructions to set up the Software Factory in this repository.

---

## Prerequisites

Before starting, ensure you have:

- **Python 3.11+** installed
- **Poetry** or **pip** for dependency management
- An **OpenAI API key** (or Anthropic/other LLM provider)
- **Git** configured with SSH access to your repositories
- A **Linear** account with API access (for Phase 2 integration)

---

## 1. Project Initialization

### 1.1 Create the Agent Directory Structure

```bash
mkdir -p agent/{nodes,tools,config}
touch agent/__init__.py
touch agent/nodes/__init__.py
touch agent/tools/__init__.py
touch agent/config/__init__.py
```

### 1.2 Initialize Python Environment

```bash
cd agent
python -m venv .venv
source .venv/bin/activate

# Install core dependencies
pip install langgraph langchain-openai pydantic python-dotenv
```

### 1.3 Create Environment Configuration

Create `.env` in the project root:

```env
OPENAI_API_KEY=sk-your-key-here
LINEAR_API_KEY=lin_api_your-key-here  # For Phase 2
```

---

## 2. Define the State Schema

Create `agent/state.py` to define the shared state between agents:

```python
from typing import TypedDict, Literal, List, Optional
from pydantic import BaseModel

class ContractSchema(BaseModel):
    """The data contract being reviewed."""
    name: str
    fields: dict
    description: str

class ReviewFeedback(BaseModel):
    """Feedback from a review agent."""
    agent: str
    approved: bool
    concerns: List[str]
    suggestions: List[str]

class AgentState(TypedDict):
    """Shared state across all agents in the graph."""
    task_description: str
    current_contract: Optional[ContractSchema]
    review_feedback: List[ReviewFeedback]
    iteration_count: int
    status: Literal["drafting", "reviewing", "approved", "failed"]
    messages: List[str]
```

---

## 3. Implement the Core Agents

### 3.1 Implementation Agent (Contract Mode)

Create `agent/nodes/contractor.py`:

```python
from langchain_openai import ChatOpenAI
from agent.state import AgentState, ContractSchema

llm = ChatOpenAI(model="gpt-4o", temperature=0)

CONTRACTOR_PROMPT = """You are a Software Contract Designer.
Your job is to take a task description and produce a Pydantic-style data contract.

Task: {task_description}

Previous feedback to address:
{feedback}

Output a JSON object with:
- name: The contract/model name
- fields: A dict of field_name -> field_type with descriptions
- description: What this contract represents

Be precise. Think about edge cases and validation rules.
"""

def contractor_node(state: AgentState) -> AgentState:
    """Generate or refine a data contract based on the task."""
    feedback_str = "\n".join(
        f"- [{fb.agent}]: {', '.join(fb.concerns)}"
        for fb in state.get("review_feedback", [])
        if not fb.approved
    ) or "None - this is the first draft."
    
    prompt = CONTRACTOR_PROMPT.format(
        task_description=state["task_description"],
        feedback=feedback_str
    )
    
    response = llm.invoke(prompt)
    # Parse the response into a ContractSchema
    # (Add proper JSON parsing in production)
    
    return {
        **state,
        "current_contract": response.content,
        "status": "reviewing",
        "iteration_count": state.get("iteration_count", 0) + 1
    }
```

### 3.2 Security Agent (Reviewer)

Create `agent/nodes/security.py`:

```python
from langchain_openai import ChatOpenAI
from agent.state import AgentState, ReviewFeedback

llm = ChatOpenAI(model="gpt-4o", temperature=0)

SECURITY_PROMPT = """You are a paranoid Security Engineer reviewing a data contract.

Contract under review:
{contract}

Check for:
1. PII exposure risks (names, emails, SSNs, etc.)
2. Missing field validations
3. Potential injection vectors
4. Authorization/authentication gaps
5. Logging of sensitive data

Respond with JSON:
{{
  "approved": true/false,
  "concerns": ["list of security issues"],
  "suggestions": ["list of recommended changes"]
}}

Be thorough but fair. Not everything needs to be locked down.
"""

def security_node(state: AgentState) -> AgentState:
    """Review the contract for security issues."""
    prompt = SECURITY_PROMPT.format(
        contract=state["current_contract"]
    )
    
    response = llm.invoke(prompt)
    # Parse response into ReviewFeedback
    
    feedback = ReviewFeedback(
        agent="security",
        approved=True,  # Parse from response
        concerns=[],
        suggestions=[]
    )
    
    return {
        **state,
        "review_feedback": state.get("review_feedback", []) + [feedback]
    }
```

### 3.3 Supervisor (Orchestrator)

Create `agent/nodes/supervisor.py`:

```python
from agent.state import AgentState

MAX_ITERATIONS = 5

def supervisor_node(state: AgentState) -> AgentState:
    """Decide whether to continue the review loop or finalize."""
    reviews = state.get("review_feedback", [])
    iteration = state.get("iteration_count", 0)
    
    # Check if all reviewers approved
    all_approved = all(fb.approved for fb in reviews) if reviews else False
    
    if all_approved:
        return {**state, "status": "approved"}
    
    if iteration >= MAX_ITERATIONS:
        return {
            **state,
            "status": "failed",
            "messages": state.get("messages", []) + [
                f"Failed to reach approval after {MAX_ITERATIONS} iterations."
            ]
        }
    
    # Clear feedback for next iteration
    return {
        **state,
        "status": "drafting",
        "review_feedback": []
    }
```

---

## 4. Build the LangGraph

Create `agent/graph.py`:

```python
from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.nodes.contractor import contractor_node
from agent.nodes.security import security_node
from agent.nodes.supervisor import supervisor_node

def build_graph():
    """Construct the agent workflow graph."""
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("contractor", contractor_node)
    workflow.add_node("security", security_node)
    workflow.add_node("supervisor", supervisor_node)
    
    # Define edges
    workflow.set_entry_point("contractor")
    workflow.add_edge("contractor", "security")
    workflow.add_edge("security", "supervisor")
    
    # Conditional routing from supervisor
    workflow.add_conditional_edges(
        "supervisor",
        lambda state: state["status"],
        {
            "drafting": "contractor",   # Loop back for revision
            "approved": END,             # Success!
            "failed": END                # Give up
        }
    )
    
    return workflow.compile()

# Create the runnable graph
app = build_graph()
```

---

## 5. Create the Entry Point

Create `agent/main.py`:

```python
from dotenv import load_dotenv
from agent.graph import app
from agent.state import AgentState

load_dotenv()

def run_factory(task: str) -> dict:
    """Run the software factory on a given task."""
    initial_state: AgentState = {
        "task_description": task,
        "current_contract": None,
        "review_feedback": [],
        "iteration_count": 0,
        "status": "drafting",
        "messages": []
    }
    
    result = app.invoke(initial_state)
    return result

if __name__ == "__main__":
    task = """
    Create a User Profile data model for a healthcare application.
    It should store patient name, date of birth, contact info, and
    insurance details.
    """
    
    result = run_factory(task)
    print(f"\nFinal Status: {result['status']}")
    print(f"Iterations: {result['iteration_count']}")
    print(f"\nFinal Contract:\n{result['current_contract']}")
```

---

## 6. Add the Makefile

Create `Makefile` in the project root:

```makefile
.PHONY: agent install lint test

# Run the agent workflow
agent:
	cd agent && python main.py

# Install dependencies
install:
	cd agent && pip install -r requirements.txt

# Run linting
lint:
	cd agent && ruff check .

# Run tests
test:
	cd agent && pytest tests/
```

---

## 7. Verify the Setup

### 7.1 Test the Basic Flow

```bash
make agent
```

You should see:
1. The contractor generates an initial contract
2. The security agent reviews it
3. The supervisor decides to approve or loop back
4. Final output with the approved contract

### 7.2 Expected Output

```
Final Status: approved
Iterations: 2

Final Contract:
{
  "name": "PatientProfile",
  "fields": {
    "patient_id": "UUID (primary key)",
    "full_name": "str (encrypted at rest)",
    "date_of_birth": "date",
    "email": "EmailStr (validated)",
    "phone": "str (E.164 format)",
    "insurance_provider": "str",
    "insurance_policy_id": "str (masked in logs)"
  },
  "description": "Core patient profile for the healthcare platform..."
}
```

---

## 8. Next Steps

Once Phase 1 is validated, proceed to:

### Phase 2: Git Integration
- Add Linear API adapter to poll for issues
- Implement git tools for branch/commit operations
- Create the Publisher node for PR creation

### Phase 3: The Assembly Line
- Add more review agents (Compliance, Design)
- Implement stacked PR logic
- Wire up ephemeral environment deployment

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `OPENAI_API_KEY not found` | Ensure `.env` is in the project root and loaded |
| `Recursion limit reached` | Increase `MAX_ITERATIONS` or improve prompts |
| `JSON parsing errors` | Add structured output parsing with Pydantic |
| `Rate limiting` | Add retry logic with exponential backoff |

### Debug Mode

Add to `agent/config/settings.py`:

```python
import os

DEBUG = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = "DEBUG" if DEBUG else "INFO"
```

Run with debug output:

```bash
DEBUG=true make agent
```
