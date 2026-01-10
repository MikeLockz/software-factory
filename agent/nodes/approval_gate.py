"""Approval Gate node - posts PRD for human review in Linear."""
from agent.state import AgentState


def format_prd_for_review(prd: dict) -> str:
    """Format PRD as markdown for human review."""
    stories = "\n".join(
        f"- As a **{s.get('as_a', 'user')}**, I want **{s.get('i_want', 'feature')}**, so that **{s.get('so_that', 'benefit')}**\n"
        f"  - Criteria: {', '.join(s.get('acceptance_criteria', []))}"
        for s in prd.get("user_stories", [])
    )

    return f"""# {prd.get('title', 'Untitled')}

## Problem Statement
{prd.get('problem_statement', 'N/A')}

## User Stories
{stories}

## Edge Cases
{chr(10).join('- ' + e for e in prd.get('edge_cases', []))}

## Out of Scope
{chr(10).join('- ' + e for e in prd.get('out_of_scope', []))}

## Success Metrics
{chr(10).join('- ' + m for m in prd.get('success_metrics', []))}

---
**Priority:** {prd.get('priority', 'P1')} | **Complexity:** {prd.get('estimated_complexity', 'M')}
"""


def approval_gate_node(state: AgentState) -> dict:
    """Post PRD for human review."""
    prd = state.get("prd")
    issue = state.get("current_issue")

    if not prd:
        return {
            "status": "failed",
            "messages": state.get("messages", []) + ["No PRD to review"]
        }

    # Format PRD for display
    prd_markdown = format_prd_for_review(prd)
    print(f"   📋 PRD Ready for Review:")
    print(prd_markdown)

    # If we have a Linear issue, post the comment
    if issue:
        try:
            from agent.adapters.linear_adapter import LinearAdapter
            adapter = LinearAdapter()
            # Replace the ticket description with the PRD
            adapter.update_issue_description(issue.id, prd_markdown)
            adapter.transition_issue(issue.id, "Human: Product Approve")
            print(f"   ✅ Posted PRD to Linear issue {issue.id}")
        except Exception as e:
            print(f"   ⚠️ Could not post to Linear: {e}")

    return {
        "status": "awaiting_approval",
        "messages": state.get("messages", []) + ["PRD posted for human review"]
    }
