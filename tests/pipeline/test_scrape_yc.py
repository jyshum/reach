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
