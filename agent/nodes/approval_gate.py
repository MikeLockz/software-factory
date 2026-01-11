"""Approval Gate node - posts PRD for human review in Linear."""
from agent.state import AgentState


def format_gherkin_criteria(criteria: list) -> str:
    """Format acceptance criteria as Gherkin scenarios."""
    lines = []
    for ac in criteria:
        # Handle both new Gherkin format and legacy string format
        if isinstance(ac, dict):
            lines.append(f"  **Scenario:** {ac.get('scenario', 'Unnamed scenario')}")
            lines.append(f"    - **Given** {ac.get('given', 'N/A')}")
            lines.append(f"    - **When** {ac.get('when', 'N/A')}")
            lines.append(f"    - **Then** {ac.get('then', 'N/A')}")
        else:
            # Legacy string format fallback
            lines.append(f"  - {ac}")
    return "\n".join(lines)


def format_prd_for_review(prd: dict) -> str:
    """Format PRD as markdown for human review."""
    stories_parts = []
    for s in prd.get("user_stories", []):
        story_header = f"### As a **{s.get('as_a', 'user')}**, I want **{s.get('i_want', 'feature')}**, so that **{s.get('so_that', 'benefit')}**"
        criteria = format_gherkin_criteria(s.get('acceptance_criteria', []))
        stories_parts.append(f"{story_header}\n\n#### Acceptance Criteria\n{criteria}")
    
    stories = "\n\n".join(stories_parts)

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
    """Post PRD for human review and wait for approval."""
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

    # If we have a Linear issue, post the PRD and move to Human: Review
    if issue:
        try:
            from agent.adapters.linear_adapter import LinearAdapter
            adapter = LinearAdapter()
            # Replace the ticket description with the PRD
            adapter.update_issue_description(issue.id, prd_markdown)
            adapter.add_comment(issue.id, "## 📋 PRD Ready for Review\n\nPlease review the PRD above. When approved, move this issue to **AI: Create ERD** to continue with technical planning.")
            # Move to Human: Review PRD for human approval
            adapter.transition_issue(issue.id, "Human: Review PRD")
            print(f"   ✅ Posted PRD to Linear issue {issue.identifier}")
            print(f"   ⏸️  Moved to 'Human: Review PRD' - waiting for human approval")
        except Exception as e:
            print(f"   ⚠️ Could not post to Linear: {e}")

    # End flow here - human will move issue back to "AI: Ready" when approved
    return {
        "status": "awaiting_prd_review",
        "messages": state.get("messages", []) + ["PRD posted for review - awaiting human approval"]
    }

