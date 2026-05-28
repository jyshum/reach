"""Email draft generation using Claude API."""

import anthropic
from backend.email.prompt import build_email_prompt

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 300


def generate_draft(
    student_bio: str,
    student_projects: str | None,
    student_interests: list[str],
    portfolio_url: str | None,
    github_url: str | None,
    resume_url: str | None,
    company_name: str,
    company_summary: str,
    specific_projects: list[str],
    founder_name: str,
    founder_bio: str | None = None,
    tone: str = "curious",
) -> str:
    """Generate a cold email draft using Claude. Returns the draft text."""
    prompt = build_email_prompt(
        student_bio=student_bio,
        student_projects=student_projects,
        student_interests=student_interests,
        portfolio_url=portfolio_url,
        github_url=github_url,
        resume_url=resume_url,
        company_name=company_name,
        company_summary=company_summary,
        specific_projects=specific_projects,
        founder_name=founder_name,
        founder_bio=founder_bio,
        tone=tone,
    )

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text
