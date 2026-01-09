from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.nodes.contractor import contractor_node
from agent.nodes.security import security_node
from agent.nodes.supervisor import supervisor_node
from agent.nodes.publisher import publisher_node


def build_graph():
    """Construct the agent workflow graph."""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("contractor", contractor_node)
    workflow.add_node("security", security_node)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("publisher", publisher_node)

    # Define edges
    workflow.set_entry_point("contractor")
    workflow.add_edge("contractor", "security")
    workflow.add_edge("security", "supervisor")

    # Conditional routing from supervisor
    workflow.add_conditional_edges(
        "supervisor",
        lambda state: state["status"],
        {
            "drafting": "contractor",   # Loop back for revision
            "approved": "publisher",    # Route to publisher on approval
            "failed": END               # Give up
        }
    )

    # Publisher completes the workflow
    workflow.add_edge("publisher", END)

    return workflow.compile()


# Create the runnable graph
app = build_graph()
