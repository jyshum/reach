"""Tests for GitHub repo fetcher — no real network calls."""

import base64
import pytest
from unittest.mock import patch, MagicMock

from backend.github_fetcher import fetch_repo_metadata, validate_repo_url


def test_validate_repo_url_valid():
    owner, repo = validate_repo_url("https://github.com/jshum/trading-bot")
    assert owner == "jshum"
    assert repo == "trading-bot"


def test_validate_repo_url_with_trailing_slash():
    owner, repo = validate_repo_url("https://github.com/jshum/trading-bot/")
    assert owner == "jshum"
    assert repo == "trading-bot"


def test_validate_repo_url_invalid():
    with pytest.raises(ValueError, match="Invalid GitHub repo URL"):
        validate_repo_url("https://gitlab.com/jshum/project")


def test_validate_repo_url_missing_repo():
    with pytest.raises(ValueError, match="Invalid GitHub repo URL"):
        validate_repo_url("https://github.com/jshum")


@patch("backend.github_fetcher._github_get")
def test_fetch_repo_metadata_success(mock_get):
    readme_content = base64.b64encode(b"# Trading Bot\nA Python bot that tracks crypto prices and executes trades.").decode()
    mock_get.side_effect = [
        {
            "name": "trading-bot",
            "description": "Crypto trading bot",
            "language": "Python",
            "stargazers_count": 12,
            "fork": False,
        },
        {
            "content": readme_content,
            "encoding": "base64",
        },
    ]

    result = fetch_repo_metadata("jshum", "trading-bot")
    assert result["repo_name"] == "trading-bot"
    assert result["language"] == "Python"
    assert result["stars"] == 12
    assert "Trading Bot" in result["readme"]
    assert result["warning"] is None


@patch("backend.github_fetcher._github_get")
def test_fetch_repo_metadata_no_readme(mock_get):
    mock_get.side_effect = [
        {"name": "my-project", "description": None, "language": "Go", "stargazers_count": 0, "fork": False},
        None,
    ]

    with pytest.raises(ValueError, match="doesn't have a README"):
        fetch_repo_metadata("jshum", "my-project")


@patch("backend.github_fetcher._github_get")
def test_fetch_repo_metadata_short_readme(mock_get):
    readme_content = base64.b64encode(b"# Hi").decode()
    mock_get.side_effect = [
        {"name": "tiny", "description": None, "language": "JS", "stargazers_count": 0, "fork": False},
        {"content": readme_content, "encoding": "base64"},
    ]

    with pytest.raises(ValueError, match="doesn't have a README"):
        fetch_repo_metadata("jshum", "tiny")


@patch("backend.github_fetcher._github_get")
def test_fetch_repo_metadata_unmodified_fork(mock_get):
    readme_content = base64.b64encode(b"# Some forked project with enough content here for testing").decode()
    mock_get.side_effect = [
        {"name": "forked", "description": "Fork", "language": "Rust", "stargazers_count": 0, "fork": True},
        {"content": readme_content, "encoding": "base64"},
    ]

    with pytest.raises(ValueError, match="unmodified fork"):
        fetch_repo_metadata("jshum", "forked")


@patch("backend.github_fetcher._github_get")
def test_fetch_repo_metadata_no_description_warning(mock_get):
    readme_content = base64.b64encode(b"# Project\nThis is a project that does interesting things with data processing.").decode()
    mock_get.side_effect = [
        {"name": "no-desc", "description": None, "language": "Python", "stargazers_count": 5, "fork": False},
        {"content": readme_content, "encoding": "base64"},
    ]

    result = fetch_repo_metadata("jshum", "no-desc")
    assert result["warning"] is not None
    assert "description" in result["warning"].lower()
