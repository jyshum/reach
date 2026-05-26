"""Prompt template for cold email generation."""


def build_email_prompt(
    student_bio: str,
    student_capabilities: list[str],
    company_name: str,
    company_summary: str,
    specific_projects: list[str],
    founder_name: str,
    guidance_angle: str | None = None,
) -> str:
    """Build a prompt for generating a cold email draft.

    Returns the full prompt string to send to an LLM.
    """
    projects_text = ""
    if specific_projects:
        projects_text = "They need help with: " + "; ".join(specific_projects) + "."

    angle_text = ""
    if guidance_angle:
        angle_text = f"\nAngle to lead with: {guidance_angle}"

    return f"""Write a cold email from a student to a startup founder.

STRICT RULES:
- Maximum 4-5 sentences. Shorter is better.
- Sound like a real student, not a professional. Casual but respectful.
- NO filler enthusiasm ("I'm really excited", "I'd love to", "I'm passionate about")
- NO compliments about the company ("I admire your work", "Your company is amazing")
- Include ONE specific hook showing you actually understand what they build
- End with a concrete, low-commitment ask (e.g. "Could I spend 2 hours this week on X?")
- Do NOT use a formal sign-off. Just the student's first name.

STUDENT CONTEXT:
Bio: {student_bio}
Capabilities: {", ".join(student_capabilities)}
{angle_text}

COMPANY CONTEXT:
Company: {company_name}
Founder: {founder_name}
What they do: {company_summary}
{projects_text}

Write the email body only. No subject line. No "Dear" or "Hi {founder_name}," — start directly with the hook."""
