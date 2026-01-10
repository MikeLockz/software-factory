from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.nodes.classifier import classifier_node
from agent.nodes.product_manager import product_manager_node
from agent.nodes.approval_gate import approval_gate_node
from agent.nodes.feature_engineer import feature_engineer_node
from agent.nodes.contract_engineer import contract_engineer_node
from agent.nodes.infra_engineer import infra_engineer_node
from agent.nodes.software_engineer import software_engineer_node
from agent.nodes.security_engineer import security_engineer_node
from agent.nodes.compliance_reviewer import compliance_reviewer_node
from agent.nodes.design_reviewer import design_reviewer_node
from agent.nodes.review_supervisor import review_supervisor_node
from agent.nodes.pr_stack_manager import pr_stack_manager_node
from agent.nodes.publisher import publisher_node
from agent.nodes.deployer import deployer_node
from agent.nodes.test_agent import test_agent_node
from agent.nodes.telemetry import telemetry_node
from agent.nodes.reverter import reverter_node
from agent.nodes.implementation_engineer import implementation_engineer_node, implementation_engineer_correction_node, validation_node


def route_from_classifier(state: AgentState) -> str:
    """Route based on request classification."""
    request_type = state.get("request_type", "general")
    if request_type == "requires_contract":
        return "feature_engineer"
    elif request_type == "infrastructure":
        return "infra_engineer"
    else:
        return "software_engineer"


def route_from_review_supervisor(state: AgentState) -> str:
    """Route from review supervisor based on status and request_type."""
    status = state["status"]
    if status == "approved":
        return "publisher"
    elif status == "drafting":
        request_type = state.get("request_type", "general")
        if state.get("work_items"):
            return "contract_engineer"
        if request_type == "requires_contract":
            return "contract_engineer"
        elif request_type == "infrastructure":
            return "infra_engineer"
        else:
            return "software_engineer"
    else:
        return "end"


def route_from_pr_stack_manager(state: AgentState) -> str:
    """Route from stack manager based on current work."""
    status = state.get("status", "")
    if status.startswith("working_"):
        return "contract_engineer"
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
            return "compliance_reviewer"
        elif work_type == "FRONTEND":
            return "design_reviewer"
    return "security_engineer"


def route_from_publisher(state: AgentState) -> str:
    """Route from publisher - continue stack or deploy."""
    work_items = state.get("work_items", [])
    current_index = state.get("current_work_index", 0)
    if work_items and current_index < len(work_items):
        return "pr_stack_manager"
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
    """Route based on PM status."""
    status = state.get("status", "")
    if status == "prd_ready":
        return "approval_gate"
    return "end"


def route_from_validation(state: AgentState) -> str:
    """Route based on validation status."""
    validation_status = state.get("validation_status", "passed")
    if validation_status == "failed":
        return "implementation_engineer_correction"
    # Route to first reviewer based on work item type
    return route_to_first_reviewer(state)


def build_graph():
    """Construct the Phase 3 agent workflow graph."""
    workflow = StateGraph(AgentState)

    workflow.add_node("product_manager", product_manager_node)
    workflow.add_node("approval_gate", approval_gate_node)
    workflow.add_node("classifier", classifier_node)
    workflow.add_node("feature_engineer", feature_engineer_node)
    workflow.add_node("pr_stack_manager", pr_stack_manager_node)
    workflow.add_node("contract_engineer", contract_engineer_node)
    workflow.add_node("infra_engineer", infra_engineer_node)
    workflow.add_node("software_engineer", software_engineer_node)
    workflow.add_node("implementation_engineer", implementation_engineer_node)
    workflow.add_node("validation", validation_node)
    workflow.add_node("implementation_engineer_correction", implementation_engineer_correction_node)
    workflow.add_node("security_engineer", security_engineer_node)
    workflow.add_node("compliance_reviewer", compliance_reviewer_node)
    workflow.add_node("design_reviewer", design_reviewer_node)
    workflow.add_node("review_supervisor", review_supervisor_node)
    workflow.add_node("publisher", publisher_node)
    workflow.add_node("deployer", deployer_node)
    workflow.add_node("test_agent", test_agent_node)
    workflow.add_node("telemetry", telemetry_node)
    workflow.add_node("reverter", reverter_node)

    workflow.set_entry_point("product_manager")

    workflow.add_conditional_edges(
        "product_manager",
        route_from_product_manager,
        {
            "approval_gate": "approval_gate",
            "end": END
        }
    )

    # After approval, continue to classifier
    workflow.add_edge("approval_gate", "classifier")

    workflow.add_conditional_edges(
        "classifier",
        route_from_classifier,
        {
            "feature_engineer": "feature_engineer",
            "infra_engineer": "infra_engineer",
            "software_engineer": "software_engineer"
        }
    )

    workflow.add_edge("feature_engineer", "pr_stack_manager")

    workflow.add_conditional_edges(
        "pr_stack_manager",
        route_from_pr_stack_manager,
        {
            "contract_engineer": "contract_engineer",
            "deployer": "deployer",
            "end": END
        }
    )

    # Implementation nodes -> implementation_engineer -> validation -> reviewers
    workflow.add_edge("contract_engineer", "implementation_engineer")
    workflow.add_edge("infra_engineer", "implementation_engineer")
    workflow.add_edge("software_engineer", "implementation_engineer")
    
    # Implementation Engineeer -> Validation
    workflow.add_edge("implementation_engineer", "validation")
    
    # Validation routes to reviewers or back to correction
    workflow.add_conditional_edges(
        "validation",
        route_from_validation,
        {
            "implementation_engineer_correction": "implementation_engineer_correction",
            "security_engineer": "security_engineer",
            "compliance_reviewer": "compliance_reviewer",
            "design_reviewer": "design_reviewer"
        }
    )
    
    # Correction loops back to validation
    workflow.add_edge("implementation_engineer_correction", "validation")

    # Specialized reviewers -> Security Engineer (series)
    workflow.add_edge("compliance_reviewer", "security_engineer")
    workflow.add_edge("design_reviewer", "security_engineer")
    workflow.add_edge("security_engineer", "review_supervisor")

    workflow.add_conditional_edges(
        "review_supervisor",
        route_from_review_supervisor,
        {
            "contract_engineer": "contract_engineer",
            "infra_engineer": "infra_engineer",
            "software_engineer": "software_engineer",
            "publisher": "publisher",
            "end": END
        }
    )

    workflow.add_conditional_edges(
        "publisher",
        route_from_publisher,
        {"pr_stack_manager": "pr_stack_manager", "deployer": "deployer"}
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
