"""Poll Linear for issues and process them through the appropriate workflow."""
import re
import time
import os
from dotenv import load_dotenv
from agent.graph import app
from agent.state import AgentState
from agent.adapters.linear_adapter import LinearAdapter

load_dotenv()

POLL_INTERVAL = 30  # seconds
TEAM_KEY = os.getenv("LINEAR_TEAM_KEY", "ENG")

# Workflow columns that trigger AI action
ACTION_COLUMNS = [
    "AI: Create PRD",    # Product Manager creates PRD
    "AI: Create ERD",    # Engineer creates technical sub-issues
    "AI: Implement",     # Engineer implements sub-issue code
]


def determine_workflow_phase(issue, state_name: str) -> dict:
    """Determine workflow phase based on state and issue properties."""
    is_sub = issue.parent_id is not None
    
    if state_name == "AI: Create PRD":
        # PRD phase - Product Manager creates PRD
        return {
            "phase": "prd",
            "is_sub_issue": False,
            "skip_pm": False,
        }
    elif state_name == "AI: Create ERD":
        # ERD phase - Engineer creates technical sub-issues
        # PRD should already exist in description
        return {
            "phase": "erd",
            "is_sub_issue": False,
            "skip_pm": True,  # Skip PM, go to classifier -> planner
        }
    elif state_name == "AI: Implement":
        # Implementation phase - only sub-issues should be here
        return {
            "phase": "implement",
            "is_sub_issue": True,  # Force sub-issue behavior
            "skip_pm": True,
        }
    else:
        # Unknown state
        return {
            "phase": "unknown",
            "is_sub_issue": is_sub,
            "skip_pm": is_sub,
        }


def process_issue(issue, adapter: LinearAdapter, phase_info: dict):
    """Process a single issue through the workflow."""
    print(f"\n📋 Processing: {issue.identifier} - {issue.title}")
    print(f"   Phase: {phase_info['phase']}")
    
    if phase_info["is_sub_issue"]:
        print(f"   📎 Sub-issue of parent: {issue.parent_id}")
    
    # Don't transition to In Progress at start - let nodes handle their own transitions
    # Only ERD and Implement phases should auto-transition
    if phase_info["phase"] in ["erd", "implement"]:
        adapter.transition_issue(issue.id, "AI: In Progress")
    
    # Build initial state
    initial_state: AgentState = {
        "task_description": f"{issue.title}\n\n{issue.description or ''}",
        "current_contract": None,
        "review_feedback": [],
        "iteration_count": 0,
        "status": "drafting",
        "messages": [],
        "current_issue": issue,
        "pr_url": None,
        "request_type": None,
        "work_items": None,
        "current_work_index": None,
        "current_work_item": None,
        "stack_base_branch": None,
        "ephemeral_status": None,
        "preview_url": None,
        "ephemeral_db_url": None,
        "test_status": None,
        "test_output": None,
        "telemetry_status": None,
        "error_count": None,
        "action": None,
        "revert_status": None,
        "reverted_commit": None,
        "is_sub_issue": phase_info["is_sub_issue"],
        "parent_issue": None,
        "technical_spec": None,
        "prd": None,
        "prd_feedback": None,
        "workflow_phase": phase_info["phase"],
    }

    try:
        result = app.invoke(initial_state)

        status = result.get("status", "unknown")
        if status == "published":
            print(f"   ✅ PR created: {result.get('pr_url')}")
            # Publisher node handles transition to Human: Review PR
        elif status == "awaiting_prd_review":
            print(f"   ✅ PRD created, moved to Human: Review PRD")
        elif status == "awaiting_technical_review":
            print(f"   ✅ ERD created, sub-issues in Human: Review ERD")
        elif status in ["failed", "error"]:
            messages = result.get('messages', [])
            feedback = result.get('review_feedback', [])
            
            error_details = []
            if messages:
                error_details.append(f"Messages: {messages}")
            if feedback:
                for fb in feedback:
                    if not fb.approved and fb.concerns:
                        error_details.append(f"{fb.agent}: {fb.concerns}")
            
            error_summary = "; ".join(error_details) if error_details else "No details"
            
            adapter.transition_issue(issue.id, "AI: Failed")
            adapter.add_comment(issue.id, f"❌ Failed: {error_summary[:500]}")
            print(f"   ❌ Failed: {status}")
            print(f"      Details: {error_summary}")
        else:
            print(f"   ℹ️  Completed with status: {status}")

    except Exception as e:
        import traceback
        adapter.transition_issue(issue.id, "AI: Failed")
        adapter.add_comment(issue.id, f"❌ Error: {str(e)}")
        print(f"   ❌ Error: {e}")
        traceback.print_exc()


def extract_pr_url_from_comments(comments: list) -> str | None:
    """Extract GitHub PR URL from issue comments."""
    pr_pattern = r'https://github\.com/[^/]+/[^/]+/pull/\d+'
    
    for comment in comments:
        match = re.search(pr_pattern, comment)
        if match:
            return match.group(0)
    
    return None


