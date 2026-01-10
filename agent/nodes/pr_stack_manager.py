from agent.state import AgentState
from agent.tools.git import create_branch


def pr_stack_manager_node(state: AgentState) -> dict:
    """Manage the stacked PR workflow."""
    work_items = state.get("work_items", [])
    current_index = state.get("current_work_index", 0)

    if current_index >= len(work_items):
        return {"status": "stack_complete"}

    current_item = work_items[current_index]
    issue = state.get("current_issue")

    if not issue:
        return {"status": "failed", "messages": state.get("messages", []) + ["No issue for stack"]}

    item_type = current_item.get("type", "CONTRACT") if isinstance(current_item, dict) else current_item.type
    
    if item_type == "CONTRACT":
        base_branch = "main"
        stack_base = f"ai/{issue.identifier.lower()}/contract"
    else:
        stack_base = state.get("stack_base_branch", "main")
        base_branch = stack_base

    branch_name = f"ai/{issue.identifier.lower()}/{item_type.lower()}"
    success, msg = create_branch(branch_name, base_branch)

    if not success:
        return {
            "status": "failed",
            "messages": state.get("messages", []) + [f"Failed to create branch: {msg}"]
        }

    if isinstance(current_item, dict):
        work_items[current_index]["branch_name"] = branch_name
        work_items[current_index]["status"] = "in_progress"
    else:
        work_items[current_index].branch_name = branch_name
        work_items[current_index].status = "in_progress"

    print(f"   📚 Stack Manager: Working on {item_type} → {branch_name}")

    return {
        "work_items": work_items,
        "current_work_item": current_item,
        "stack_base_branch": stack_base if item_type == "CONTRACT" else state.get("stack_base_branch"),
        "status": f"working_{item_type.lower()}",
        "messages": state.get("messages", []) + [f"Started {item_type} on {branch_name}"]
    }
