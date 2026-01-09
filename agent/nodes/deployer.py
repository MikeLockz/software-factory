from agent.state import AgentState
from agent.tools.deploy import deploy_preview, provision_ephemeral_db


def deployer_node(state: AgentState) -> dict:
    """Deploy ephemeral environment for testing."""
    branch = state.get("stack_base_branch")
    if not branch:
        print("   🚀 Deployer: Skipped (no branch)")
        return {
            "ephemeral_status": "skipped",
            "messages": state.get("messages", []) + ["No branch to deploy"]
        }

    db_success, db_result = provision_ephemeral_db(branch)
    if not db_success:
        print(f"   🚀 Deployer: DB provisioning skipped")
        return {
            "ephemeral_status": "db_skipped",
            "messages": state.get("messages", []) + [f"DB provisioning skipped: {db_result}"]
        }

    deploy_success, preview_url = deploy_preview(branch)
    if not deploy_success:
        print(f"   🚀 Deployer: Deploy skipped")
        return {
            "ephemeral_status": "deploy_skipped",
            "ephemeral_db_url": db_result,
            "messages": state.get("messages", []) + [f"Deploy skipped: {preview_url}"]
        }

    print(f"   🚀 Deployer: Deployed to {preview_url}")
    return {
        "ephemeral_status": "deployed",
        "preview_url": preview_url,
        "ephemeral_db_url": db_result,
        "messages": state.get("messages", []) + [f"Deployed to {preview_url}"]
    }