def check_pr_merges_and_complete(adapter: LinearAdapter):
    """Check issues in Human: Review PR for merged PRs and complete them."""
    print("\n🔍 Checking for merged PRs...")
    
    # Try to import GitHub adapter - skip if not configured
    try:
        from agent.adapters.github_adapter import GitHubAdapter
        github = GitHubAdapter()
    except ValueError as e:
        print(f"   ⚠️ GitHub integration not configured: {e}")
        return
    except Exception as e:
        print(f"   ⚠️ GitHub adapter error: {e}")
        return
    
    # Get issues in Human: Review PR
    pr_issues = adapter.get_issues_in_state(TEAM_KEY, "Human: Review PR")
    
    if not pr_issues:
        print("   No issues awaiting PR review.")
        return
    
    print(f"   Found {len(pr_issues)} issue(s) in Human: Review PR")
    
    for issue in pr_issues:
        # Get comments to find PR URL
        comments = adapter.get_issue_comments(issue.id)
        pr_url = extract_pr_url_from_comments(comments)
        
        if not pr_url:
            print(f"   ⚠️ {issue.identifier}: No PR URL found in comments")
            continue
        
        # Check if PR is merged
        if github.is_pr_merged(pr_url):
            print(f"   ✅ {issue.identifier}: PR merged! Moving to Done")
            adapter.transition_issue(issue.id, "Done")
            adapter.add_comment(issue.id, "🎉 PR merged! Issue completed.")
            
            # Check if parent should be completed
            if issue.parent_id:
                check_parent_completion(adapter, issue.parent_id)
        else:
            print(f"   ⏳ {issue.identifier}: PR not yet merged")


def check_parent_completion(adapter: LinearAdapter, parent_id: str):
    """Check if all sub-issues are complete and complete the parent if so."""
    parent = adapter.get_issue_by_id(parent_id)
    if not parent:
        print(f"   ⚠️ Could not find parent issue: {parent_id}")
        return
    
    # Check if all sub-issues are done
    if adapter.all_sub_issues_completed(parent_id):
        print(f"   🎉 All sub-issues complete! Moving parent {parent.identifier} to Done")
        adapter.transition_issue(parent_id, "Done")
        adapter.add_comment(parent_id, "🎉 All sub-issues completed! Parent issue marked as done.")


def check_in_progress_parents(adapter: LinearAdapter):
    """Check parent issues in AI: In Progress to see if they should be completed."""
    print("\n🔍 Checking parent issues for completion...")
    
    # Get parent issues in AI: In Progress
    in_progress = adapter.get_issues_in_state(TEAM_KEY, "AI: In Progress")
    
    # Filter to only parent issues (no parent_id)
    parent_issues = [i for i in in_progress if i.parent_id is None]
    
    if not parent_issues:
        print("   No parent issues in progress.")
        return
    
    print(f"   Found {len(parent_issues)} parent issue(s) in AI: In Progress")
    
    for parent in parent_issues:
        if adapter.all_sub_issues_completed(parent.id):
            print(f"   🎉 All sub-issues complete! Moving {parent.identifier} to Done")
            adapter.transition_issue(parent.id, "Done")
            adapter.add_comment(parent.id, "🎉 All sub-issues completed! Parent issue marked as done.")
        else:
            sub_issues = adapter.get_sub_issues(parent.id)
            done_count = sum(1 for s in sub_issues if s.state in {"Done", "Completed", "Closed"})
            print(f"   ⏳ {parent.identifier}: {done_count}/{len(sub_issues)} sub-issues complete")


def poll_and_process():
    """Poll Linear for issues in all action columns and process them."""
    adapter = LinearAdapter()
    
    # Phase 1-3: Process AI action columns
    for column in ACTION_COLUMNS:
        print(f"\n🔄 Checking '{column}' column...")
        issues = adapter.get_issues_in_state(TEAM_KEY, column)
        
        if not issues:
            print("   No issues found.")
            continue
        
        print(f"   Found {len(issues)} issue(s)")
        
        for issue in issues:
            phase_info = determine_workflow_phase(issue, column)
            process_issue(issue, adapter, phase_info)
    
    # Phase 4: Check for merged PRs and complete issues
    check_pr_merges_and_complete(adapter)
    
    # Phase 5: Check parent issues for auto-completion
    check_in_progress_parents(adapter)


def main():
    """Main polling loop."""
    print("🏭 Software Factory - Workflow Pipeline")
    print("=" * 50)
    print(f"Monitoring columns: {', '.join(ACTION_COLUMNS)}")
    print("Also checking: Human: Review PR (for merged PRs)")

    while True:
        poll_and_process()
        print(f"\n⏳ Sleeping for {POLL_INTERVAL}s...")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
