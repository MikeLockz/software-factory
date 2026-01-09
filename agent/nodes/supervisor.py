from agent.state import AgentState

MAX_ITERATIONS = 5


def supervisor_node(state: AgentState) -> dict:
    """Decide whether to continue the review loop or finalize."""
    reviews = state.get("review_feedback", [])
    iteration = state.get("iteration_count", 0)

    # Check if all reviewers approved
    all_approved = all(fb.approved for fb in reviews) if reviews else False

    if all_approved:
        return {"status": "approved"}

    if iteration >= MAX_ITERATIONS:
        messages = state.get("messages", [])
        return {
            "status": "failed",
            "messages": messages + [
                f"Failed to reach approval after {MAX_ITERATIONS} iterations."
            ]
        }

    # Need another iteration
    return {"status": "drafting"}
