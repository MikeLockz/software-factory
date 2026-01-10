"""Contractor Planner - creates technical specs for data contracts."""
import json
import os
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from agent.state import AgentState
from agent.config.context import get_context_for_prompt

load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.3)

CONTRACTOR_PLANNER_PROMPT = """You are a Senior Software Architect creating a technical specification for a data contract.

{project_context}

PRD Summary:
{prd_summary}

Task Description:
{task_description}

Create a detailed technical specification including:

1. **Schema Design**: Field names, types, validation rules
2. **Sample Data**: Example valid/invalid payloads
3. **Integration Points**: Where this contract will be used
4. **Migration Plan**: If replacing existing contracts
5. **Testing Strategy**: How to validate the contract

Output JSON:
{{
  "title": "Technical spec title",
  "contract_name": "ContractName (PascalCase)",
  "schema": {{
    "field_name": {{
      "type": "string|int|bool|list|dict",
      "required": true,
      "validation": "description of validation rules",
      "example": "example value"
    }}
  }},
  "sample_valid_payload": {{}},
  "sample_invalid_payloads": [{{}}],
  "integration_points": ["where this is used"],
  "migration_notes": "any migration considerations",
  "testing_strategy": ["test cases to implement"],
  "estimated_effort": "S|M|L"
}}
"""


def contractor_planner_node(state: AgentState) -> dict:
    """Generate a technical spec for a data contract."""
    prd = state.get("prd", {})
    prd_summary = f"{prd.get('title', 'N/A')}: {prd.get('problem_statement', 'N/A')}"

    prompt = CONTRACTOR_PLANNER_PROMPT.format(
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
        print(f"   📐 Contractor Planner created spec: {tech_spec.get('title', 'Untitled')}")
        print(f"      Contract: {tech_spec.get('contract_name', 'Unknown')}")
        print(f"      Effort: {tech_spec.get('estimated_effort', 'M')}")
    except json.JSONDecodeError:
        tech_spec = {"error": "Failed to parse spec", "raw": content[:500]}
        print("   ⚠️ Contractor Planner could not parse response")

    return {
        "technical_spec": tech_spec,
        "status": "spec_ready",
        "messages": state.get("messages", []) + ["Contractor Planner created technical spec"]
    }
