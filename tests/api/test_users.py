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
    """Patch auth to return a fixed user ID."""
    return patch("backend.auth.jwt.decode", return_value={"sub": user_id, "email": "test@school.edu"})


def test_get_me_creates_new_user(client, auth_headers):
    mock_db = MagicMock()
    # First query returns no existing user
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    # Insert returns the new user
    mock_db.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "user-uuid-123", "email": "test@school.edu", "tier": "free", "skills": []}
    ]

    with _mock_auth(), patch("backend.routers.users.get_db", return_value=mock_db):
        response = client.get("/me", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "user-uuid-123"
    assert data["tier"] == "free"


def test_get_me_returns_existing_user(client, auth_headers):
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "user-uuid-123", "email": "test@school.edu", "tier": "paid", "skills": ["python scripting"],
         "school": "MIT", "grad_year": 2028, "bio": None, "github_url": None, "portfolio_url": None}
    ]

    with _mock_auth(), patch("backend.routers.users.get_db", return_value=mock_db):
        response = client.get("/me", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["tier"] == "paid"


def test_get_me_requires_auth(client):
    response = client.get("/me")
    assert response.status_code == 401


def test_put_me_updates_profile(client, auth_headers):
    mock_db = MagicMock()
    mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        {"id": "user-uuid-123", "email": "test@school.edu", "tier": "free",
         "skills": ["python scripting", "react frontend"], "school": "MIT",
         "grad_year": 2028, "bio": "Hi", "github_url": None, "portfolio_url": None}
    ]

    with _mock_auth(), patch("backend.routers.users.get_db", return_value=mock_db):
        response = client.put("/me", headers=auth_headers, json={
            "skills": ["python scripting", "react frontend"],
            "school": "MIT",
            "grad_year": 2028,
            "bio": "Hi",
        })

    assert response.status_code == 200
    assert response.json()["skills"] == ["python scripting", "react frontend"]
