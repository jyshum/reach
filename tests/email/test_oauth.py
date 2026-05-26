import os
import pytest
from unittest.mock import patch, MagicMock
from cryptography.fernet import Fernet

TEST_KEY = Fernet.generate_key().decode()


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", TEST_KEY)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost:3000/gmail/callback")


def test_encrypt_decrypt_roundtrip():
    from backend.email.oauth import encrypt_token, decrypt_token
    original = "ya29.a0AfH6SMBx..."
    encrypted = encrypt_token(original)
    assert encrypted != original
    assert decrypt_token(encrypted) == original


def test_encrypt_produces_different_ciphertext():
    from backend.email.oauth import encrypt_token
    token = "my-refresh-token"
    a = encrypt_token(token)
    b = encrypt_token(token)
    assert a != b


def test_build_auth_url_contains_scopes():
    from backend.email.oauth import build_auth_url
    url = build_auth_url()
    assert "gmail.send" in url
    assert "gmail.readonly" in url
    assert "test-client-id" in url


def test_exchange_code_calls_google(monkeypatch):
    from backend.email.oauth import exchange_code

    mock_flow = MagicMock()
    mock_flow.credentials.refresh_token = "refresh-123"
    mock_flow.credentials.token = "access-456"

    with patch("backend.email.oauth.Flow.from_client_config", return_value=mock_flow):
        mock_flow.fetch_token = MagicMock()
        refresh, access = exchange_code("auth-code-xyz")

    assert refresh == "refresh-123"
    assert access == "access-456"
    mock_flow.fetch_token.assert_called_once_with(code="auth-code-xyz")


def test_refresh_access_token(monkeypatch):
    from backend.email.oauth import refresh_access_token

    mock_creds = MagicMock()
    mock_creds.token = "new-access-token"
    mock_creds.valid = True

    with patch("backend.email.oauth.Credentials", return_value=mock_creds):
        token = refresh_access_token("old-refresh-token")

    assert token == "new-access-token"
    mock_creds.refresh.assert_called_once()
