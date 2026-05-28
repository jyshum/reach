"""Tests for the interest-aligned email prompt."""

from backend.email.prompt import build_email_prompt, TONES


def test_prompt_includes_student_projects():
    result = build_email_prompt(
        student_bio="HS junior",
        student_projects="Built a CNN plant disease classifier using PyTorch",
        student_interests=["Generative AI", "Healthcare"],
        portfolio_url="https://alice.dev",
        github_url="https://github.com/alice",
        resume_url=None,
        company_name="Pando Bioscience",
        company_summary="AI-driven enzyme engineering",
        specific_projects=["Enzyme screening pipeline"],
        founder_name="Will Cao",
        founder_bio="Will changed her major from engineering machines to engineering bacteria.",
        tone="curious",
    )
    assert "plant disease classifier" in result
    assert "Pando Bioscience" in result
    assert "Will Cao" in result
    assert "alice.dev" in result
    assert "github.com/alice" in result


def test_prompt_includes_founder_bio():
    result = build_email_prompt(
        student_bio="Student",
        student_projects=None,
        student_interests=["Developer Tools"],
        portfolio_url=None,
        github_url=None,
        resume_url=None,
        company_name="TestCo",
        company_summary="Dev tools for teams",
        specific_projects=[],
        founder_name="Bob",
        founder_bio="Bob spent 10 years at Google building infrastructure tools.",
        tone="friendly",
    )
    assert "10 years at Google" in result


def test_prompt_handles_all_none_optionals():
    result = build_email_prompt(
        student_bio="Student",
        student_projects=None,
        student_interests=[],
        portfolio_url=None,
        github_url=None,
        resume_url=None,
        company_name="TestCo",
        company_summary="Building things",
        specific_projects=[],
        founder_name="Sam",
        founder_bio=None,
        tone="curious",
    )
    assert "TestCo" in result
    assert "Sam" in result


def test_prompt_includes_resume_url():
    result = build_email_prompt(
        student_bio="Student",
        student_projects=None,
        student_interests=[],
        portfolio_url=None,
        github_url=None,
        resume_url="https://docs.google.com/my-resume",
        company_name="TestCo",
        company_summary="Building things",
        specific_projects=[],
        founder_name="Sam",
        founder_bio=None,
        tone="earnest",
    )
    assert "docs.google.com/my-resume" in result


def test_tone_changes_voice():
    base = dict(
        student_bio="Student",
        student_projects=None,
        student_interests=[],
        portfolio_url=None,
        github_url=None,
        resume_url=None,
        company_name="TestCo",
        company_summary="Test",
        specific_projects=[],
        founder_name="Sam",
        founder_bio=None,
    )
    curious = build_email_prompt(**base, tone="curious")
    scrappy = build_email_prompt(**base, tone="scrappy")
    assert "curious" in curious.lower()
    assert "Resourceful" in scrappy


def test_prompt_emphasizes_domain_alignment():
    result = build_email_prompt(
        student_bio="Student",
        student_projects="Built a trading bot",
        student_interests=["Fintech", "Payments"],
        portfolio_url=None,
        github_url=None,
        resume_url=None,
        company_name="PayCo",
        company_summary="Payment infrastructure for SMBs",
        specific_projects=[],
        founder_name="Jane",
        founder_bio=None,
        tone="curious",
    )
    # Prompt should emphasize interest alignment, not skill-gap filling
    assert "interest" in result.lower() or "into" in result.lower() or "domain" in result.lower()
