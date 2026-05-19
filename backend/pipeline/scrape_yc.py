"""Scrape YC company directory via Algolia API."""

import requests

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


def fetch_batch(batch: str) -> list[dict]:
    """Fetch all companies for a single YC batch from Algolia."""
    url = f"https://{ALGOLIA_APP_ID}-dsn.algolia.net/1/indexes/{ALGOLIA_INDEX}/query"
    headers = {
        "X-Algolia-API-Key": ALGOLIA_API_KEY,
        "X-Algolia-Application-Id": ALGOLIA_APP_ID,
        "Content-Type": "application/json",
    }
    payload = {
        "params": f'facetFilters=["batch:{batch}"]&hitsPerPage=1000'
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"[ERROR] Failed to fetch batch {batch}: {e}")
        return []

    data = response.json()
    hits = data.get("hits", [])
    print(f"[INFO] Batch {batch}: {len(hits)} companies fetched")
    return [extract_company(hit) for hit in hits]
