"""Infra Engineer Planner - creates technical specs for infrastructure changes using Claude Code."""
import json
import os
from agent.state import AgentState
from agent.config.context import get_context_for_prompt
from agent.tools.claude_code import run_claude_code, extract_json_from_response


INFRA_ENGINEER_PLANNER_PROMPT = """You are a Senior Infrastructure Architect creating a technical specification.

{project_context}

PRD (Product Requirements Document):
{prd_content}

Create a detailed technical specification including:

1. **Resource Requirements**: What infrastructure resources are needed
2. **Configuration Schema**: Environment variables, secrets, config files
3. **Deployment Steps**: How to deploy this change
4. **Rollback Plan**: How to undo if something goes wrong
5. **Monitoring**: What metrics/alerts to set up
6. **Security Considerations**: Access controls, secrets management

Output your response as JSON (no markdown code blocks):
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
    """Generate a technical spec for infrastructure changes using Claude Code."""
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

    prompt = INFRA_ENGINEER_PLANNER_PROMPT.format(
        project_context=get_context_for_prompt(),
        prd_content=prd_content
    )

    # Run Claude Code CLI
    print("   🤖 Running Claude Code for infrastructure planning...")
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
            "messages": state.get("messages", []) + [f"Infra planner failed: {result['error']}"]
        }

    # Parse the response
    response_text = result.get("result", "")
    tech_spec = extract_json_from_response(response_text)

    if tech_spec:
        print(f"   📐 Infra Engineer Planner created spec: {tech_spec.get('title', 'Untitled')}")
        print(f"      Resource type: {tech_spec.get('resource_type', 'Unknown')}")
        print(f"      Effort: {tech_spec.get('estimated_effort', 'M')}")
    else:
        tech_spec = {"error": "Failed to parse spec", "raw": response_text[:500]}
        print("   ⚠️ Infra Engineer Planner could not parse response")

    return {
        "technical_spec": tech_spec,
        "status": "spec_ready",
        "messages": state.get("messages", []) + ["Infra Engineer Planner created technical spec"]
    }
