import sys
from dotenv import load_dotenv
from agent.graph import app
from agent.state import AgentState

load_dotenv()


def run_factory(task: str) -> dict:
    """Run the software factory on a given task."""
    initial_state: AgentState = {
        "task_description": task,
        "current_contract": None,
        "review_feedback": [],
        "iteration_count": 0,
        "status": "drafting",
        "messages": []
    }

    result = app.invoke(initial_state)
    return result


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    else:
        task = """
        Create a User Profile data model for a healthcare application.
        It should store patient name, date of birth, contact info, and
        insurance details.
        """

    print(f"🏭 Software Factory - Phase 1: The Brain")
    print(f"{'=' * 50}")
    print(f"📝 Task: {task.strip()[:100]}...")
    print(f"{'=' * 50}\n")

    result = run_factory(task)

    print(f"\n{'=' * 50}")
    print(f"✅ Final Status: {result['status']}")
    print(f"🔄 Iterations: {result['iteration_count']}")

    if result.get("messages"):
        print(f"\n📨 Messages:")
        for msg in result["messages"]:
            print(f"  - {msg}")

    print(f"\n📋 Final Contract:")
    print(result.get("current_contract", "No contract generated"))


if __name__ == "__main__":
    main()
