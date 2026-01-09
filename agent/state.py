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


class AgentState(TypedDict):
    """Shared state across all agents in the graph."""
    task_description: str
    current_contract: Optional[str]
    review_feedback: List[ReviewFeedback]
    iteration_count: int
    status: Literal["drafting", "reviewing", "approved", "failed", "published"]
    messages: List[str]
    # Phase 2: Linear integration (Any type to avoid circular import with LangGraph)
    current_issue: Optional[Any]  # LinearIssue from agent.adapters.linear_adapter
    pr_url: Optional[str]
