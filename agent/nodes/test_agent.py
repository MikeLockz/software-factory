import os
import subprocess
from agent.state import AgentState


def test_agent_node(state: AgentState) -> dict:
    """Run E2E tests against the ephemeral environment."""
    preview_url = state.get("preview_url")
    if not preview_url:
        print("   🧪 Tests: Skipped (no preview URL)")
        return {
            "test_status": "skipped",
            "messages": state.get("messages", []) + ["No preview URL for testing"]
        }

    try:
        result = subprocess.run(
            ["npx", "playwright", "test", "--reporter=json"],
            env={**os.environ, "BASE_URL": preview_url},
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode == 0:
            print("   🧪 Tests: ✅ All passed")
            return {
                "test_status": "passed",
                "test_output": result.stdout[:1000],
                "messages": state.get("messages", []) + ["All E2E tests passed"]
            }

        print("   🧪 Tests: ❌ Failed")
        return {
            "test_status": "failed",
            "test_output": (result.stdout + result.stderr)[:1000],
            "messages": state.get("messages", []) + ["E2E tests failed"]
        }

    except subprocess.TimeoutExpired:
        print("   🧪 Tests: ⏰ Timeout")
        return {
            "test_status": "timeout",
            "messages": state.get("messages", []) + ["E2E tests timed out"]
        }
    except FileNotFoundError:
        print("   🧪 Tests: Skipped (playwright not found)")
        return {
            "test_status": "skipped",
            "messages": state.get("messages", []) + ["Playwright not installed"]
        }
    except Exception as e:
        print(f"   🧪 Tests: Error - {e}")
        return {
            "test_status": "error",
            "messages": state.get("messages", []) + [f"Test error: {e}"]
        }
