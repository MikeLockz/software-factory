"""Contractor Planner - creates technical specs for data contracts using Claude Code."""
import json
import os
from agent.state import AgentState
from agent.config.context import get_context_for_prompt
from agent.tools.claude_code import run_claude_code, extract_json_from_response


CONTRACTOR_PLANNER_PROMPT = """You are a Senior Software Architect creating a technical specification for a data contract.

{project_context}

PRD (Product Requirements Document):
{prd_content}

Create a detailed technical specification including:

1. **Schema Design**: Field names, types, validation rules
2. **Sample Data**: Example valid/invalid payloads
3. **Integration Points**: Where this contract will be used
4. **Migration Plan**: If replacing existing contracts
5. **Testing Strategy**: How to validate the contract

Output your response as JSON (no markdown code blocks):
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
    """Generate a technical spec for a data contract using Claude Code."""
    # Fetch fresh issue content from Linear - PRD is in the description after approval
    issue = state.get("current_issue")
    prd_content = ""
    
    if issue:
        from agent.adapters.linear_adapter import LinearAdapter
        try:
            adapter = LinearAdapter()
            fresh_issue = adapter.get_issue_by_id(issue.id)
            if fresh_issue and fresh_issue.description:
                prd_content = fresh_issue.description
                print(f"   📄 Fetched fresh PRD from Linear issue {fresh_issue.identifier}")
        except Exception as e:
            print(f"   ⚠️ Could not fetch fresh issue: {e}")
    
    # Use fresh content, or fall back to task_description
    if not prd_content:
        prd_content = state.get("task_description", "No PRD available")

    prompt = CONTRACTOR_PLANNER_PROMPT.format(
        project_context=get_context_for_prompt(),
        prd_content=prd_content
    )

    # Run Claude Code CLI
    print("   🤖 Running Claude Code for contract planning...")
    result = run_claude_code(
        prompt=prompt,
        working_dir=state.get("workspace_path", "."),
        allowed_tools=["Read"],  # Read-only for planning
        output_format="text",
        timeout=120
    )

    if result.get("error"):
        print(f"   ⚠️ Claude Code error: {result['error']}")
        return {
            "technical_spec": {"error": result["error"]},
            "status": "spec_failed",
            "messages": state.get("messages", []) + [f"Contractor planner failed: {result['error']}"]
        }

    # Parse the response
    response_text = result.get("result", "")
    tech_spec = extract_json_from_response(response_text)

    if tech_spec:
        print(f"   📐 Contractor Planner created spec: {tech_spec.get('title', 'Untitled')}")
        print(f"      Contract: {tech_spec.get('contract_name', 'Unknown')}")
        print(f"      Effort: {tech_spec.get('estimated_effort', 'M')}")
    else:
        tech_spec = {"error": "Failed to parse spec", "raw": response_text[:500]}
        print("   ⚠️ Contractor Planner could not parse response")

    return {
        "technical_spec": tech_spec,
        "status": "spec_ready",
        "messages": state.get("messages", []) + ["Contractor Planner created technical spec"]
    }
