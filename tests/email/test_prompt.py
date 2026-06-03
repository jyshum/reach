"""Tests for the email prompt builder."""

from backend.email.prompt import build_system_prompt, build_user_prompt, TONES


def test_system_prompt_contains_rules():
    system = build_system_prompt()
    assert "high school" in system.lower()
    assert "4-5 sentences" in system
    assert "SUBJECT:" in system
    assert "at most one" in system  # repo rule


def test_system_prompt_contains_signature_rule():
    system = build_system_prompt()
    assert "signature" in system.lower()


def test_user_prompt_includes_bio():
    result = build_user_prompt(
        student_bio="I'm a junior at Lincoln High. Writing Python scrapers. I'm interested in NLP.",
        repo_summaries=[],
        student_interests=["Generative AI"],
        signature_links={},
        company_name="Pando Bio",
        company_summary="AI enzyme design",
        specific_projects=["Enzyme screening pipeline"],
        founder_name="Will Cao",
        founder_bio="Will changed her major from engineering machines to engineering bacteria.",
        tone="curious",
    )
    assert "junior at Lincoln High" in result
    assert "Pando Bio" in result
    assert "Will Cao" in result
    assert "engineering bacteria" in result


def test_user_prompt_includes_repo_summaries():
    result = build_user_prompt(
        student_bio="Student",
        repo_summaries=[
            {"repo_name": "trading-bot", "summary": "A Python bot for crypto.", "language": "Python", "stars": 12},
            {"repo_name": "scraper", "summary": "Web scraper for pricing data.", "language": "JavaScript", "stars": 0},
        ],
        student_interests=[],
        signature_links={},
        company_name="TestCo",
        company_summary="Test",
        specific_projects=[],
        founder_name="Sam",
        tone="curious",
    )
    assert "trading-bot" in result
    assert "Python bot for crypto" in result
    assert "scraper" in result


def test_user_prompt_omits_repos_when_empty():
    result = build_user_prompt(
        student_bio="Student",
        repo_summaries=[],
        student_interests=[],
        signature_links={},
        company_name="TestCo",
        company_summary="Test",
        specific_projects=[],
        founder_name="Sam",
        tone="curious",
    )
    assert "Projects:" not in result


def test_user_prompt_includes_signature_links():
    result = build_user_prompt(
        student_bio="Student",
        repo_summaries=[],
        student_interests=[],
        signature_links={
            "github_url": "https://github.com/alice",
            "resume_url": "https://storage.example.com/resume.pdf",
        },
        company_name="TestCo",
        company_summary="Test",
        specific_projects=[],
        founder_name="Sam",
        tone="curious",
    )
    assert "github.com/alice" in result
    assert "resume.pdf" in result
    assert "SIGNATURE LINKS" in result


def test_user_prompt_omits_signature_section_when_no_links():
    result = build_user_prompt(
        student_bio="Student",
        repo_summaries=[],
        student_interests=[],
        signature_links={},
        company_name="TestCo",
        company_summary="Test",
        specific_projects=[],
        founder_name="Sam",
        tone="curious",
    )
    assert "SIGNATURE LINKS" not in result


def test_user_prompt_tone_changes_voice():
    base = dict(
        student_bio="Student",
        repo_summaries=[],
        student_interests=[],
        signature_links={},
        company_name="TestCo",
        company_summary="Test",
        specific_projects=[],
        founder_name="Sam",
        founder_bio=None,
    )
    curious = build_user_prompt(**base, tone="curious")
    scrappy = build_user_prompt(**base, tone="scrappy")
    assert "curious" in curious.lower() or "nerdy" in curious.lower()
    assert "Resourceful" in scrappy


def test_user_prompt_handles_all_none_optionals():
    result = build_user_prompt(
        student_bio="Student",
        repo_summaries=[],
        student_interests=[],
        signature_links={},
        company_name="TestCo",
        company_summary="Building things",
        specific_projects=[],
        founder_name="Sam",
        founder_bio=None,
        tone="curious",
    )
    assert "TestCo" in result
    assert "Sam" in result
