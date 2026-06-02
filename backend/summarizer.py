"""Summarize a GitHub repo using Claude Haiku for cold email context."""

import anthropic


def summarize_repo(
    repo_name: str,
    readme: str,
    language: str | None,
    description: str | None,
    stars: int,
) -> str:
    """Call Haiku to produce a 2-3 sentence summary of a GitHub project.

    Cost: ~$0.001 per call.
    """
    context_parts = [f"Project: {repo_name}"]
    if language:
        context_parts.append(f"Language: {language}")
    if description:
        context_parts.append(f"Description: {description}")
    context_parts.append(f"Stars: {stars}")
    context_parts.append(f"\nREADME:\n{readme}")

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[
            {
                "role": "user",
                "content": (
                    "Summarize this GitHub project in 2-3 sentences for a cold email. "
                    "Focus on what it does, the tech used, and what's impressive about it.\n\n"
                    + "\n".join(context_parts)
                ),
            },
        ],
    )
    return response.content[0].text
