import subprocess
from agent.state import AgentState
from agent.adapters.linear_adapter import LinearAdapter


def reverter_node(state: AgentState) -> dict:
    """Revert deployment and create bug ticket."""
    issue = state.get("current_issue")
    pr_url = state.get("pr_url")

    if not pr_url:
        print("   ⏪ Reverter: Skipped (no PR URL)")
        return {"revert_status": "skipped"}

    try:
        result = subprocess.run(
            ["gh", "pr", "view", pr_url, "--json", "mergeCommit", "-q", ".mergeCommit.oid"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0 and result.stdout.strip():
            merge_sha = result.stdout.strip()

            subprocess.run(["git", "revert", merge_sha, "--no-edit"])
            subprocess.run(["git", "push", "origin", "main"])

            print(f"   ⏪ Reverter: Reverted {merge_sha[:8]}")

            if issue:
                try:
                    adapter = LinearAdapter()
                    adapter.add_comment(
                        issue.id,
                        f"⚠️ **Auto-Reverted**\n\nError spike detected after deployment.\nRevert commit: {merge_sha}"
                    )
                    adapter.transition_issue(issue.id, "AI: Failed")
                except Exception:
                    pass

            return {
                "revert_status": "completed",
                "reverted_commit": merge_sha,
                "messages": state.get("messages", []) + [f"Reverted commit {merge_sha}"]
            }
        else:
            print("   ⏪ Reverter: PR not merged yet")
            return {
                "revert_status": "skipped",
                "messages": state.get("messages", []) + ["PR not merged, nothing to revert"]
            }

    except Exception as e:
        print(f"   ⏪ Reverter: Failed - {e}")
        return {
            "revert_status": "failed",
            "messages": state.get("messages", []) + [f"Revert failed: {e}"]
        }
