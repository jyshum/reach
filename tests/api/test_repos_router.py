"""Tests for /me/repos endpoints."""

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
    with patch("backend.routers.repos.get_db", return_value=db):
        yield db


def test_create_repo_success(mock_db):
    user_table = MagicMock()
    repos_table = MagicMock()

    def table_router(name):
        if name == "users":
            return user_table
        return repos_table

    mock_db.table.side_effect = table_router

    user_select = user_table.select.return_value.eq.return_value
    user_select.execute.return_value = MagicMock(data=[{"summarization_count": 0}])

    repos_select = repos_table.select.return_value.eq.return_value
    repos_select.execute.return_value = MagicMock(data=[])

    repos_table.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": 1, "repo_url": "https://github.com/jshum/bot", "repo_name": "bot", "summary": "A bot.", "language": "Python", "stars": 5}]
    )

    user_table.update.return_value.eq.return_value.execute.return_value = MagicMock()

    with _mock_auth(), \
         patch("backend.routers.repos.fetch_repo_metadata") as mock_fetch, \
         patch("backend.routers.repos.summarize_repo") as mock_summarize:
        mock_fetch.return_value = {
            "repo_name": "bot",
            "description": "A bot",
            "language": "Python",
            "stars": 5,
            "readme": "# Bot\nDoes things...",
            "warning": None,
        }
        mock_summarize.return_value = "A bot."

        resp = client.post("/me/repos", json={"repo_url": "https://github.com/jshum/bot"}, headers=AUTH_HEADERS)

    assert resp.status_code == 200
    data = resp.json()
    assert data["repo_name"] == "bot"
    assert data["summary"] == "A bot."


def test_create_repo_invalid_url(mock_db):
    with _mock_auth():
        resp = client.post("/me/repos", json={"repo_url": "https://gitlab.com/x/y"}, headers=AUTH_HEADERS)
    assert resp.status_code == 400
    assert "Invalid" in resp.json()["detail"]


def test_create_repo_exceeds_3_limit(mock_db):
    user_table = MagicMock()
    repos_table = MagicMock()

    def table_router(name):
        if name == "users":
            return user_table
        return repos_table

    mock_db.table.side_effect = table_router

    user_select = user_table.select.return_value.eq.return_value
    user_select.execute.return_value = MagicMock(data=[{"summarization_count": 2}])

    repos_select = repos_table.select.return_value.eq.return_value
    repos_select.execute.return_value = MagicMock(data=[{}, {}, {}])

    with _mock_auth():
        resp = client.post("/me/repos", json={"repo_url": "https://github.com/jshum/bot"}, headers=AUTH_HEADERS)
    assert resp.status_code == 400
    assert "3" in resp.json()["detail"]


def test_create_repo_exceeds_summarization_limit(mock_db):
    user_table = MagicMock()
    repos_table = MagicMock()

    def table_router(name):
        if name == "users":
            return user_table
        return repos_table

    mock_db.table.side_effect = table_router

    user_select = user_table.select.return_value.eq.return_value
    user_select.execute.return_value = MagicMock(data=[{"summarization_count": 10}])

    repos_select = repos_table.select.return_value.eq.return_value
    repos_select.execute.return_value = MagicMock(data=[])

    with _mock_auth():
        resp = client.post("/me/repos", json={"repo_url": "https://github.com/jshum/bot"}, headers=AUTH_HEADERS)
    assert resp.status_code == 400
    assert "10" in resp.json()["detail"]


def test_list_repos(mock_db):
    table = mock_db.table.return_value
    select = table.select.return_value
    eq = select.eq.return_value
    eq.execute.return_value = MagicMock(data=[
        {"id": 1, "repo_url": "https://github.com/jshum/bot", "repo_name": "bot", "summary": "A bot.", "language": "Python", "stars": 5},
    ])

    with _mock_auth():
        resp = client.get("/me/repos", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["repo_name"] == "bot"


def test_delete_repo(mock_db):
    table = mock_db.table.return_value
    delete_chain = table.delete.return_value.eq.return_value.eq.return_value
    delete_chain.execute.return_value = MagicMock(data=[{"id": 1}])

    with _mock_auth():
        resp = client.delete("/me/repos/1", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
