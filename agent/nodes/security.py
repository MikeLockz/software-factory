import json
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from agent.state import AgentState, ReviewFeedback

load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)

SECURITY_PROMPT = """You are a Security Engineer reviewing a data contract for a healthcare application.

Contract under review:
{contract}

Check for these critical issues only:
1. PII fields without any validation mention
2. Obvious injection risks (raw SQL, unsanitized HTML)
3. Missing required field types (dates as strings without format)

Respond with ONLY a JSON object (no markdown):
{{
  "approved": true or false,
  "concerns": ["list of CRITICAL security issues only"],
  "suggestions": ["list of recommended improvements"]
}}

IMPORTANT: Be pragmatic. Approve the contract if it addresses basic security.
Minor improvements can be noted as suggestions without blocking approval.
If fields mention validation, sanitization, or proper types, that's sufficient.
"""


def security_node(state: AgentState) -> dict:
    """Review the contract for security issues."""
    prompt = SECURITY_PROMPT.format(
        contract=state.get("current_contract", "{}")
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

    # Parse the response
    try:
        data = json.loads(content)
        feedback = ReviewFeedback(
            agent="security",
            approved=data.get("approved", False),
            concerns=data.get("concerns", []),
            suggestions=data.get("suggestions", [])
        )
    except (json.JSONDecodeError, ValueError):
        feedback = ReviewFeedback(
            agent="security",
            approved=False,
            concerns=["Failed to parse security review response"],
            suggestions=["Retry the review"]
        )

    existing_feedback = state.get("review_feedback", [])

    return {
        "review_feedback": existing_feedback + [feedback]
    }
