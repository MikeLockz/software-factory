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

    def update_issue_description(self, issue_id: str, description: str) -> bool:
        """Update an issue's description."""
        mutation = '''
        mutation UpdateIssueDescription($id: String!, $description: String!) {
            issueUpdate(id: $id, input: { description: $description }) {
                success
            }
        }
        '''
        result = self._query(mutation, {"id": issue_id, "description": description})
        return result.get("data", {}).get("issueUpdate", {}).get("success", False)

    def get_team_id(self, team_key: str) -> Optional[str]:
        """Get team ID by team key."""
        query = '''
        query GetTeam($key: String!) {
            teams(filter: { key: { eq: $key } }) {
                nodes { id }
            }
        }
        '''
        result = self._query(query, {"key": team_key})
        teams = result.get("data", {}).get("teams", {}).get("nodes", [])
        return teams[0]["id"] if teams else None

    def create_sub_issue(
        self,
        parent_id: str,
        team_key: str,
        title: str,
        description: str,
        state_name: str = "Human: Technical Review"
    ) -> Optional[LinearIssue]:
        """Create a sub-issue under a parent issue."""
        # Get team ID
        team_id = self.get_team_id(team_key)
        if not team_id:
            print(f"Could not find team with key: {team_key}")
            return None

        # Get state ID for initial state
        state_query = '''
        query GetState($name: String!) {
            workflowStates(filter: { name: { eq: $name } }) {
                nodes { id }
            }
        }
        '''
        state_result = self._query(state_query, {"name": state_name})
        states = state_result.get("data", {}).get("workflowStates", {}).get("nodes", [])
        state_id = states[0]["id"] if states else None

        # Create the sub-issue
        mutation = '''
        mutation CreateSubIssue($teamId: String!, $title: String!, $description: String!, $parentId: String!, $stateId: String) {
            issueCreate(input: {
                teamId: $teamId
                title: $title
                description: $description
                parentId: $parentId
                stateId: $stateId
            }) {
                success
                issue {
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
        variables = {
            "teamId": team_id,
            "title": title,
            "description": description,
            "parentId": parent_id
        }
        if state_id:
            variables["stateId"] = state_id

        result = self._query(mutation, variables)
        issue_data = result.get("data", {}).get("issueCreate", {})

        if not issue_data.get("success"):
            print(f"Failed to create sub-issue: {result}")
            return None

        issue = issue_data.get("issue", {})
        return LinearIssue(
            id=issue["id"],
            identifier=issue["identifier"],
            title=issue["title"],
            description=issue.get("description"),
            state=issue["state"]["name"],
            priority=issue.get("priority", 0),
            parent_id=issue.get("parent", {}).get("id") if issue.get("parent") else None
        )

    def create_workflow_state(
        self,
        team_key: str,
        name: str,
        color: str = "#95a2b3",
        state_type: str = "started",
        description: str = ""
    ) -> Optional[str]:
        """Create a new workflow state for a team.
        
        Args:
            team_key: Team key (e.g., "ENG")
            name: Name of the state (e.g., "Human: Review")
            color: Hex color code (default: gray)
            state_type: One of: backlog, unstarted, started, completed, canceled
            description: Optional description
            
        Returns:
            State ID if created, None if failed
        """
        team_id = self.get_team_id(team_key)
        if not team_id:
            print(f"Could not find team with key: {team_key}")
            return None

        mutation = '''
        mutation CreateWorkflowState($teamId: String!, $name: String!, $color: String!, $type: String!, $description: String) {
            workflowStateCreate(input: {
                teamId: $teamId
                name: $name
                color: $color
                type: $type
                description: $description
            }) {
                success
                workflowState {
                    id
                    name
                }
            }
        }
        '''
        result = self._query(mutation, {
            "teamId": team_id,
            "name": name,
            "color": color,
            "type": state_type,
            "description": description
        })
        
        state_data = result.get("data", {}).get("workflowStateCreate", {})
        if state_data.get("success"):
            state = state_data.get("workflowState", {})
            print(f"✅ Created workflow state: {state.get('name')} ({state.get('id')})")
            return state.get("id")
        else:
            errors = result.get("errors", [])
            print(f"Failed to create workflow state: {errors}")
            return None

    def get_workflow_states(self, team_key: str) -> List[str]:
        """Get all workflow state names for a team."""
        team_id = self.get_team_id(team_key)
        if not team_id:
            return []
            
        query = '''
        query GetStates($teamId: String!) {
            team(id: $teamId) {
                states {
                    nodes {
                        name
                    }
                }
            }
        }
        '''
        result = self._query(query, {"teamId": team_id})
        states = result.get("data", {}).get("team", {}).get("states", {}).get("nodes", [])
        return [s["name"] for s in states]

    def ensure_workflow_states(self, team_key: str) -> dict:
        """Ensure required workflow states exist for the AI factory.
        
        Creates any missing states from the required set.
        
        Returns:
            Dict of state name -> created (True) or already existed (False)
        """
        required_states = [
            {"name": "AI: Ready", "color": "#5e6ad2", "type": "unstarted", 
             "description": "Ready for AI processing"},
            {"name": "AI: In Progress", "color": "#f2c94c", "type": "started",
             "description": "AI is currently working on this issue"},
            {"name": "AI: Review", "color": "#26b5ce", "type": "started",
             "description": "AI completed work, ready for code review"},
            {"name": "AI: Failed", "color": "#eb5757", "type": "started",
             "description": "AI encountered an error"},
            {"name": "AI: Awaiting Sub-task", "color": "#95a2b3", "type": "started",
             "description": "Waiting for sub-task to be completed"},
            {"name": "Human: Review", "color": "#bb87fc", "type": "started",
             "description": "Waiting for human review/approval"},
        ]
        
        existing = set(self.get_workflow_states(team_key))
        results = {}
        
        for state in required_states:
            if state["name"] in existing:
                print(f"   ✓ {state['name']} already exists")
                results[state["name"]] = False
            else:
                created = self.create_workflow_state(
                    team_key=team_key,
                    name=state["name"],
                    color=state["color"],
                    state_type=state["type"],
                    description=state["description"]
                )
                results[state["name"]] = created is not None
                
        return results

