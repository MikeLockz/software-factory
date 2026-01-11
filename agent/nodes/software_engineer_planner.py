"""Software Engineer Planner - creates technical specs for feature implementation using Claude Code."""
import json
import os
from agent.state import AgentState
from agent.config.context import get_context_for_prompt
from agent.tools.claude_code import run_claude_code, extract_json_from_response


SOFTWARE_ENGINEER_PLANNER_PROMPT = """You are a Senior Software Architect creating a technical specification for a feature.

{project_context}

PRD (Product Requirements Document):
{prd_content}

Additional Context (Comments):
{comments}

Create a detailed technical specification including:

1. **Component Breakdown**: What modules/components need to be created or modified
2. **File Structure**: Where each file should live
3. **API Contracts**: If applicable, the API endpoints and payloads
4. **Data Flow**: How data moves through the system
5. **Dependencies**: External packages or internal modules needed
6. **Testing Strategy**: How to test this feature

Output your response as JSON (no markdown code blocks):
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
    """Generate a technical spec for feature implementation using Claude Code."""
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
            
            # Fetch comments
            comments = adapter.get_issue_comments(issue.id)
            if comments:
                comments_text = "\n\n".join(comments)
                print(f"   💬 Fetched {len(comments)} comments")
            else:
                comments_text = "No comments available."
        except Exception as e:
            print(f"   ⚠️ Could not fetch fresh issue or comments: {e}")
            comments_text = "Could not fetch comments."
    
    # Use fresh content, or fall back to task_description
    if not prd_content:
        prd_content = state.get("task_description", "No PRD available")

    prompt = SOFTWARE_ENGINEER_PLANNER_PROMPT.format(
        project_context=get_context_for_prompt(),
        prd_content=prd_content,
        comments=comments_text
    )

    # Run Claude Code CLI
    print("   🤖 Running Claude Code for software planning...")
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
            "messages": state.get("messages", []) + [f"Software planner failed: {result['error']}"]
        }

    # Parse the response
    response_text = result.get("result", "")
    tech_spec = extract_json_from_response(response_text)

    if tech_spec:
        print(f"   📐 Software Engineer Planner created spec: {tech_spec.get('title', 'Untitled')}")
        print(f"      Components: {len(tech_spec.get('components', []))}")
        print(f"      Effort: {tech_spec.get('estimated_effort', 'M')}")
    else:
        tech_spec = {"error": "Failed to parse spec", "raw": response_text[:500]}
        print("   ⚠️ Software Engineer Planner could not parse response")

    return {
        "technical_spec": tech_spec,
        "status": "spec_ready",
        "messages": state.get("messages", []) + ["Software Engineer Planner created technical spec"]
    }
