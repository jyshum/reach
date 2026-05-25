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
    return patch("backend.auth._decode_token", return_value={"sub": user_id, "email": "test@school.edu"})


def test_get_outreach(client, auth_headers):
    mock_db = MagicMock()
    outreach_data = [
        {"id": 1, "user_id": "user-uuid-123", "company_id": 1, "status": "sent",
         "sent_at": "2026-05-20T10:00:00Z", "followup_date": "2026-05-25T10:00:00Z",
         "notes": "Sent cold email", "created_at": "2026-05-20T10:00:00Z"},
    ]
    company_data = [{"id": 1, "name": "AlphaCo"}]

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "outreach_log":
            mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = outreach_data
        elif table_name == "companies":
            mock_table.select.return_value.in_.return_value.execute.return_value.data = company_data
        return mock_table

    mock_db.table.side_effect = table_side_effect

    with _mock_auth(), patch("backend.routers.outreach.get_db", return_value=mock_db):
        response = client.get("/outreach", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "sent"
    assert data[0]["company_name"] == "AlphaCo"


def test_post_outreach(client, auth_headers):
    mock_db = MagicMock()
    mock_db.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": 1, "user_id": "user-uuid-123", "company_id": 1, "status": "sent",
         "sent_at": "2026-05-20T10:00:00Z", "followup_date": "2026-05-25T10:00:00Z",
         "notes": None, "created_at": "2026-05-20T10:00:00Z"}
    ]

    with _mock_auth(), patch("backend.routers.outreach.get_db", return_value=mock_db):
        response = client.post("/outreach", headers=auth_headers, json={
            "company_id": 1,
            "status": "sent",
            "sent_at": "2026-05-20T10:00:00Z",
        })

    assert response.status_code == 201
    assert response.json()["status"] == "sent"


def test_put_outreach(client, auth_headers):
    mock_db = MagicMock()

    # Verify ownership
    mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        {"id": 1, "user_id": "user-uuid-123"}
    ]
    # Update
    mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        {"id": 1, "user_id": "user-uuid-123", "company_id": 1, "status": "replied",
         "sent_at": "2026-05-20T10:00:00Z", "followup_date": "2026-05-25T10:00:00Z",
         "notes": "Got a reply!", "created_at": "2026-05-20T10:00:00Z"}
    ]

    with _mock_auth(), patch("backend.routers.outreach.get_db", return_value=mock_db):
        response = client.put("/outreach/1", headers=auth_headers, json={
            "status": "replied",
            "notes": "Got a reply!",
        })

    assert response.status_code == 200
    assert response.json()["status"] == "replied"


def test_outreach_requires_auth(client):
    assert client.get("/outreach").status_code == 401
    assert client.post("/outreach", json={"company_id": 1, "status": "sent"}).status_code == 401
