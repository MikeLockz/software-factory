import json
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from agent.state import AgentState

load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

CLASSIFIER_PROMPT = """You are a request classifier for a software development AI system.

Analyze this task and classify it into ONE of these categories:

1. **requires_contract** - Tasks that involve:
   - API endpoints (REST, GraphQL)
   - Data models or schemas
   - Frontend-backend communication
   - Database entities
   - User-facing features with data exchange

2. **infrastructure** - Tasks that involve:
   - Monorepo setup, project scaffolding
   - CI/CD pipelines, GitHub Actions
   - Docker, Kubernetes, deployment configs
   - Linting, formatting, tooling setup
   - Environment configuration

3. **general** - Everything else:
   - General code implementations
   - Utilities, helpers, scripts
   - Documentation-only changes
   - Refactoring, bug fixes
   - Features without API contracts

Task: {task_description}

Respond with ONLY a JSON object:
{{"classification": "requires_contract"}} or {{"classification": "infrastructure"}} or {{"classification": "general"}}
"""


def classifier_node(state: AgentState) -> dict:
    """Classify the request type to determine workflow path."""
    prompt = CLASSIFIER_PROMPT.format(
        task_description=state["task_description"]
    )

    response = llm.invoke(prompt)
    content = response.content
    if isinstance(content, list):
        content = content[0] if content else ""
    content = content.strip()

    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\n?", "", content)
        content = re.sub(r"\n?```$", "", content)

    try:
        data = json.loads(content)
        request_type = data.get("classification", "general")
        if request_type not in ["requires_contract", "infrastructure", "general"]:
            request_type = "general"
    except json.JSONDecodeError:
        request_type = "general"

    print(f"   📊 Classified as: {request_type}")

    return {
        "request_type": request_type,
        "messages": state.get("messages", []) + [f"Classified as: {request_type}"]
    }
