from dotenv import load_dotenv
load_dotenv()
from agent.adapters.linear_adapter import LinearAdapter

def reset_issue():
    adapter = LinearAdapter()
    issue_id = "0c3405ac-3b01-4a74-8034-2780dfbcc34a"
    print(f"Resetting issue {issue_id} to 'AI: Ready'...")
    success = adapter.transition_issue(issue_id, "AI: Ready")
    if success:
        print("✅ Success")
    else:
        print("❌ Failed")

if __name__ == "__main__":
    reset_issue()
