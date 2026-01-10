"""Sub-Issue Handler - creates sub-issues from technical specs for human review."""
import os
import json
from agent.state import AgentState
from agent.adapters.linear_adapter import LinearAdapter

TEAM_KEY = os.getenv("LINEAR_TEAM_KEY", "ENG")


def format_tech_spec_for_review(tech_spec: dict, request_type: str) -> str:
    """Format technical spec as markdown for human review."""
    title = tech_spec.get("title", "Technical Specification")
    effort = tech_spec.get("estimated_effort", "M")
    
    sections = [f"# {title}\n\n**Estimated Effort:** {effort}\n"]
    
    if request_type == "requires_contract":
        # Contract spec formatting
        contract_name = tech_spec.get("contract_name", "Unknown")
        sections.append(f"## Contract: `{contract_name}`\n")
        
        schema = tech_spec.get("schema", {})
        if schema:
            sections.append("### Schema\n")
            for field, details in schema.items():
                if isinstance(details, dict):
                    field_type = details.get("type", "unknown")
                    required = "required" if details.get("required") else "optional"
                    validation = details.get("validation", "")
                    sections.append(f"- `{field}` ({field_type}, {required}): {validation}\n")
        
        if tech_spec.get("sample_valid_payload"):
            sections.append(f"\n### Sample Valid Payload\n```json\n{json.dumps(tech_spec['sample_valid_payload'], indent=2)}\n```\n")
        
        if tech_spec.get("testing_strategy"):
            sections.append("\n### Testing Strategy\n")
            for test in tech_spec.get("testing_strategy", []):
                sections.append(f"- {test}\n")
                
    elif request_type == "infrastructure":
        # Infrastructure spec formatting
        resource_type = tech_spec.get("resource_type", "Unknown")
        sections.append(f"## Resource Type: `{resource_type}`\n")
        
        resources = tech_spec.get("resources", [])
        if resources:
            sections.append("\n### Resources\n")
            for res in resources:
                sections.append(f"- **{res.get('name', 'unknown')}** ({res.get('type', 'unknown')}): {res.get('description', '')}\n")
        
        env_vars = tech_spec.get("environment_variables", [])
        if env_vars:
            sections.append("\n### Environment Variables\n")
            for var in env_vars:
                req = "required" if var.get("required") else "optional"
                sections.append(f"- `{var.get('name', 'VAR')}` ({req}): {var.get('description', '')}\n")
        
        if tech_spec.get("deployment_steps"):
            sections.append("\n### Deployment Steps\n")
            for i, step in enumerate(tech_spec.get("deployment_steps", []), 1):
                sections.append(f"{i}. {step}\n")
                
        if tech_spec.get("rollback_plan"):
            sections.append(f"\n### Rollback Plan\n{tech_spec['rollback_plan']}\n")
            
    else:
        # General software spec formatting
        components = tech_spec.get("components", [])
        if components:
            sections.append("## Components\n")
            for comp in components:
                sections.append(f"### `{comp.get('path', comp.get('name', 'unknown'))}`\n")
                sections.append(f"**Type:** {comp.get('type', 'module')}\n\n")
                sections.append(f"{comp.get('description', '')}\n\n")
                if comp.get("public_interface"):
                    sections.append("**Interface:**\n")
                    for iface in comp.get("public_interface", []):
                        sections.append(f"- `{iface}`\n")
                sections.append("\n")
        
        api_contracts = tech_spec.get("api_contracts", [])
        if api_contracts:
            sections.append("## API Contracts\n")
            for api in api_contracts:
                sections.append(f"### `{api.get('method', 'GET')} {api.get('path', '/unknown')}`\n")
                sections.append(f"{api.get('description', '')}\n\n")
        
        if tech_spec.get("data_flow"):
            sections.append(f"## Data Flow\n{tech_spec['data_flow']}\n\n")
        
        if tech_spec.get("testing_strategy"):
            sections.append("## Testing Strategy\n")
            for test in tech_spec.get("testing_strategy", []):
                sections.append(f"- {test}\n")
    
    return "".join(sections)


def sub_issue_handler_node(state: AgentState) -> dict:
    """Create a sub-issue from the technical spec for human review."""
    tech_spec = state.get("technical_spec")
    issue = state.get("current_issue")
    request_type = state.get("request_type", "general")
    
    if not tech_spec or not issue:
        return {
            "status": "failed",
            "messages": state.get("messages", []) + ["No technical spec or issue to create sub-issue from"]
        }
    
    # Format the spec for the sub-issue description
    spec_markdown = format_tech_spec_for_review(tech_spec, request_type)
    
    # Create sub-issue title
    spec_title = tech_spec.get("title", f"Technical Implementation for {issue.identifier}")
    sub_issue_title = f"[Tech Spec] {spec_title}"
    
    # Create the sub-issue
    adapter = LinearAdapter()
    try:
        sub_issue = adapter.create_sub_issue(
            parent_id=issue.id,
            team_key=TEAM_KEY,
            title=sub_issue_title,
            description=spec_markdown,
            state_name="Human: Review"
        )
        
        if sub_issue:
            print(f"   📋 Created sub-issue: {sub_issue.identifier}")
            print(f"      Title: {sub_issue_title}")
            print(f"      State: Human: Review")
            
            # Add comment to parent issue
            adapter.add_comment(
                issue.id,
                f"📐 Technical spec created as sub-issue: **{sub_issue.identifier}**\n\n"
                f"Awaiting human review in 'Human: Technical Review' column."
            )
            
            # Transition parent issue to waiting state
            adapter.transition_issue(issue.id, "AI: Awaiting Sub-task")
            
            return {
                "status": "awaiting_technical_review",
                "messages": state.get("messages", []) + [f"Created sub-issue {sub_issue.identifier} for technical review"]
            }
        else:
            return {
                "status": "failed",
                "messages": state.get("messages", []) + ["Failed to create sub-issue"]
            }
            
    except Exception as e:
        print(f"   ⚠️ Error creating sub-issue: {e}")
        return {
            "status": "failed", 
            "messages": state.get("messages", []) + [f"Error creating sub-issue: {str(e)}"]
        }
