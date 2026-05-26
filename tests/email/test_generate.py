from unittest.mock import patch, MagicMock
import pytest


def test_generate_draft_calls_claude():
    from backend.email.generate import generate_draft

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="I'm a high school senior in SF...")]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("backend.email.generate.anthropic.Anthropic", return_value=mock_client):
        draft = generate_draft(
            student_bio="HS senior, ML projects",
            student_capabilities=["deep-learning", "data-pipelines"],
            company_name="Pando Bio",
            company_summary="AI enzyme design",
            specific_projects=["Analyze screening data"],
            founder_name="Alex Chen",
            tone="curious",
        )

    assert draft == "I'm a high school senior in SF..."
    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["model"] == "claude-haiku-4-5-20251001"
    assert call_kwargs["max_tokens"] == 300


def test_generate_draft_passes_guidance_angle():
    from backend.email.generate import generate_draft

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Draft text")]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("backend.email.generate.anthropic.Anthropic", return_value=mock_client):
        generate_draft(
            student_bio="Student",
            student_capabilities=["frontend-development"],
            company_name="TestCo",
            company_summary="Test",
            specific_projects=[],
            founder_name="Jane",
            tone="friendly",
            guidance_angle="Lead with React experience",
        )

    prompt_text = mock_client.messages.create.call_args[1]["messages"][0]["content"]
    assert "Lead with React experience" in prompt_text


def test_generate_draft_uses_correct_tone():
    from backend.email.generate import generate_draft

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Draft")]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("backend.email.generate.anthropic.Anthropic", return_value=mock_client):
        generate_draft(
            student_bio="Student",
            student_capabilities=["backend-apis"],
            company_name="TestCo",
            company_summary="Test",
            specific_projects=[],
            founder_name="Sam",
            tone="friendly",
        )

    prompt_text = mock_client.messages.create.call_args[1]["messages"][0]["content"]
    assert "Warm" in prompt_text
