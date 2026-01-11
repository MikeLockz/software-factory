from typing import TypedDict, Literal, List, Optional, Any
from pydantic import BaseModel


class ContractSchema(BaseModel):
    """The data contract being reviewed."""
    name: str
    fields: dict
    description: str


class ReviewFeedback(BaseModel):
    """Feedback from a review agent."""
    agent: str
    approved: bool
    concerns: List[str]
    suggestions: List[str]


class WorkItem(BaseModel):
    """A single work item in the stacked PR workflow."""
    type: Literal["CONTRACT", "BACKEND", "FRONTEND"]
    title: str
    description: str
    acceptance_criteria: List[str] = []
    depends_on: Optional[str] = None
    branch_name: Optional[str] = None
    pr_url: Optional[str] = None
    status: Literal["pending", "in_progress", "completed", "failed"] = "pending"


class AgentState(TypedDict):
    """Shared state across all agents in the graph."""
    task_description: str
    current_contract: Optional[str]
    review_feedback: List[ReviewFeedback]
    iteration_count: int
    status: Literal["drafting", "reviewing", "approved", "failed", "published", "architected", "stack_complete", "working_contract", "working_backend", "working_frontend", "prd_ready", "prd_approved", "spec_ready", "awaiting_technical_review", "awaiting_prd_review"]
    messages: List[str]
    # Phase 2: Linear integration
    current_issue: Optional[Any]
    pr_url: Optional[str]
    # Product Manager
    prd: Optional[Any]
    prd_feedback: Optional[str]
    # Request classification
    request_type: Optional[Literal["requires_contract", "infrastructure", "general"]]
    # Phase 3: Stacked PRs
    work_items: Optional[List[Any]]
    current_work_index: Optional[int]
    current_work_item: Optional[Any]
    stack_base_branch: Optional[str]
    # Phase 3: Ephemeral environments
    ephemeral_status: Optional[str]
    preview_url: Optional[str]
    ephemeral_db_url: Optional[str]
    # Phase 3: Testing
    test_status: Optional[str]
    test_output: Optional[str]
    # Phase 3: Telemetry
    telemetry_status: Optional[str]
    error_count: Optional[int]
    action: Optional[str]
    # Phase 3: Revert
    revert_status: Optional[str]
    reverted_commit: Optional[str]
    # Issue type routing
    is_sub_issue: Optional[bool]
    parent_issue: Optional[Any]
    # Technical spec from planner nodes
    technical_spec: Optional[Any]
    # Workflow phase (prd, erd, implement)
    workflow_phase: Optional[Literal["prd", "erd", "implement"]]
