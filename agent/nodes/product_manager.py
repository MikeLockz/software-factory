"""Product Manager Agent - converts vague user ideas into structured PRDs with acceptance criteria."""
import json
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from agent.state import AgentState
from agent.config.context import get_context_for_prompt

load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.3)

PRODUCT_MANAGER_PROMPT = """You are a Senior Product Manager creating a Product Requirements Document.

{project_context}

User Request:
{user_request}

Previous Feedback (if any):
{feedback}

Create a comprehensive PRD with:

IMPORTANT:
- STRICTLY ADHERE to the user request.
- Do NOT halluncinate or invent features that are not explicitly asked for or strictly necessary.
- If the request is simple, keep the PRD simple and focused.
- Avoid "padding" the PRD with generic features (e.g., "User Authentication" or "Dashboard") unless requested.

1. **Problem Statement**: What problem does this solve? Who is affected?
2. **User Stories**: 3-5 user stories in "As a [user], I want [goal], so that [benefit]" format (ONLY relevant stories). Assign a unique ID to each (e.g., "US-1").
3. **Acceptance Criteria**: For EACH user story, write 1-3 Gherkin-formatted scenarios using Given/When/Then syntax. These must be in a separate list, linked by User Story ID.
4. **Edge Cases**: What could go wrong? What are the boundary conditions?
5. **Out of Scope**: What are we explicitly NOT building?
6. **Success Metrics**: How do we measure success?

Output JSON:
{{
  "title": "Feature title",
  "problem_statement": "Clear problem description",
  "user_stories": [
    {{
      "id": "US-1",
      "as_a": "user type",
      "i_want": "goal",
      "so_that": "benefit"
    }}
  ],
  "acceptance_criteria": [
    {{
      "id": "AC-1",
      "story_id": "US-1",
      "scenario": "Descriptive scenario name",
      "given": "the initial context or precondition",
      "when": "the action or trigger occurs",
      "then": "the expected outcome or result"
    }}
  ],
  "edge_cases": ["edge case 1", "edge case 2"],
  "out_of_scope": ["exclusion 1", "exclusion 2"],
  "success_metrics": ["metric 1", "metric 2"],
  "priority": "P0|P1|P2",
  "estimated_complexity": "S|M|L|XL"
}}
"""


def product_manager_node(state: AgentState) -> dict:
    """Generate a structured PRD from user input."""
    feedback = state.get("prd_feedback") or "None - first draft"

    prompt = PRODUCT_MANAGER_PROMPT.format(
        project_context=get_context_for_prompt(),
        user_request=state["task_description"],
        feedback=feedback
    )

    response = llm.invoke(prompt)
    content = response.content
    if isinstance(content, list):
        content = content[0] if content else ""
    content = content.strip()

    # Strip markdown
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\n?", "", content)
        content = re.sub(r"\n?```$", "", content)

    try:
        prd = json.loads(content)
        if prd is None:
             raise ValueError("Parsed JSON is null")
             
        print(f"   📋 Product Manager created PRD: {prd.get('title', 'Untitled')}")
        print(f"      User stories: {len(prd.get('user_stories', []))}")
        print(f"      Priority: {prd.get('priority', 'P1')} | Complexity: {prd.get('estimated_complexity', 'M')}")
    except (json.JSONDecodeError, ValueError) as e:
        prd = {"error": "Failed to parse PRD", "raw": content[:500]}
        print(f"   ⚠️ Product Manager could not parse PRD response: {e}")

    return {
        "prd": prd,
        "status": "prd_ready",
        "messages": state.get("messages", []) + ["Product Manager created PRD"]
    }
