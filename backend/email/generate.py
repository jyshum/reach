"""Email draft generation using Claude API."""

import anthropic
from backend.email.prompt import build_email_prompt

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 300


def generate_draft(
    student_bio: str,
    student_capabilities: list[str],
    company_name: str,
    company_summary: str,
    specific_projects: list[str],
    founder_name: str,
    tone: str = "curious",
    guidance_angle: str | None = None,
) -> str:
    """Generate a cold email draft using Claude. Returns the draft text."""
    prompt = build_email_prompt(
        student_bio=student_bio,
        student_capabilities=student_capabilities,
        company_name=company_name,
        company_summary=company_summary,
        specific_projects=specific_projects,
        founder_name=founder_name,
        guidance_angle=guidance_angle,
        tone=tone,
    )

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text
