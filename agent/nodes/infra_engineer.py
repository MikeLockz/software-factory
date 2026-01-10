import json
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from agent.state import AgentState
from agent.config.context import get_context_for_prompt

load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-001", temperature=0)

INFRA_ENGINEER_PROMPT = """You are an Infrastructure Engineer.
Your job is to take an infrastructure task and produce implementation artifacts.

{project_context}

Task: {task_description}

Previous feedback to address:
{feedback}

Output ONLY a JSON object with these exact keys:
- "name": The artifact name (snake_case)
- "type": The type of artifact (e.g., "dockerfile", "ci_config", "script", "config")
- "content": The actual file content as a string
- "description": What this artifact does

Be precise. Follow infrastructure best practices.
Output raw JSON only, no markdown code blocks.
"""


def infra_engineer_node(state: AgentState) -> dict:
    """Generate infrastructure artifacts based on the task."""
    feedback_list = state.get("review_feedback", [])
    feedback_str = "\n".join(
        f"- [{fb.agent}]: {', '.join(fb.concerns)}"
        for fb in feedback_list
        if not fb.approved
    ) or "None - this is the first draft."

    prompt = INFRA_ENGINEER_PROMPT.format(
        project_context=get_context_for_prompt(),
        task_description=state["task_description"],
        feedback=feedback_str
    )

    response = llm.invoke(prompt)
    content = response.content
    if isinstance(content, list):
        content = content[0] if content else ""
    content = content.strip()

    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\n?", "", content)
        content = re.sub(r"\n?```$", "", content)

    try:
        json.loads(content)
    except json.JSONDecodeError:
        content = json.dumps({
            "name": "parse_error",
            "type": "error",
            "content": "",
            "description": f"Failed to parse: {content[:200]}"
        })

    return {
        "current_contract": content,
        "status": "reviewing",
        "iteration_count": state.get("iteration_count", 0) + 1,
        "review_feedback": []
    }
