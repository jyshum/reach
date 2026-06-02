import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test.jwt.token"}


def _mock_auth(user_id="user-uuid-123"):
    return patch(
        "backend.auth._decode_token",
        return_value={"sub": user_id, "email": "test@school.edu"},
    )


# --- OAuth endpoints ---


def test_get_auth_url_requires_auth(client):
    response = client.get("/email/gmail/auth-url")
    assert response.status_code == 401


def test_get_auth_url_returns_google_url(client, auth_headers):
    with _mock_auth(), \
         patch("backend.routers.email.build_auth_url", return_value="https://accounts.google.com/o/oauth2/v2/auth?client_id=test"):
        response = client.get("/email/gmail/auth-url", headers=auth_headers)

    assert response.status_code == 200
    assert "https://accounts.google.com" in response.json()["url"]


def test_gmail_callback_stores_token(client, auth_headers):
    mock_db = MagicMock()
    mock_db.table.return_value.upsert.return_value.execute.return_value.data = [{}]

    with _mock_auth(), \
         patch("backend.routers.email.exchange_code", return_value=("refresh-tok", "access-tok")), \
         patch("backend.routers.email.encrypt_token", return_value="encrypted-refresh"), \
         patch("backend.routers.email.build_gmail_service") as mock_build, \
         patch("backend.routers.email.get_db", return_value=mock_db):

        mock_service = MagicMock()
        mock_service.users().getProfile().execute.return_value = {"emailAddress": "student@gmail.com"}
        mock_build.return_value = mock_service

        response = client.post(
            "/email/gmail/callback",
            json={"code": "auth-code-xyz"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    assert response.json()["gmail_email"] == "student@gmail.com"
    mock_db.table.return_value.upsert.assert_called_once()


def test_gmail_status_not_connected(client, auth_headers):
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

    with _mock_auth(), patch("backend.routers.email.get_db", return_value=mock_db):
        response = client.get("/email/gmail/status", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["connected"] is False


def test_gmail_status_connected(client, auth_headers):
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"gmail_email": "student@gmail.com"}
    ]

    with _mock_auth(), patch("backend.routers.email.get_db", return_value=mock_db):
        response = client.get("/email/gmail/status", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["connected"] is True
    assert response.json()["gmail_email"] == "student@gmail.com"


def test_gmail_disconnect(client, auth_headers):
    mock_db = MagicMock()
    mock_db.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = [{}]

    with _mock_auth(), patch("backend.routers.email.get_db", return_value=mock_db):
        response = client.delete("/email/gmail/disconnect", headers=auth_headers)

    assert response.status_code == 200


# --- Generate endpoint ---


def _sample_company():
    return {
        "id": 1,
        "name": "AlphaCo",
        "summary": "AI tools for alpha",
        "specific_projects": ["Build dashboard"],
        "founder_name": "Alex Chen",
        "capability_tags": ["deep-learning"],
        "need_tags": [],
    }


def _sample_user():
    return {
        "id": "user-uuid-123",
        "skills": ["deep-learning", "data-pipelines"],
        "bio": "HS senior interested in ML",
        "location": "San Francisco",
    }


def test_generate_requires_auth(client):
    response = client.post("/email/generate", json={"company_id": 1})
    assert response.status_code == 401


def test_generate_returns_draft(client, auth_headers):
    mock_db = MagicMock()

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "companies":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [_sample_company()]
        elif table_name == "users":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [_sample_user()]
        return mock_table

    mock_db.table.side_effect = table_side_effect

    with _mock_auth(), \
         patch("backend.routers.email.get_db", return_value=mock_db), \
         patch("backend.routers.email.generate_draft", return_value="I'm a high school senior in SF..."):
        response = client.post(
            "/email/generate",
            json={"company_id": 1, "tone": "curious"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["draft"] == "I'm a high school senior in SF..."
    assert data["company_name"] == "AlphaCo"
    assert data["tone"] == "curious"


def test_generate_company_not_found(client, auth_headers):
    mock_db = MagicMock()

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "companies":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = []
        elif table_name == "users":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [_sample_user()]
        return mock_table

    mock_db.table.side_effect = table_side_effect

    with _mock_auth(), patch("backend.routers.email.get_db", return_value=mock_db):
        response = client.post(
            "/email/generate",
            json={"company_id": 999},
            headers=auth_headers,
        )

    assert response.status_code == 404


# --- Send endpoint ---


def test_send_requires_auth(client):
    response = client.post("/email/send", json={
        "company_id": 1, "subject_line": "Hi", "final_text": "Hello", "original_draft": "Hello",
    })
    assert response.status_code == 401


def test_send_requires_gmail_connected(client, auth_headers):
    mock_db = MagicMock()

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "gmail_tokens":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = []
        elif table_name == "companies":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [_sample_company()]
        return mock_table

    mock_db.table.side_effect = table_side_effect

    with _mock_auth(), patch("backend.routers.email.get_db", return_value=mock_db):
        response = client.post(
            "/email/send",
            json={"company_id": 1, "subject_line": "Hi", "final_text": "Hello", "original_draft": "Hello"},
            headers=auth_headers,
        )

    assert response.status_code == 400
    assert "Gmail" in response.json()["detail"]


def test_send_requires_founder_email(client, auth_headers):
    mock_db = MagicMock()
    company_no_email = _sample_company()
    company_no_email["founder_email"] = None

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "gmail_tokens":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                {"encrypted_refresh_token": "enc-tok", "gmail_email": "me@gmail.com"}
            ]
        elif table_name == "companies":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [company_no_email]
        return mock_table

    mock_db.table.side_effect = table_side_effect

    with _mock_auth(), patch("backend.routers.email.get_db", return_value=mock_db):
        response = client.post(
            "/email/send",
            json={"company_id": 1, "subject_line": "Hi", "final_text": "Hello", "original_draft": "Hello"},
            headers=auth_headers,
        )

    assert response.status_code == 400
    assert "email" in response.json()["detail"].lower()


def test_send_success(client, auth_headers):
    mock_db = MagicMock()
    company = _sample_company()
    company["founder_email"] = "founder@startup.com"

    insert_result = {"id": 1, "status": "sent"}

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "gmail_tokens":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                {"encrypted_refresh_token": "enc-tok", "gmail_email": "me@gmail.com"}
            ]
        elif table_name == "companies":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [company]
        elif table_name == "email_log":
            mock_table.insert.return_value.execute.return_value.data = [insert_result]
        elif table_name == "outreach_log":
            mock_table.insert.return_value.execute.return_value.data = [{}]
        return mock_table

    mock_db.table.side_effect = table_side_effect

    with _mock_auth(), \
         patch("backend.routers.email.get_db", return_value=mock_db), \
         patch("backend.routers.email.decrypt_token", return_value="refresh-tok"), \
         patch("backend.routers.email.refresh_access_token", return_value="access-tok"), \
         patch("backend.routers.email.build_gmail_service", return_value=MagicMock()), \
         patch("backend.routers.email.send_email", return_value={"message_id": "msg-123", "thread_id": "thread-456"}):
        response = client.post(
            "/email/send",
            json={
                "company_id": 1,
                "subject_line": "Quick question about AlphaCo",
                "final_text": "Hi, I'm a high school senior...",
                "original_draft": "Draft text here",
                "tone": "curious",
            },
            headers=auth_headers,
        )

    assert response.status_code == 200
    assert response.json()["status"] == "sent"


# --- Reply checking ---


def test_check_replies_requires_auth(client):
    response = client.post("/email/check-replies")
    assert response.status_code == 401


def test_check_replies_detects_reply(client, auth_headers):
    mock_db = MagicMock()

    sent_emails = [
        {"id": 1, "gmail_thread_id": "thread-1", "status": "sent", "company_id": 1},
    ]

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "gmail_tokens":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                {"encrypted_refresh_token": "enc-tok", "gmail_email": "me@gmail.com"}
            ]
        elif table_name == "email_log":
            mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = sent_emails
            mock_table.update.return_value.eq.return_value.execute.return_value.data = [{}]
        elif table_name == "outreach_log":
            mock_table.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{}]
        return mock_table

    mock_db.table.side_effect = table_side_effect

    with _mock_auth(), \
         patch("backend.routers.email.get_db", return_value=mock_db), \
         patch("backend.routers.email.decrypt_token", return_value="refresh-tok"), \
         patch("backend.routers.email.refresh_access_token", return_value="access-tok"), \
         patch("backend.routers.email.build_gmail_service"), \
         patch("backend.routers.email.check_thread_for_reply", return_value=True):
        response = client.post("/email/check-replies", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["replies_found"] == 1


def test_check_replies_no_sent_emails(client, auth_headers):
    mock_db = MagicMock()

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "gmail_tokens":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                {"encrypted_refresh_token": "enc-tok", "gmail_email": "me@gmail.com"}
            ]
        elif table_name == "email_log":
            mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        return mock_table

    mock_db.table.side_effect = table_side_effect

    with _mock_auth(), \
         patch("backend.routers.email.get_db", return_value=mock_db), \
         patch("backend.routers.email.decrypt_token", return_value="refresh-tok"), \
         patch("backend.routers.email.refresh_access_token", return_value="access-tok"), \
         patch("backend.routers.email.build_gmail_service"):
        response = client.post("/email/check-replies", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["replies_found"] == 0


def test_check_replies_detects_bounce(client, auth_headers):
    mock_db = MagicMock()

    sent_emails = [
        {"id": 1, "gmail_thread_id": "thread-1", "status": "sent", "company_id": 1},
    ]

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "gmail_tokens":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                {"encrypted_refresh_token": "enc-tok", "gmail_email": "me@gmail.com"}
            ]
        elif table_name == "email_log":
            mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = sent_emails
            mock_table.update.return_value.eq.return_value.execute.return_value.data = [{}]
        elif table_name == "outreach_log":
            mock_table.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{}]
        elif table_name == "companies":
            mock_table.update.return_value.eq.return_value.execute.return_value.data = [{}]
        return mock_table

    mock_db.table.side_effect = table_side_effect

    with _mock_auth(), \
         patch("backend.routers.email.get_db", return_value=mock_db), \
         patch("backend.routers.email.decrypt_token", return_value="refresh-tok"), \
         patch("backend.routers.email.refresh_access_token", return_value="access-tok"), \
         patch("backend.routers.email.build_gmail_service"), \
         patch("backend.routers.email.check_thread_for_bounce", return_value=True):
        response = client.post("/email/check-replies", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["bounces_found"] == 1
    assert response.json()["replies_found"] == 0
