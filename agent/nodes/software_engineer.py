import json
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from agent.state import AgentState

load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)

SOFTWARE_ENGINEER_PROMPT = """You are a Software Engineer.
Your job is to take a feature request and produce code implementation artifacts.

Task: {task_description}

Previous feedback to address:
{feedback}

Output ONLY a JSON object with these exact keys:
- "name": The module/component name (snake_case)
- "type": The type of artifact (e.g., "module", "component", "service", "utility")
- "language": Programming language (e.g., "python", "typescript")
- "content": The actual code content as a string
- "description": What this code does

Be precise. Follow clean code principles.
Output raw JSON only, no markdown code blocks.
"""


def software_engineer_node(state: AgentState) -> dict:
    """Generate code implementations based on the task."""
    feedback_list = state.get("review_feedback", [])
    feedback_str = "\n".join(
        f"- [{fb.agent}]: {', '.join(fb.concerns)}"
        for fb in feedback_list
        if not fb.approved
    ) or "None - this is the first draft."

    prompt = SOFTWARE_ENGINEER_PROMPT.format(
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
            "language": "unknown",
            "content": "",
            "description": f"Failed to parse: {content[:200]}"
        })

    return {
        "current_contract": content,
        "status": "reviewing",
        "iteration_count": state.get("iteration_count", 0) + 1,
        "review_feedback": []
    }
