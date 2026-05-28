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


def _sample_companies():
    return [
        {"id": 1, "name": "AlphaCo", "yc_batch": "Winter 2024", "one_liner": "AI for alpha",
         "industry": "ai-ml", "stage_detail": "growing", "technical_level": "technical",
         "team_size": 5, "reachability_score": "high", "reachability_probability": 0.98,
         "need_tags": ["python scripting", "data analysis"], "yc_tags": ["Machine Learning"], "status": "Active",
         "description": "Alpha does alpha.", "summary": "Alpha builds AI tools.",
         "website": "https://alpha.com", "stage": "Early", "specific_projects": ["Build dashboard", "Write docs"],
         "is_hiring": False, "founder_name": None, "founder_title": None,
         "founder_linkedin": None, "founder_twitter": None, "all_locations": "SF",
         "tags": ["AI"], "industries": ["AI"], "long_description": "Full description."},
        {"id": 2, "name": "BetaCo", "yc_batch": "Summer 2024", "one_liner": "Design for beta",
         "industry": "consumer", "stage_detail": "building-mvp", "technical_level": "mixed",
         "team_size": 3, "reachability_score": "medium", "reachability_probability": 0.75,
         "need_tags": ["graphic design", "content writing"], "yc_tags": ["Consumer"], "status": "Active",
         "description": "Beta does beta.", "summary": "Beta builds consumer tools.",
         "website": "https://beta.com", "stage": "Early", "specific_projects": ["Design logo", "Write blog"],
         "is_hiring": True, "founder_name": None, "founder_title": None,
         "founder_linkedin": None, "founder_twitter": None, "all_locations": "NYC",
         "tags": ["Consumer"], "industries": ["Consumer"], "long_description": "Full description."},
    ]


def test_get_companies_anonymous(client):
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = _sample_companies()

    with patch("backend.routers.companies.get_db", return_value=mock_db):
        response = client.get("/companies")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Sorted by reachability when no auth — BetaCo scores higher (building-mvp + hiring)
    assert data[0]["name"] == "BetaCo"


def test_get_companies_with_auth_ranked(client, auth_headers):
    mock_db = MagicMock()
    # Companies query
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = _sample_companies()

    # User query (has Consumer interest — should boost BetaCo)
    user_data = [{"id": "user-uuid-123", "interests": ["Consumer"]}]

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "companies":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = _sample_companies()
        elif table_name == "users":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = user_data
        return mock_table

    mock_db.table.side_effect = table_side_effect

    with _mock_auth(), patch("backend.routers.companies.get_db", return_value=mock_db):
        response = client.get("/companies", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # BetaCo should rank higher due to interest match
    assert data[0]["name"] == "BetaCo"


def test_get_companies_filter_by_industry(client):
    mock_db = MagicMock()
    # Only return ai-ml companies when filtered
    filtered = [c for c in _sample_companies() if c["industry"] == "ai-ml"]
    mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = filtered
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = filtered

    with patch("backend.routers.companies.get_db", return_value=mock_db):
        response = client.get("/companies?industry=ai-ml")

    assert response.status_code == 200


def test_get_company_brief_requires_auth(client):
    response = client.get("/companies/1")
    assert response.status_code == 401


def test_get_company_brief_success(client, auth_headers):
    mock_db = MagicMock()

    company = _sample_companies()[0]
    user_data = [{"id": "user-uuid-123", "interests": ["Machine Learning"], "tier": "paid"}]
    brief_views = []

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "companies":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [company]
        elif table_name == "users":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = user_data
        elif table_name == "brief_views":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = brief_views
            mock_table.insert.return_value.execute.return_value.data = [{}]
        return mock_table

    mock_db.table.side_effect = table_side_effect

    with _mock_auth(), patch("backend.routers.companies.get_db", return_value=mock_db):
        response = client.get("/companies/1", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["name"] == "AlphaCo"


def test_get_company_brief_includes_guidance(client, auth_headers):
    mock_db = MagicMock()

    company = _sample_companies()[0]  # AlphaCo: ai-ml, growing, Machine Learning tag
    user_data = [{"id": "user-uuid-123", "interests": ["Machine Learning"], "tier": "paid"}]
    brief_views = []

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "companies":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [company]
        elif table_name == "users":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = user_data
        elif table_name == "brief_views":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = brief_views
            mock_table.insert.return_value.execute.return_value.data = [{}]
        return mock_table

    mock_db.table.side_effect = table_side_effect

    with _mock_auth(), patch("backend.routers.companies.get_db", return_value=mock_db):
        response = client.get("/companies/1", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["guidance"] is not None
    assert "your_angle" in data["guidance"]
    assert "reference_this" in data["guidance"]
    assert "dont_say" in data["guidance"]
    assert "your_ask" in data["guidance"]
    # No unfilled placeholders
    for field in data["guidance"].values():
        assert "{" not in field


def test_get_company_brief_no_skills_no_guidance(client, auth_headers):
    mock_db = MagicMock()

    company = _sample_companies()[0]
    user_data = [{"id": "user-uuid-123", "interests": [], "tier": "paid"}]
    brief_views = []

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "companies":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [company]
        elif table_name == "users":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = user_data
        elif table_name == "brief_views":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = brief_views
            mock_table.insert.return_value.execute.return_value.data = [{}]
        return mock_table

    mock_db.table.side_effect = table_side_effect

    with _mock_auth(), patch("backend.routers.companies.get_db", return_value=mock_db):
        response = client.get("/companies/1", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["guidance"] is None
