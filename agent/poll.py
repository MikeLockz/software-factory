import time
import os
from dotenv import load_dotenv
from agent.graph import app
from agent.state import AgentState
from agent.adapters.linear_adapter import LinearAdapter

load_dotenv()

POLL_INTERVAL = 30  # seconds
TEAM_KEY = os.getenv("LINEAR_TEAM_KEY", "ENG")


def poll_and_process():
    """Poll Linear for ready issues and process them."""
    adapter = LinearAdapter()

    print(f"🔄 Polling Linear for issues in 'AI: Ready' state...")
    issues = adapter.get_ready_issues(TEAM_KEY)

    if not issues:
        print("   No issues found.")
        return

    for issue in issues:
        print(f"\n📋 Processing: {issue.identifier} - {issue.title}")

        # Transition to In Progress
        adapter.transition_issue(issue.id, "AI: In Progress")

        # Run the factory
        initial_state: AgentState = {
            "task_description": f"{issue.title}\n\n{issue.description or ''}",
            "current_contract": None,
            "review_feedback": [],
            "iteration_count": 0,
            "status": "drafting",
            "messages": [],
            "current_issue": issue,
            "pr_url": None
        }

        try:
            result = app.invoke(initial_state)

            if result["status"] == "published":
                print(f"   ✅ PR created: {result.get('pr_url')}")
            else:
                messages = result.get('messages', [])
                feedback = result.get('review_feedback', [])
                
                # Build error details
                error_details = []
                if messages:
                    error_details.append(f"Messages: {messages}")
                if feedback:
                    for fb in feedback:
                        if not fb.approved and fb.concerns:
                            error_details.append(f"{fb.agent}: {fb.concerns}")
                
                error_summary = "; ".join(error_details) if error_details else "No details available"
                
                adapter.transition_issue(issue.id, "AI: Failed")
                adapter.add_comment(issue.id, f"❌ Failed: {error_summary[:500]}")
                print(f"   ❌ Failed: {result['status']}")
                print(f"      Details: {error_summary}")

        except Exception as e:
            import traceback
            adapter.transition_issue(issue.id, "AI: Failed")
            adapter.add_comment(issue.id, f"❌ Error: {str(e)}")
            print(f"   ❌ Error: {e}")
            traceback.print_exc()


def main():
    """Main polling loop."""
    print("🏭 Software Factory - Phase 2: Linear Integration")
    print("=" * 50)

    while True:
        poll_and_process()
        print(f"\n⏳ Sleeping for {POLL_INTERVAL}s...")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
