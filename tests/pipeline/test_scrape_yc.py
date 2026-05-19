import pytest
from backend.pipeline.scrape_yc import extract_company


def test_extract_company_maps_fields():
    hit = {
        "name": "Acme Corp",
        "one_liner": "AI for supply chains.",
        "batch": "W24",
        "tags": ["B2B", "Supply Chain", "AI"],
        "website": "https://acmecorp.com",
        "objectID": "acme-corp",
        "logo": "https://example.com/logo.png",
        "extra_field": "should be ignored",
    }
    result = extract_company(hit)
    assert result == {
        "name": "Acme Corp",
        "description": "AI for supply chains.",
        "batch": "W24",
        "tags": ["B2B", "Supply Chain", "AI"],
        "website": "https://acmecorp.com",
    }


def test_extract_company_handles_missing_fields():
    hit = {
        "name": "Bare Minimum Co",
        "batch": "S23",
    }
    result = extract_company(hit)
    assert result == {
        "name": "Bare Minimum Co",
        "description": "",
        "batch": "S23",
        "tags": [],
        "website": "",
    }


from backend.pipeline.scrape_yc import dedup_companies


def test_dedup_removes_duplicate_names():
    companies = [
        {"name": "Acme", "description": "v1", "batch": "W23", "tags": [], "website": ""},
        {"name": "Acme", "description": "v2", "batch": "W24", "tags": [], "website": ""},
        {"name": "Beta", "description": "unique", "batch": "S23", "tags": [], "website": ""},
    ]
    result = dedup_companies(companies)
    assert len(result) == 2
    names = [c["name"] for c in result]
    assert "Acme" in names
    assert "Beta" in names


def test_dedup_preserves_order_keeps_first():
    companies = [
        {"name": "Acme", "description": "first", "batch": "W23", "tags": [], "website": ""},
        {"name": "Acme", "description": "second", "batch": "W24", "tags": [], "website": ""},
    ]
    result = dedup_companies(companies)
    assert len(result) == 1
    assert result[0]["description"] == "first"


def test_dedup_empty_list():
    assert dedup_companies([]) == []


import json
import os
from unittest.mock import patch, Mock
from backend.pipeline.scrape_yc import fetch_batch
from backend.pipeline.scrape_yc import scrape_yc_directory


def test_fetch_batch_parses_response():
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "hits": [
            {
                "name": "TestCo",
                "one_liner": "Testing things.",
                "batch": "W24",
                "tags": ["SaaS"],
                "website": "https://testco.com",
            }
        ],
        "nbHits": 1,
    }

    with patch("backend.pipeline.scrape_yc.requests.post", return_value=mock_response) as mock_post:
        result = fetch_batch("W24")

    assert len(result) == 1
    assert result[0]["name"] == "TestCo"
    assert result[0]["description"] == "Testing things."

    # Verify correct Algolia endpoint was called
    call_args = mock_post.call_args
    url = call_args[0][0]
    assert "45BWZJ1SGC" in url
    assert "YCCompany_production" in url


def test_fetch_batch_returns_empty_on_error():
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = Exception("Server error")

    with patch("backend.pipeline.scrape_yc.requests.post", return_value=mock_response) as mock_post:
        mock_post.return_value.raise_for_status = mock_response.raise_for_status
        result = fetch_batch("W24")

    assert result == []


def test_scrape_yc_directory_writes_json(tmp_path):
    mock_hits = {
        "hits": [
            {
                "name": "AlphaCo",
                "one_liner": "Alpha does alpha.",
                "batch": "W24",
                "tags": ["AI"],
                "website": "https://alpha.com",
            },
        ],
        "nbHits": 1,
    }
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_hits
    mock_response.raise_for_status = Mock()

    output_path = tmp_path / "raw_companies.json"

    with patch("backend.pipeline.scrape_yc.requests.post", return_value=mock_response):
        scrape_yc_directory(output_path=str(output_path))

    assert output_path.exists()
    data = json.loads(output_path.read_text())
    assert len(data) > 0
    assert data[0]["name"] == "AlphaCo"


def test_scrape_yc_directory_creates_parent_dir(tmp_path):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"hits": [], "nbHits": 0}
    mock_response.raise_for_status = Mock()

    output_path = tmp_path / "subdir" / "raw_companies.json"

    with patch("backend.pipeline.scrape_yc.requests.post", return_value=mock_response):
        scrape_yc_directory(output_path=str(output_path))

    assert output_path.exists()
    data = json.loads(output_path.read_text())
    assert data == []


@pytest.mark.integration
def test_fetch_batch_live_returns_companies():
    """Smoke test: hit real Algolia API for W24 batch."""
    result = fetch_batch("W24")
    assert len(result) > 50, f"Expected 50+ companies, got {len(result)}"
    first = result[0]
    assert "name" in first
    assert "description" in first
    assert "batch" in first
    assert first["batch"] == "W24"
