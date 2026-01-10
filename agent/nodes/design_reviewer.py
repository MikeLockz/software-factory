import json
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from agent.state import AgentState, ReviewFeedback

load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

DESIGN_PROMPT = """You are a Design System Purist reviewing frontend code.

Code under review:
{content}

Check for:
1. Component reusability (no inline styles, proper composition)
2. Design token usage (colors, spacing, typography from system)
3. Accessibility (aria labels, keyboard navigation, focus states)
4. Responsive design (mobile-first, breakpoints)
5. Consistent naming conventions

Respond with JSON only:
{{
  "approved": true or false,
  "concerns": ["list of design issues"],
  "suggestions": ["list of recommendations"]
}}

Approve if the code follows reasonable design patterns.
"""


def design_reviewer_node(state: AgentState) -> dict:
    """Review frontend code for design consistency."""
    content = state.get("current_contract") or ""

    prompt = DESIGN_PROMPT.format(content=content)
    response = llm.invoke(prompt)

    resp_content = response.content
    if isinstance(resp_content, list):
        resp_content = resp_content[0] if resp_content else ""
    resp_content = resp_content.strip()

    if resp_content.startswith("```"):
        resp_content = re.sub(r"^```(?:json)?\n?", "", resp_content)
        resp_content = re.sub(r"\n?```$", "", resp_content)

    try:
        data = json.loads(resp_content)
        feedback = ReviewFeedback(
            agent="design",
            approved=data.get("approved", False),
            concerns=data.get("concerns", []),
            suggestions=data.get("suggestions", [])
        )
    except (json.JSONDecodeError, ValueError):
        feedback = ReviewFeedback(
            agent="design",
            approved=False,
            concerns=["Failed to parse design review"],
            suggestions=[]
        )

    print(f"   🎨 Design: {'✅ Approved' if feedback.approved else '❌ Issues found'}")

    existing = state.get("review_feedback", [])
    return {"review_feedback": existing + [feedback]}
