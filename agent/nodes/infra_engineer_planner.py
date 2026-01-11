"""Infra Engineer Planner - creates technical specs for infrastructure changes."""
import json
import os
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from agent.state import AgentState
from agent.config.context import get_context_for_prompt

load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.3)

INFRA_ENGINEER_PLANNER_PROMPT = """You are a Senior Infrastructure Architect creating a technical specification.

{project_context}

PRD Summary:
{prd_summary}

Task Description:
{task_description}

Create a detailed technical specification including:

1. **Resource Requirements**: What infrastructure resources are needed
2. **Configuration Schema**: Environment variables, secrets, config files
3. **Deployment Steps**: How to deploy this change
4. **Rollback Plan**: How to undo if something goes wrong
5. **Monitoring**: What metrics/alerts to set up
6. **Security Considerations**: Access controls, secrets management

Output JSON:
{{
  "title": "Technical spec title",
  "resource_type": "dockerfile|ci_config|script|terraform|k8s",
  "resources": [
    {{
      "name": "resource_name",
      "type": "container|database|cache|queue|storage",
      "config": {{}},
      "description": "what this resource does"
    }}
  ],
  "environment_variables": [
    {{
      "name": "VAR_NAME",
      "description": "what this var controls",
      "required": true,
      "example": "example_value"
    }}
  ],
  "deployment_steps": ["step 1", "step 2"],
  "rollback_plan": "how to rollback",
  "monitoring": ["metric or alert to set up"],
  "security_notes": ["security consideration"],
  "estimated_effort": "S|M|L"
}}
"""


def infra_engineer_planner_node(state: AgentState) -> dict:
    """Generate a technical spec for infrastructure changes."""
    prd = state.get("prd") or {}
    if prd:
        prd_summary = f"{prd.get('title', 'N/A')}: {prd.get('problem_statement', 'N/A')}"
    else:
        # PRD is in the issue description - use task_description which includes it
        prd_summary = state.get("task_description", "No PRD available")

    prompt = INFRA_ENGINEER_PLANNER_PROMPT.format(
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
        print(f"   📐 Infra Engineer Planner created spec: {tech_spec.get('title', 'Untitled')}")
        print(f"      Resource type: {tech_spec.get('resource_type', 'Unknown')}")
        print(f"      Effort: {tech_spec.get('estimated_effort', 'M')}")
    except json.JSONDecodeError:
        tech_spec = {"error": "Failed to parse spec", "raw": content[:500]}
        print("   ⚠️ Infra Engineer Planner could not parse response")

    return {
        "technical_spec": tech_spec,
        "status": "spec_ready",
        "messages": state.get("messages", []) + ["Infra Engineer Planner created technical spec"]
    }
