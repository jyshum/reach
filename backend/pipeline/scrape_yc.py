"""Scrape YC company directory via Algolia API."""

ALGOLIA_APP_ID = "45BWZJ1SGC"
ALGOLIA_API_KEY = "be7591b7e2cc2a51d92e5ec0a1498399"
ALGOLIA_INDEX = "YCCompany_production"
TARGET_BATCHES = ["W23", "S23", "W24", "S24"]


def extract_company(hit: dict) -> dict:
    """Extract relevant fields from a single Algolia hit."""
    return {
        "name": hit.get("name", ""),
        "description": hit.get("one_liner", ""),
        "batch": hit.get("batch", ""),
        "tags": hit.get("tags", []),
        "website": hit.get("website", ""),
    }


def dedup_companies(companies: list[dict]) -> list[dict]:
    """Remove duplicate companies by name, keeping first occurrence."""
    seen = set()
    result = []
    for company in companies:
        name = company["name"]
        if name not in seen:
            seen.add(name)
            result.append(company)
    return result
