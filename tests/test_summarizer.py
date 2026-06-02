"""Tests for repo summarizer — mocks the Anthropic API."""

from unittest.mock import patch, MagicMock
from backend.summarizer import summarize_repo


@patch("backend.summarizer.anthropic")
def test_summarize_repo_returns_text(mock_anthropic):
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="A Python trading bot that executes crypto trades using Binance API. Uses websockets for real-time data. Impressive for a solo dev project.")]
    )

    result = summarize_repo(
        repo_name="trading-bot",
        readme="# Trading Bot\nA Python bot for crypto trading...",
        language="Python",
        description="Crypto trading bot",
        stars=12,
    )

    assert "trading bot" in result.lower()
    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["model"] == "claude-haiku-4-5-20251001"
    assert call_kwargs["max_tokens"] == 200


@patch("backend.summarizer.anthropic")
def test_summarize_repo_passes_context(mock_anthropic):
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="A React dashboard for visualizing sensor data.")]
    )

    summarize_repo(
        repo_name="sensor-dash",
        readme="# Sensor Dashboard\nReal-time IoT sensor visualization...",
        language="TypeScript",
        description="IoT dashboard",
        stars=3,
    )

    call_kwargs = mock_client.messages.create.call_args[1]
    user_message = call_kwargs["messages"][0]["content"]
    assert "sensor-dash" in user_message.lower() or "Sensor Dashboard" in user_message
    assert "TypeScript" in user_message
