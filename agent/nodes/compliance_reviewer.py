import json
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from agent.state import AgentState, ReviewFeedback

load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

COMPLIANCE_PROMPT = """You are a Compliance Officer reviewing code for regulatory requirements.

Content under review:
{content}

Check for:
1. GDPR compliance (data retention, right to erasure, consent)
2. HIPAA (if healthcare data)
3. Accessibility (WCAG 2.1 AA)
4. Proper error logging (no PII in logs)
5. Audit trail requirements

Respond with JSON only:
{{
  "approved": true or false,
  "concerns": ["list of compliance issues"],
  "suggestions": ["list of recommendations"]
}}

Approve if no critical compliance violations exist.
"""


def compliance_reviewer_node(state: AgentState) -> dict:
    """Review for compliance issues."""
    content = state.get("current_contract") or ""

    prompt = COMPLIANCE_PROMPT.format(content=content)
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
            agent="compliance",
            approved=data.get("approved", False),
            concerns=data.get("concerns", []),
            suggestions=data.get("suggestions", [])
        )
    except (json.JSONDecodeError, ValueError):
        feedback = ReviewFeedback(
            agent="compliance",
            approved=False,
            concerns=["Failed to parse compliance review"],
            suggestions=[]
        )

    print(f"   📋 Compliance: {'✅ Approved' if feedback.approved else '❌ Issues found'}")

    existing = state.get("review_feedback", [])
    return {"review_feedback": existing + [feedback]}
