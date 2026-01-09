import json
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from agent.state import AgentState

load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)

ARCHITECT_PROMPT = """You are a Software Architect breaking down a feature into stacked PRs.

Feature Request:
{task_description}

Break this into exactly 3 ordered work items following Middle-Out methodology:
1. CONTRACT: Define the data schema/API contract (Pydantic models, OpenAPI spec)
2. BACKEND: Implement the server logic using the contract
3. FRONTEND: Build the UI consuming the contract

Output JSON:
{{
  "work_items": [
    {{
      "type": "CONTRACT",
      "title": "Define [X] schema",
      "description": "Detailed spec for the contract",
      "acceptance_criteria": ["list", "of", "criteria"]
    }},
    {{
      "type": "BACKEND",
      "title": "Implement [X] API",
      "description": "Backend implementation details",
      "acceptance_criteria": ["list", "of", "criteria"],
      "depends_on": "CONTRACT"
    }},
    {{
      "type": "FRONTEND",
      "title": "Build [X] UI",
      "description": "Frontend implementation details",
      "acceptance_criteria": ["list", "of", "criteria"],
      "depends_on": "CONTRACT"
    }}
  ]
}}
"""


def architect_node(state: AgentState) -> dict:
    """Break down a feature into stacked work items."""
    prompt = ARCHITECT_PROMPT.format(
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
        breakdown = json.loads(content)
        work_items = breakdown.get("work_items", [])
    except json.JSONDecodeError:
        work_items = []

    print(f"   🏗️ Architect: {len(work_items)} work items planned")

    return {
        "work_items": work_items,
        "current_work_index": 0,
        "status": "architected" if work_items else "failed",
        "messages": state.get("messages", []) + [f"Architected {len(work_items)} work items"]
    }
