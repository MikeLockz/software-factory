from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.nodes.product_manager import product_manager_node
from agent.nodes.approval_gate import approval_gate_node
from agent.nodes.classifier import classifier_node
from agent.nodes.architect import architect_node
from agent.nodes.contractor import contractor_node
from agent.nodes.contractor_planner import contractor_planner_node
from agent.nodes.infra_engineer import infra_engineer_node
from agent.nodes.infra_engineer_planner import infra_engineer_planner_node
from agent.nodes.software_engineer import software_engineer_node
from agent.nodes.software_engineer_planner import software_engineer_planner_node
from agent.nodes.sub_issue_handler import sub_issue_handler_node
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


def route_entry_point(state: AgentState) -> str:
    """Route based on workflow phase determined by poll.py."""
    phase = state.get("workflow_phase", "prd")
    
    if phase == "prd":
        # PRD phase - go to product manager
        print("   📝 PRD phase - routing to product manager")
        return "product_manager"
    elif phase == "erd":
        # ERD phase - skip PM, go to classifier -> planner -> sub-issue handler
        print("   📐 ERD phase - routing to classifier for technical planning")
        return "classifier"
    elif phase == "implement":
        # Implementation phase - sub-issue ready for implementation
        print("   🔨 Implementation phase - routing to classifier for implementation")
        return "classifier"
    else:
        # Legacy support for is_sub_issue flag
        if state.get("is_sub_issue"):
            print("   📎 Sub-issue detected - skipping product manager, going to classifier")
            return "classifier"
        return "product_manager"


def route_from_classifier(state: AgentState) -> str:
    """Route based on workflow phase and request classification."""
    phase = state.get("workflow_phase", "")
    request_type = state.get("request_type", "general")

    if phase == "implement":
        # Implementation phase: go directly to implementation engineer
        if request_type == "requires_contract":
            return "contractor"
        elif request_type == "infrastructure":
            return "infra_engineer"
        else:
            return "software_engineer"
    else:
        # ERD phase (or legacy): go to planner to create sub-issues
        if request_type == "requires_contract":
            return "contractor_planner"
        elif request_type == "infrastructure":
            return "infra_engineer_planner"
        else:
            return "software_engineer_planner"


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


def route_from_product_manager(state: AgentState) -> str:
    """Route from product manager based on PRD status."""
    status = state.get("status", "")
    if status == "prd_ready":
        return "approval_gate"
    return "end"


def route_from_approval_gate(state: AgentState) -> str:
    """Route from approval gate - end flow, wait for human review."""
    # PRD is now in Human: Review PRD
    # Human will move issue to "AI: Create ERD" when approved
    # poll.py will pick it up with workflow_phase="erd"
    return "end"


def route_from_planner(state: AgentState) -> str:
    """Route from planner nodes - go to sub-issue handler."""
    status = state.get("status", "")
    if status == "spec_ready":
        return "sub_issue_handler"
    return "end"


def build_graph():
    """Construct the Phase 3 agent workflow graph with technical review flow."""
    workflow = StateGraph(AgentState)

    # Entry router (determines if sub-issue or parent)
    workflow.add_node("entry_router", lambda state: state)  # Pass-through

    # Product Manager nodes
    workflow.add_node("product_manager", product_manager_node)
    workflow.add_node("approval_gate", approval_gate_node)
    
    # Classifier
    workflow.add_node("classifier", classifier_node)
    
    # Planner nodes (for parent issues)
    workflow.add_node("contractor_planner", contractor_planner_node)
    workflow.add_node("software_engineer_planner", software_engineer_planner_node)
    workflow.add_node("infra_engineer_planner", infra_engineer_planner_node)
    workflow.add_node("sub_issue_handler", sub_issue_handler_node)
    
    # Implementation nodes (for sub-issues)
    workflow.add_node("architect", architect_node)
    workflow.add_node("stack_manager", stack_manager_node)
    workflow.add_node("contractor", contractor_node)
    workflow.add_node("infra_engineer", infra_engineer_node)
    workflow.add_node("software_engineer", software_engineer_node)
    
    # Review nodes
    workflow.add_node("security", security_node)
    workflow.add_node("compliance", compliance_node)
    workflow.add_node("design", design_node)
    workflow.add_node("supervisor", supervisor_node)
    
    # Publishing & deployment nodes
    workflow.add_node("publisher", publisher_node)
    workflow.add_node("deployer", deployer_node)
    workflow.add_node("test_agent", test_agent_node)
    workflow.add_node("telemetry", telemetry_node)
    workflow.add_node("reverter", reverter_node)

    # Entry point: router decides if sub-issue or parent
    workflow.set_entry_point("entry_router")
    workflow.add_conditional_edges(
        "entry_router",
        route_entry_point,
        {"product_manager": "product_manager", "classifier": "classifier"}
    )

    # Product Manager -> Approval Gate -> Classifier (for parent issues)
    workflow.add_conditional_edges(
        "product_manager",
        route_from_product_manager,
        {"approval_gate": "approval_gate", "end": END}
    )
    workflow.add_conditional_edges(
        "approval_gate",
        route_from_approval_gate,
        {"classifier": "classifier", "end": END}
    )

    # Classifier routes to planners (parent) or implementation (sub-issue)
    workflow.add_conditional_edges(
        "classifier",
        route_from_classifier,
        {
            # Parent issue routes (planners)
            "contractor_planner": "contractor_planner",
            "software_engineer_planner": "software_engineer_planner",
            "infra_engineer_planner": "infra_engineer_planner",
            # Sub-issue routes (implementation) - requires_contract goes to architect
            "contractor": "architect",  # Contract requests still go through architect->stack_manager
            "infra_engineer": "infra_engineer",
            "software_engineer": "software_engineer"
        }
    )

    # Planners -> Sub-issue handler -> END (wait for human)
    workflow.add_conditional_edges(
        "contractor_planner",
        route_from_planner,
        {"sub_issue_handler": "sub_issue_handler", "end": END}
    )
    workflow.add_conditional_edges(
        "software_engineer_planner",
        route_from_planner,
        {"sub_issue_handler": "sub_issue_handler", "end": END}
    )
    workflow.add_conditional_edges(
        "infra_engineer_planner",
        route_from_planner,
        {"sub_issue_handler": "sub_issue_handler", "end": END}
    )
    workflow.add_edge("sub_issue_handler", END)

    # Architect -> Stack Manager (for contract requests)
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
