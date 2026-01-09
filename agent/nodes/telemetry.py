import os
import httpx
from agent.state import AgentState

SENTRY_API = "https://sentry.io/api/0"


def telemetry_node(state: AgentState) -> dict:
    """Monitor production for error spikes after deployment."""
    sentry_token = os.getenv("SENTRY_AUTH_TOKEN")
    sentry_org = os.getenv("SENTRY_ORG")
    sentry_project = os.getenv("SENTRY_PROJECT")

    if not all([sentry_token, sentry_org, sentry_project]):
        print("   📊 Telemetry: Skipped (Sentry not configured)")
        return {
            "telemetry_status": "skipped",
            "messages": state.get("messages", []) + ["Sentry not configured"]
        }

    try:
        response = httpx.get(
            f"{SENTRY_API}/projects/{sentry_org}/{sentry_project}/stats/",
            headers={"Authorization": f"Bearer {sentry_token}"},
            params={"stat": "received", "resolution": "1m", "since": "-5m"}
        )

        if response.status_code != 200:
            print("   📊 Telemetry: Error fetching stats")
            return {
                "telemetry_status": "error",
                "messages": state.get("messages", []) + ["Failed to fetch Sentry stats"]
            }

        stats = response.json()
        recent_errors = sum(point[1] for point in stats[-5:]) if stats else 0

        ERROR_THRESHOLD = 100

        if recent_errors > ERROR_THRESHOLD:
            print(f"   📊 Telemetry: ⚠️ Error spike! {recent_errors} errors")
            return {
                "telemetry_status": "error_spike",
                "error_count": recent_errors,
                "action": "revert",
                "messages": state.get("messages", []) + [f"Error spike: {recent_errors} errors in 5min"]
            }

        print(f"   📊 Telemetry: ✅ Healthy ({recent_errors} errors)")
        return {
            "telemetry_status": "healthy",
            "error_count": recent_errors,
            "messages": state.get("messages", []) + [f"Production healthy: {recent_errors} errors"]
        }

    except Exception as e:
        print(f"   📊 Telemetry: Error - {e}")
        return {
            "telemetry_status": "error",
            "messages": state.get("messages", []) + [f"Telemetry error: {e}"]
        }
