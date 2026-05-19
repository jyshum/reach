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
