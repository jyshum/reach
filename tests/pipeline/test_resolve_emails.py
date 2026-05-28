"""Tests for email resolution — parsing logic only (no network)."""

import pytest
from backend.pipeline.resolve_emails import (
    extract_domain,
    extract_emails_from_html,
    filter_generic_emails,
    guess_email_patterns,
    match_founder_email,
)


def test_extract_domain_simple():
    assert extract_domain("https://www.pando.bio/") == "pando.bio"
    assert extract_domain("https://yuma.ai") == "yuma.ai"
    assert extract_domain("http://metal.so") == "metal.so"


def test_extract_domain_with_subdomain():
    assert extract_domain("https://app.example.com") == "example.com"


def test_extract_domain_none():
    assert extract_domain(None) is None
    assert extract_domain("") is None


def test_extract_emails_from_html_finds_mailto():
    html = '<a href="mailto:alice@example.com">Contact</a>'
    emails = extract_emails_from_html(html, "example.com")
    assert "alice@example.com" in emails


def test_extract_emails_from_html_finds_plain_text():
    html = "<p>Reach us at bob@startup.io for inquiries</p>"
    emails = extract_emails_from_html(html, "startup.io")
    assert "bob@startup.io" in emails


def test_extract_emails_filters_wrong_domain():
    html = '<a href="mailto:user@gmail.com">Email</a> and alice@example.com'
    emails = extract_emails_from_html(html, "example.com")
    assert "alice@example.com" in emails
    assert "user@gmail.com" not in emails


def test_filter_generic_emails():
    emails = ["info@co.com", "hello@co.com", "alice@co.com", "support@co.com", "sales@co.com"]
    filtered = filter_generic_emails(emails)
    assert filtered == ["alice@co.com"]


def test_guess_email_patterns():
    patterns = guess_email_patterns("Alice", "Smith", "example.com")
    assert "alice@example.com" in patterns
    assert "alice.smith@example.com" in patterns
    assert "alicesmith@example.com" in patterns
    assert "a.smith@example.com" in patterns


def test_match_founder_email_picks_best():
    emails = ["alice@example.com", "bob@example.com"]
    result = match_founder_email(emails, "Alice", "Smith")
    assert result == "alice@example.com"


def test_match_founder_email_no_match():
    emails = ["jobs@example.com"]
    result = match_founder_email(emails, "Alice", "Smith")
    # Returns first non-generic email even if name doesn't match
    assert result == "jobs@example.com"


def test_match_founder_email_empty():
    result = match_founder_email([], "Alice", "Smith")
    assert result is None
