"""Software Engineer Planner - creates technical specs for feature implementation."""
import json
import os
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from agent.state import AgentState
from agent.config.context import get_context_for_prompt

load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.3)

SOFTWARE_ENGINEER_PLANNER_PROMPT = """You are a Senior Software Architect creating a technical specification for a feature.

{project_context}

PRD Summary:
{prd_summary}

Task Description:
{task_description}

Create a detailed technical specification including:

1. **Component Breakdown**: What modules/components need to be created or modified
2. **File Structure**: Where each file should live
3. **API Contracts**: If applicable, the API endpoints and payloads
4. **Data Flow**: How data moves through the system
5. **Dependencies**: External packages or internal modules needed
6. **Testing Strategy**: How to test this feature

Output JSON:
{{
  "title": "Technical spec title",
  "components": [
    {{
      "name": "component_name",
      "type": "module|component|service|utility",
      "path": "src/path/to/file.py",
      "description": "what this component does",
      "public_interface": ["function_name(args) -> return_type"]
    }}
  ],
  "api_contracts": [
    {{
      "method": "GET|POST|PUT|DELETE",
      "path": "/api/endpoint",
      "request_body": {{}},
      "response_body": {{}},
      "description": "what this endpoint does"
    }}
  ],
  "data_flow": "description of how data moves through components",
  "dependencies": ["package_name"],
  "testing_strategy": ["test cases to implement"],
  "estimated_effort": "S|M|L"
}}
"""


def software_engineer_planner_node(state: AgentState) -> dict:
    """Generate a technical spec for feature implementation."""
    prd = state.get("prd", {})
    prd_summary = f"{prd.get('title', 'N/A')}: {prd.get('problem_statement', 'N/A')}"

    prompt = SOFTWARE_ENGINEER_PLANNER_PROMPT.format(
        project_context=get_context_for_prompt(),
        prd_summary=prd_summary,
        task_description=state["task_description"]
    )

    response = llm.invoke(prompt)
    content = response.content
    if isinstance(content, list):
        content = content[0] if content else ""
    content = content.strip()

    # Strip markdown
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\n?", "", content)
        content = re.sub(r"\n?```$", "", content)

    try:
        tech_spec = json.loads(content)
        print(f"   📐 Software Engineer Planner created spec: {tech_spec.get('title', 'Untitled')}")
        print(f"      Components: {len(tech_spec.get('components', []))}")
        print(f"      Effort: {tech_spec.get('estimated_effort', 'M')}")
    except json.JSONDecodeError:
        tech_spec = {"error": "Failed to parse spec", "raw": content[:500]}
        print("   ⚠️ Software Engineer Planner could not parse response")

    return {
        "technical_spec": tech_spec,
        "status": "spec_ready",
        "messages": state.get("messages", []) + ["Software Engineer Planner created technical spec"]
    }
