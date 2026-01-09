import os
import httpx
from typing import Optional, List
from pydantic import BaseModel

LINEAR_API_URL = "https://api.linear.app/graphql"


class LinearIssue(BaseModel):
    id: str
    identifier: str
    title: str
    description: Optional[str]
    state: str
    priority: int
    parent_id: Optional[str] = None


class LinearAdapter:
    """Adapter for Linear API interactions."""

    def __init__(self):
        self.api_key = os.getenv("LINEAR_API_KEY")
        if not self.api_key:
            raise ValueError("LINEAR_API_KEY not set")
        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }

    def _query(self, query: str, variables: dict = None) -> dict:
        """Execute a GraphQL query against Linear."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        response = httpx.post(
            LINEAR_API_URL,
            headers=self.headers,
            json=payload
        )
        if response.status_code != 200:
            print(f"Linear API error: {response.status_code} - {response.text}")
        response.raise_for_status()
        return response.json()

    def get_ready_issues(self, team_key: str) -> List[LinearIssue]:
        """Fetch issues in the 'AI: Ready' state."""
        query = '''
        query ReadyIssues($teamKey: String!) {
            issues(filter: {
                team: { key: { eq: $teamKey } }
                state: { name: { eq: "AI: Ready" } }
            }) {
                nodes {
                    id
                    identifier
                    title
                    description
                    state { name }
                    priority
                    parent { id }
                }
            }
        }
        '''
        result = self._query(query, {"teamKey": team_key})
        issues = result.get("data", {}).get("issues", {}).get("nodes", [])

        return [
            LinearIssue(
                id=issue["id"],
                identifier=issue["identifier"],
                title=issue["title"],
                description=issue.get("description"),
                state=issue["state"]["name"],
                priority=issue["priority"],
                parent_id=issue.get("parent", {}).get("id") if issue.get("parent") else None
            )
            for issue in issues
        ]

    def transition_issue(self, issue_id: str, state_name: str) -> bool:
        """Move an issue to a different state."""
        # First, get the state ID
        state_query = '''
        query GetState($name: String!) {
            workflowStates(filter: { name: { eq: $name } }) {
                nodes { id }
            }
        }
        '''
        state_result = self._query(state_query, {"name": state_name})
        states = state_result.get("data", {}).get("workflowStates", {}).get("nodes", [])

        if not states:
            return False

        state_id = states[0]["id"]

        mutation = '''
        mutation UpdateIssue($id: String!, $stateId: String!) {
            issueUpdate(id: $id, input: { stateId: $stateId }) {
                success
            }
        }
        '''
        result = self._query(mutation, {"id": issue_id, "stateId": state_id})
        return result.get("data", {}).get("issueUpdate", {}).get("success", False)

    def add_comment(self, issue_id: str, body: str) -> bool:
        """Add a comment to an issue."""
        mutation = '''
        mutation AddComment($issueId: String!, $body: String!) {
            commentCreate(input: { issueId: $issueId, body: $body }) {
                success
            }
        }
        '''
        result = self._query(mutation, {"issueId": issue_id, "body": body})
        return result.get("data", {}).get("commentCreate", {}).get("success", False)
