"""Prompt template for cold email generation.

Split into system prompt (stable rules) and user prompt (per-call context).
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


def build_system_prompt() -> str:
    """Build the system prompt with stable rules for email generation."""
    return """You write cold emails from high school students to startup founders.

RULES:
- Open by establishing you're a high school student. This is your biggest pattern interrupt — founders don't get emails from high schoolers.
- Maximum 4-5 sentences. Shorter is better.
- Sound like a real student, not a professional.
- NO filler enthusiasm ("I'm really excited", "I'd love to", "I'm passionate about")
- NO compliments about the company ("I admire your work", "Your company is amazing")
- Show genuine interest in the founder's DOMAIN — you care about the same problems they're solving.
- If the student has projects, reference at most one — pick the one most relevant to the founder's domain. Don't just name-drop it; connect it to what the founder is building.
- Include ONE specific hook showing you actually understand what they build.
- Do NOT use a formal sign-off. Just the student's first name.
- After the name, add a signature line with the provided links (only include links that are provided). Format: "GitHub: url | Resume: url" on its own line. Do not put links anywhere in the email body.

OUTPUT FORMAT:
- First line: SUBJECT: <subject line, under 8 words, specific to this founder>
- Then a blank line
- Then the email body (including first name sign-off and signature line)"""


def build_user_prompt(
    student_bio: str,
    repo_summaries: list[dict],
    student_interests: list[str],
    signature_links: dict,
    company_name: str,
    company_summary: str,
    specific_projects: list[str],
    founder_name: str,
    founder_bio: str | None = None,
    tone: str = DEFAULT_TONE,
) -> str:
    """Build the user prompt with per-call context."""
    tone_config = TONES.get(tone, TONES[DEFAULT_TONE])

    # Repo summaries
    repos_section = ""
    if repo_summaries:
        lines = []
        for r in repo_summaries:
            parts = [r["repo_name"]]
            if r.get("language"):
                parts[0] += f" ({r['language']}"
                if r.get("stars", 0) > 0:
                    parts[0] += f", {r['stars']} stars"
                parts[0] += ")"
            elif r.get("stars", 0) > 0:
                parts[0] += f" ({r['stars']} stars)"
            lines.append(f"- {parts[0]}: {r['summary']}")
        repos_section = "\nProjects:\n" + "\n".join(lines)

    # Interests
    interests_section = ""
    if student_interests:
        interests_section = f"\nDomain interests: {', '.join(student_interests)}"

    # Signature links
    sig_section = ""
    sig_lines = []
    if signature_links.get("github_url"):
        sig_lines.append(f"GitHub: {signature_links['github_url']}")
    if signature_links.get("resume_url"):
        sig_lines.append(f"Resume: {signature_links['resume_url']}")
    if signature_links.get("portfolio_url"):
        sig_lines.append(f"Portfolio: {signature_links['portfolio_url']}")
    if sig_lines:
        sig_section = "\n\nSIGNATURE LINKS (for the sign-off line, NOT the email body):\n" + "\n".join(sig_lines)

    # Founder context
    founder_bio_section = ""
    if founder_bio:
        founder_bio_section = f"\nFounder background: {founder_bio}"

    company_projects_section = ""
    if specific_projects:
        company_projects_section = "\nThey need help with: " + "; ".join(specific_projects)

    return f"""TONE: {tone_config["voice"]}
ASK: {tone_config["ask"]}

STUDENT:
Bio: {student_bio}{repos_section}{interests_section}{sig_section}

COMPANY:
Company: {company_name}
Founder: {founder_name}{founder_bio_section}
What they do: {company_summary}{company_projects_section}

Write the email."""
