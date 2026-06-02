"""Tests for /me/resume endpoints."""

import io
import pytest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)
MOCK_USER_ID = "test-user-123"
AUTH_HEADERS = {"Authorization": "Bearer test.jwt.token"}


def _mock_auth(user_id=MOCK_USER_ID):
    """Patch auth to return a fixed user ID."""
    return patch("backend.auth._decode_token", return_value={"sub": user_id})


@pytest.fixture
def mock_db():
    db = MagicMock()
    with patch("backend.routers.resume.get_db", return_value=db):
        yield db


def _make_storage_mock():
    """Build a storage mock with from_() chain."""
    storage = MagicMock()
    from_chain = MagicMock()
    storage.from_.return_value = from_chain
    return storage, from_chain


def test_upload_resume_success():
    db = MagicMock()
    storage, from_chain = _make_storage_mock()
    from_chain.get_public_url.return_value = "https://storage.example.com/resumes/test-user-123/resume.pdf"
    db.storage = storage
    db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

    pdf_content = b"%PDF-1.4 fake pdf content"
    with _mock_auth(), patch("backend.routers.resume.get_db", return_value=db):
        resp = client.post(
            "/me/resume",
            files={"file": ("resume.pdf", io.BytesIO(pdf_content), "application/pdf")},
            headers=AUTH_HEADERS,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "resume_url" in data
    assert "resumes" in data["resume_url"] or "storage.example.com" in data["resume_url"]
    from_chain.upload.assert_called_once()
    from_chain.get_public_url.assert_called_once()
    db.table.return_value.update.assert_called_once_with({"resume_url": data["resume_url"]})


def test_upload_resume_not_pdf():
    pdf_content = b"plain text content"
    with _mock_auth():
        resp = client.post(
            "/me/resume",
            files={"file": ("notes.txt", io.BytesIO(pdf_content), "text/plain")},
            headers=AUTH_HEADERS,
        )

    assert resp.status_code == 400
    assert "PDF" in resp.json()["detail"]


def test_upload_resume_too_large():
    # Create content slightly over 2MB
    big_content = b"x" * (2 * 1024 * 1024 + 1)
    db = MagicMock()
    storage, from_chain = _make_storage_mock()
    db.storage = storage

    with _mock_auth(), patch("backend.routers.resume.get_db", return_value=db):
        resp = client.post(
            "/me/resume",
            files={"file": ("resume.pdf", io.BytesIO(big_content), "application/pdf")},
            headers=AUTH_HEADERS,
        )

    assert resp.status_code == 400
    assert "2MB" in resp.json()["detail"] or "large" in resp.json()["detail"].lower()


def test_delete_resume():
    db = MagicMock()
    storage, from_chain = _make_storage_mock()
    db.storage = storage
    db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

    with _mock_auth(), patch("backend.routers.resume.get_db", return_value=db):
        resp = client.delete("/me/resume", headers=AUTH_HEADERS)

    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    from_chain.remove.assert_called_once_with([f"{MOCK_USER_ID}/resume.pdf"])
    db.table.return_value.update.assert_called_once_with({"resume_url": None})
