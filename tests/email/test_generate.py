"""Tests for email draft generation."""

from unittest.mock import patch, MagicMock


def test_generate_draft_calls_claude_with_system_prompt():
    from backend.email.generate import generate_draft

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="SUBJECT: Quick chat about enzymes\n\nI'm a high school senior in SF...")]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("backend.email.generate.anthropic.Anthropic", return_value=mock_client):
        subject, draft = generate_draft(
            student_bio="HS senior, ML projects",
            repo_summaries=[{"repo_name": "bot", "summary": "A bot.", "language": "Python", "stars": 5}],
            student_interests=["Generative AI"],
            signature_links={"github_url": "https://github.com/alice"},
            company_name="Pando Bio",
            company_summary="AI enzyme design",
            specific_projects=["Analyze screening data"],
            founder_name="Alex Chen",
            tone="curious",
        )

    assert subject == "Quick chat about enzymes"
    assert "high school senior" in draft
    assert "SUBJECT:" not in draft

    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["model"] == "claude-haiku-4-5-20251001"
    assert call_kwargs["max_tokens"] == 300
    assert "system" in call_kwargs
    assert "high school" in call_kwargs["system"].lower()


def test_generate_draft_fallback_subject():
    from backend.email.generate import generate_draft

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="I'm a high school student interested in your work...")]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("backend.email.generate.anthropic.Anthropic", return_value=mock_client):
        subject, draft = generate_draft(
            student_bio="Student",
            repo_summaries=[],
            student_interests=[],
            signature_links={},
            company_name="TestCo",
            company_summary="Test",
            specific_projects=[],
            founder_name="Sam",
            tone="friendly",
        )

    assert subject == "Quick question - TestCo"
    assert "high school student" in draft


def test_generate_draft_includes_founder_bio():
    from backend.email.generate import generate_draft

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="SUBJECT: Test\n\nDraft text")]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("backend.email.generate.anthropic.Anthropic", return_value=mock_client):
        generate_draft(
            student_bio="Student",
            repo_summaries=[],
            student_interests=["Developer Tools"],
            signature_links={},
            company_name="TestCo",
            company_summary="Test",
            specific_projects=[],
            founder_name="Jane",
            founder_bio="Jane built infra tools at Google for 10 years",
            tone="friendly",
        )

    call_kwargs = mock_client.messages.create.call_args[1]
    user_message = call_kwargs["messages"][0]["content"]
    assert "10 years" in user_message


def test_generate_draft_uses_correct_tone():
    from backend.email.generate import generate_draft

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="SUBJECT: Test\n\nDraft")]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("backend.email.generate.anthropic.Anthropic", return_value=mock_client):
        generate_draft(
            student_bio="Student",
            repo_summaries=[],
            student_interests=[],
            signature_links={},
            company_name="TestCo",
            company_summary="Test",
            specific_projects=[],
            founder_name="Sam",
            tone="friendly",
        )

    call_kwargs = mock_client.messages.create.call_args[1]
    user_message = call_kwargs["messages"][0]["content"]
    assert "Warm" in user_message
