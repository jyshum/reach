"""Prompt template for cold email generation.

Email angle: interest/domain alignment — "I'm into the same stuff
you're building" rather than "I can help with X."
"""

TONES = {
    "curious": {
        "label": "Curious",
        "voice": "Genuinely curious and a bit nerdy. You're interested in their problem and want to learn by helping. Humble but not timid.",
        "ask": 'End with a question about their work that opens a conversation (e.g. "I\'m curious how you handle X — could I take a look and share what I find?")',
    },
    "friendly": {
        "label": "Friendly",
        "voice": "Warm and personable. You come across as someone who would be fun to work with. Light touch, not overly casual.",
        "ask": 'End with a low-pressure suggestion (e.g. "Happy to hop on a quick call if you want to chat about it")',
    },
    "scrappy": {
        "label": "Scrappy",
        "voice": "Resourceful and action-oriented. You've already tried things, built things, figured things out on your own. You're not asking for permission — you're showing up with proof of work.",
        "ask": 'End by offering something concrete you\'ve already done or could do immediately (e.g. "I already prototyped X — want me to send it over?")',
    },
    "earnest": {
        "label": "Earnest",
        "voice": "Sincere and straightforward. You genuinely care about the problem they're solving and want to contribute meaningfully. No games, no tricks — just honest interest.",
        "ask": 'End with a simple, direct ask that shows commitment (e.g. "I\'d be glad to put in a few hours on X if that would be useful")',
    },
}

DEFAULT_TONE = "curious"


def build_email_prompt(
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
    tone: str = DEFAULT_TONE,
) -> str:
    """Build a prompt for generating a cold email draft."""
    tone_config = TONES.get(tone, TONES[DEFAULT_TONE])

    # Student context
    projects_section = ""
    if student_projects:
        projects_section = f"\nProjects: {student_projects}"

    interests_section = ""
    if student_interests:
        interests_section = f"\nDomain interests: {', '.join(student_interests)}"

    links_section = ""
    links = []
    if portfolio_url:
        links.append(f"Portfolio: {portfolio_url}")
    if github_url:
        links.append(f"GitHub: {github_url}")
    if resume_url:
        links.append(f"Resume: {resume_url}")
    if links:
        links_section = "\nLinks (include naturally if relevant, don't force all of them): " + " | ".join(links)

    # Founder context
    founder_bio_section = ""
    if founder_bio:
        founder_bio_section = f"\nFounder background: {founder_bio}"

    company_projects_section = ""
    if specific_projects:
        company_projects_section = "\nThey need help with: " + "; ".join(specific_projects)

    return f"""Write a cold email from a high school student to a startup founder.

VOICE: {tone_config["voice"]}

STRICT RULES:
- Open by establishing you're a high school student (this is your biggest pattern interrupt — founders don't get emails from high schoolers).
- Maximum 4-5 sentences. Shorter is better.
- Sound like a real student, not a professional.
- NO filler enthusiasm ("I'm really excited", "I'd love to", "I'm passionate about")
- NO compliments about the company ("I admire your work", "Your company is amazing")
- Show genuine interest in their DOMAIN — you care about the same problems they're solving
- If the student has built something relevant, reference it as proof of genuine interest (not as a credential)
- Include ONE specific hook showing you actually understand what they build
- {tone_config["ask"]}
- Do NOT use a formal sign-off. Just the student's first name.

STUDENT CONTEXT:
Bio: {student_bio}{projects_section}{interests_section}{links_section}

COMPANY CONTEXT:
Company: {company_name}
Founder: {founder_name}{founder_bio_section}
What they do: {company_summary}{company_projects_section}

Write the email body only. No subject line. No "Dear" or "Hi {founder_name}," — start directly with the hook."""
