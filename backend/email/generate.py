"""Email draft generation using Claude API."""

import anthropic
from backend.email.prompt import build_system_prompt, build_user_prompt

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 300


def _parse_subject(raw: str, company_name: str) -> tuple[str, str]:
    """Parse SUBJECT: prefix from LLM response. Returns (subject_line, body)."""
    lines = raw.strip().split("\n", 1)
    first_line = lines[0].strip()

    if first_line.upper().startswith("SUBJECT:"):
        subject = first_line[len("SUBJECT:"):].strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        if subject:
            return subject, body

    return f"Quick question - {company_name}", raw.strip()


def generate_draft(
    student_bio: str,
    repo_summaries: list[dict],
    student_interests: list[str],
    signature_links: dict,
    company_name: str,
    company_summary: str,
    specific_projects: list[str],
    founder_name: str,
    founder_bio: str | None = None,
    tone: str = "curious",
) -> tuple[str, str]:
    """Generate a cold email draft using Claude.

    Returns (subject_line, draft_body).
    """
    system = build_system_prompt()
    user = build_user_prompt(
        student_bio=student_bio,
        repo_summaries=repo_summaries,
        student_interests=student_interests,
        signature_links=signature_links,
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
        system=system,
        messages=[{"role": "user", "content": user}],
    )

    raw = response.content[0].text
    return _parse_subject(raw, company_name)
