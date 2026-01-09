# Testing Strategy

> **Goal:** Comprehensive testing for agents, graphs, and generated code.

---

## Test Pyramid

```
         ┌─────────────┐
         │    E2E      │  ← Full workflow tests
         ├─────────────┤
         │ Integration │  ← Graph execution tests
         ├─────────────┤
         │    Unit     │  ← Individual node tests
         └─────────────┘
```

---

## 1. Unit Tests for Nodes

### 1.1 Test Structure

```
agent/
└── tests/
    ├── __init__.py
    ├── conftest.py           # Shared fixtures
    ├── test_contractor.py
    ├── test_security.py
    ├── test_supervisor.py
    └── mocks/
        └── llm_responses.py  # Mock LLM outputs
```

### 1.2 LLM Mocking

Create `agent/tests/mocks/llm_responses.py`:

```python
CONTRACTOR_RESPONSE = '''
{
    "name": "UserProfile",
    "fields": {
        "id": "UUID",
        "email": "EmailStr",
        "name": "str"
    },
    "description": "User profile model"
}
'''

SECURITY_APPROVED = '''
{
    "approved": true,
    "concerns": [],
    "suggestions": ["Consider adding rate limiting"]
}
'''

SECURITY_REJECTED = '''
{
    "approved": false,
    "concerns": ["PII field 'ssn' lacks encryption"],
    "suggestions": ["Encrypt SSN at rest"]
}
'''
```

### 1.3 Test Examples

Create `agent/tests/test_contractor.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from agent.nodes.contractor import contractor_node
from agent.tests.mocks.llm_responses import CONTRACTOR_RESPONSE

@pytest.fixture
def initial_state():
    return {
        "task_description": "Create a user profile model",
        "current_contract": None,
        "review_feedback": [],
        "iteration_count": 0,
        "status": "drafting",
        "messages": []
    }

@patch("agent.nodes.contractor.llm")
def test_contractor_generates_valid_contract(mock_llm, initial_state):
    """Contractor should generate a valid JSON contract."""
    mock_response = MagicMock()
    mock_response.content = CONTRACTOR_RESPONSE
    mock_llm.invoke.return_value = mock_response
    
    result = contractor_node(initial_state)
    
    assert result["status"] == "reviewing"
    assert result["iteration_count"] == 1
    assert "UserProfile" in result["current_contract"]

@patch("agent.nodes.contractor.llm")
def test_contractor_handles_feedback(mock_llm, initial_state):
    """Contractor should incorporate feedback in prompt."""
    from agent.state import ReviewFeedback
    
    initial_state["review_feedback"] = [
        ReviewFeedback(
            agent="security",
            approved=False,
            concerns=["Missing validation"],
            suggestions=["Add email validation"]
        )
    ]
    
    mock_response = MagicMock()
    mock_response.content = CONTRACTOR_RESPONSE
    mock_llm.invoke.return_value = mock_response
    
    contractor_node(initial_state)
    
    # Verify feedback was included in prompt
    call_args = mock_llm.invoke.call_args[0][0]
    assert "Missing validation" in call_args
```

Create `agent/tests/test_supervisor.py`:

```python
import pytest
from agent.nodes.supervisor import supervisor_node
from agent.state import ReviewFeedback

def test_supervisor_approves_when_all_pass():
    state = {
        "review_feedback": [
            ReviewFeedback(agent="security", approved=True, concerns=[], suggestions=[])
        ],
        "iteration_count": 1,
        "messages": []
    }
    
    result = supervisor_node(state)
    assert result["status"] == "approved"

def test_supervisor_requests_revision_on_rejection():
    state = {
        "review_feedback": [
            ReviewFeedback(agent="security", approved=False, concerns=["Issue"], suggestions=[])
        ],
        "iteration_count": 1,
        "messages": []
    }
    
    result = supervisor_node(state)
    assert result["status"] == "drafting"

def test_supervisor_fails_after_max_iterations():
    state = {
        "review_feedback": [
            ReviewFeedback(agent="security", approved=False, concerns=["Issue"], suggestions=[])
        ],
        "iteration_count": 5,
        "messages": []
    }
    
    result = supervisor_node(state)
    assert result["status"] == "failed"
```

---

## 2. Integration Tests

### 2.1 Graph Execution Tests

Create `agent/tests/test_graph.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from agent.graph import build_graph
from agent.tests.mocks.llm_responses import CONTRACTOR_RESPONSE, SECURITY_APPROVED

@pytest.fixture
def mock_llm():
    """Mock all LLM calls."""
    with patch("agent.nodes.contractor.llm") as contractor_mock, \
         patch("agent.nodes.security.llm") as security_mock:
        
        contractor_response = MagicMock()
        contractor_response.content = CONTRACTOR_RESPONSE
        contractor_mock.invoke.return_value = contractor_response
        
        security_response = MagicMock()
        security_response.content = SECURITY_APPROVED
        security_mock.invoke.return_value = security_response
        
        yield

def test_full_approval_flow(mock_llm):
    """Test complete flow from drafting to approval."""
    app = build_graph()
    
    initial_state = {
        "task_description": "Create a user profile model",
        "current_contract": None,
        "review_feedback": [],
        "iteration_count": 0,
        "status": "drafting",
        "messages": []
    }
    
    result = app.invoke(initial_state)
    
    assert result["status"] == "approved"
    assert result["iteration_count"] >= 1
    assert result["current_contract"] is not None
```

---

## 3. E2E Tests

### 3.1 Full Workflow Tests

Create `agent/tests/e2e/test_workflow.py`:

```python
import pytest
import os

# Only run E2E tests when flag is set
pytestmark = pytest.mark.skipunless(
    os.getenv("RUN_E2E_TESTS"),
    "E2E tests require RUN_E2E_TESTS=1"
)

def test_real_contract_generation():
    """Test with real LLM (requires API key)."""
    from agent.graph import app
    
    initial_state = {
        "task_description": "Create a simple todo item model with title and completed status",
        "current_contract": None,
        "review_feedback": [],
        "iteration_count": 0,
        "status": "drafting",
        "messages": []
    }
    
    result = app.invoke(initial_state)
    
    assert result["status"] in ["approved", "failed"]
    if result["status"] == "approved":
        assert "todo" in result["current_contract"].lower()
```

---

## 4. Test Configuration

### 4.1 pytest Configuration

Create `agent/pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = -v --tb=short
markers =
    slow: marks tests as slow
    e2e: marks end-to-end tests
```

### 4.2 conftest.py

Create `agent/tests/conftest.py`:

```python
import pytest
import os
from dotenv import load_dotenv

@pytest.fixture(scope="session", autouse=True)
def load_env():
    """Load environment variables for tests."""
    load_dotenv()

@pytest.fixture
def clean_state():
    """Provide a clean agent state."""
    return {
        "task_description": "",
        "current_contract": None,
        "review_feedback": [],
        "iteration_count": 0,
        "status": "drafting",
        "messages": []
    }
```

---

## 5. Makefile Targets

```makefile
# Run all unit tests
test:
	cd agent && pytest tests/ -v --ignore=tests/e2e

# Run with coverage
test-cov:
	cd agent && pytest tests/ --cov=. --cov-report=html --ignore=tests/e2e

# Run E2E tests (uses real LLM)
test-e2e:
	cd agent && RUN_E2E_TESTS=1 pytest tests/e2e/ -v

# Run specific test file
test-file:
	cd agent && pytest tests/$(FILE) -v
```

---

## 6. CI Integration

Add `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd agent
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run unit tests
        run: make test
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```
