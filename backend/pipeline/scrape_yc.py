"""Scrape YC company directory via Algolia API."""

import json
import os
from urllib.parse import quote

import requests

ALGOLIA_APP_ID = "45BWZJ1SGC"
ALGOLIA_API_KEY = "NzllNTY5MzJiZGM2OTY2ZTQwMDEzOTNhYWZiZGRjODlhYzVkNjBmOGRjNzJiMWM4ZTU0ZDlhYTZjOTJiMjlhMWFuYWx5dGljc1RhZ3M9eWNkYyZyZXN0cmljdEluZGljZXM9WUNDb21wYW55X3Byb2R1Y3Rpb24lMkNZQ0NvbXBhbnlfQnlfTGF1bmNoX0RhdGVfcHJvZHVjdGlvbiZ0YWdGaWx0ZXJzPSU1QiUyMnljZGNfcHVibGljJTIyJTVE"
ALGOLIA_INDEX = "YCCompany_production"
TARGET_BATCHES = ["Winter 2023", "Summer 2023", "Winter 2024", "Summer 2024"]


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
    batch_filter = quote(f'["batch:{batch}"]')
    payload = {
        "params": f"facetFilters={batch_filter}&hitsPerPage=1000"
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


DEFAULT_OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw_companies.json")


def scrape_yc_directory(output_path: str = DEFAULT_OUTPUT_PATH) -> list[dict]:
    """Scrape all target batches, dedup, and write to JSON file."""
    all_companies = []
    for batch in TARGET_BATCHES:
        companies = fetch_batch(batch)
        all_companies.extend(companies)

    deduped = dedup_companies(all_companies)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(deduped, f, indent=2)

    print(f"[DONE] Wrote {len(deduped)} companies to {output_path}")
    return deduped


if __name__ == "__main__":
    scrape_yc_directory()
