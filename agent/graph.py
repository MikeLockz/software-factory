from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.nodes.classifier import classifier_node
from agent.nodes.architect import architect_node
from agent.nodes.contractor import contractor_node
from agent.nodes.infra_engineer import infra_engineer_node
from agent.nodes.software_engineer import software_engineer_node
from agent.nodes.security import security_node
from agent.nodes.compliance import compliance_node
from agent.nodes.design import design_node
from agent.nodes.supervisor import supervisor_node
from agent.nodes.stack_manager import stack_manager_node
from agent.nodes.publisher import publisher_node
from agent.nodes.deployer import deployer_node
from agent.nodes.test_agent import test_agent_node
from agent.nodes.telemetry import telemetry_node
from agent.nodes.reverter import reverter_node


def route_from_classifier(state: AgentState) -> str:
    """Route based on request classification."""
    request_type = state.get("request_type", "general")
    if request_type == "requires_contract":
        return "architect"
    elif request_type == "infrastructure":
        return "infra_engineer"
    else:
        return "software_engineer"


def route_from_supervisor(state: AgentState) -> str:
    """Route from supervisor based on status and request_type."""
    status = state["status"]
    if status == "approved":
        return "publisher"
    elif status == "drafting":
        request_type = state.get("request_type", "general")
        if state.get("work_items"):
            return "contractor"
        if request_type == "requires_contract":
            return "contractor"
        elif request_type == "infrastructure":
            return "infra_engineer"
        else:
            return "software_engineer"
    else:
        return "end"


def route_from_stack_manager(state: AgentState) -> str:
    """Route from stack manager based on current work."""
    status = state.get("status", "")
    if status.startswith("working_"):
        return "contractor"
    elif status == "stack_complete":
        return "deployer"
    else:
        return "end"


def route_to_first_reviewer(state: AgentState) -> str:
    """Route to first reviewer based on work item type."""
    current_work = state.get("current_work_item")
    if current_work:
        work_type = current_work.get("type") if isinstance(current_work, dict) else current_work.type
        if work_type == "BACKEND":
            return "compliance"
        elif work_type == "FRONTEND":
            return "design"
    return "security"


def route_from_publisher(state: AgentState) -> str:
    """Route from publisher - continue stack or deploy."""
    work_items = state.get("work_items", [])
    current_index = state.get("current_work_index", 0)
    if work_items and current_index < len(work_items):
        return "stack_manager"
    return "deployer"


def route_from_test_agent(state: AgentState) -> str:
    """Route based on test results."""
    test_status = state.get("test_status", "skipped")
    if test_status == "passed":
        return "telemetry"
    return "end"


def route_from_telemetry(state: AgentState) -> str:
    """Route based on telemetry status."""
    if state.get("telemetry_status") == "error_spike":
        return "reverter"
    return "end"


def build_graph():
    """Construct the Phase 3 agent workflow graph."""
    workflow = StateGraph(AgentState)

    workflow.add_node("classifier", classifier_node)
    workflow.add_node("architect", architect_node)
    workflow.add_node("stack_manager", stack_manager_node)
    workflow.add_node("contractor", contractor_node)
    workflow.add_node("infra_engineer", infra_engineer_node)
    workflow.add_node("software_engineer", software_engineer_node)
    workflow.add_node("security", security_node)
    workflow.add_node("compliance", compliance_node)
    workflow.add_node("design", design_node)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("publisher", publisher_node)
    workflow.add_node("deployer", deployer_node)
    workflow.add_node("test_agent", test_agent_node)
    workflow.add_node("telemetry", telemetry_node)
    workflow.add_node("reverter", reverter_node)

    workflow.set_entry_point("classifier")

    workflow.add_conditional_edges(
        "classifier",
        route_from_classifier,
        {
            "architect": "architect",
            "infra_engineer": "infra_engineer",
            "software_engineer": "software_engineer"
        }
    )

    workflow.add_edge("architect", "stack_manager")

    workflow.add_conditional_edges(
        "stack_manager",
        route_from_stack_manager,
        {
            "contractor": "contractor",
            "deployer": "deployer",
            "end": END
        }
    )

    # Implementation nodes -> first reviewer
    workflow.add_conditional_edges(
        "contractor",
        route_to_first_reviewer,
        {"security": "security", "compliance": "compliance", "design": "design"}
    )
    workflow.add_conditional_edges(
        "infra_engineer",
        route_to_first_reviewer,
        {"security": "security", "compliance": "compliance", "design": "design"}
    )
    workflow.add_conditional_edges(
        "software_engineer",
        route_to_first_reviewer,
        {"security": "security", "compliance": "compliance", "design": "design"}
    )

    # Specialized reviewers -> Security (series)
    workflow.add_edge("compliance", "security")
    workflow.add_edge("design", "security")
    workflow.add_edge("security", "supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "contractor": "contractor",
            "infra_engineer": "infra_engineer",
            "software_engineer": "software_engineer",
            "publisher": "publisher",
            "end": END
        }
    )

    workflow.add_conditional_edges(
        "publisher",
        route_from_publisher,
        {"stack_manager": "stack_manager", "deployer": "deployer"}
    )

    workflow.add_edge("deployer", "test_agent")

    workflow.add_conditional_edges(
        "test_agent",
        route_from_test_agent,
        {"telemetry": "telemetry", "end": END}
    )

    workflow.add_conditional_edges(
        "telemetry",
        route_from_telemetry,
        {"reverter": "reverter", "end": END}
    )

    workflow.add_edge("reverter", END)

    return workflow.compile()


app = build_graph()
