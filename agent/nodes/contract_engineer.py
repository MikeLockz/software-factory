import json
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from agent.state import AgentState
from agent.config.context import get_context_for_prompt

load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

CONTRACTOR_PROMPT = """You are a Software Contract Designer.
Your job is to take a task description and produce a Pydantic-style data contract.

{project_context}

Task: {task_description}

Previous feedback to address:
{feedback}

Output ONLY a JSON object with these exact keys:
- "name": The contract/model name (PascalCase)
- "fields": A dict of field_name -> field_type with descriptions
- "description": What this contract represents

Be precise. Think about edge cases and validation rules.
Output raw JSON only, no markdown code blocks.
"""


def contract_engineer_node(state: AgentState) -> dict:
    """Generate or refine a data contract based on the task."""
    feedback_list = state.get("review_feedback", [])
    feedback_str = "\n".join(
        f"- [{fb.agent}]: {', '.join(fb.concerns)}"
        for fb in feedback_list
        if not fb.approved
    ) or "None - this is the first draft."

    prompt = CONTRACTOR_PROMPT.format(
        project_context=get_context_for_prompt(),
        task_description=state["task_description"],
        feedback=feedback_str
    )

    response = llm.invoke(prompt)
    content = response.content
    if isinstance(content, list):
        content = content[0] if content else ""
    content = content.strip()

    # Strip markdown code blocks if present
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\n?", "", content)
        content = re.sub(r"\n?```$", "", content)

    # Validate JSON
    try:
        json.loads(content)
    except json.JSONDecodeError:
        content = json.dumps({
            "name": "ParseError",
            "fields": {},
            "description": f"Failed to parse: {content[:200]}"
        })

    return {
        "current_contract": content,
        "status": "reviewing",
        "iteration_count": state.get("iteration_count", 0) + 1,
        "review_feedback": []  # Clear for new review cycle
    }
