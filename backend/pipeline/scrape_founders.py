"""Scrape YC company pages for founder data."""

import html
import json
import os
import re
import time

import requests

_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
RAW_DATA_PATH = os.path.join(_ROOT, "data", "raw_companies.json")
FOUNDERS_OUTPUT_PATH = os.path.join(_ROOT, "data", "founders.json")

REQUEST_DELAY = 1.0  # seconds between requests
REQUEST_TIMEOUT = 15  # seconds per request
LOG_EVERY = 50


def strip_s3_signature(url: str | None) -> str | None:
    """Remove AWS query-string signature from an S3 URL."""
    if not url:
        return url
    return url.split("?")[0]


def parse_founders_from_html(page_html: str) -> dict | None:
    """Extract founder data from a YC company page's HTML.

    The page embeds company data as HTML-entity-encoded JSON.
    We find the founders array and return the first active founder.
    """
    # Decode HTML entities first, then find the founders JSON array
    decoded = html.unescape(page_html)
    match = re.search(r'"founders":\[', decoded)
    if not match:
        return None

    # Bracket-match to find the full array (regex is unreliable with nested JSON)
    start = match.start() + len('"founders":')
    depth = 0
    end = start
    for i, c in enumerate(decoded[start:], start):
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if depth != 0:
        return None

    try:
        founders = json.loads(decoded[start:end])
    except json.JSONDecodeError:
        return None

    if not founders:
        return None

    # Find first active founder
    founder = None
    for f in founders:
        if f.get("is_active", True):
            founder = f
            break

    if not founder:
        # Fallback: use first founder regardless
        founder = founders[0]

    return {
        "founder_name": founder.get("full_name") or None,
        "founder_title": founder.get("title") or None,
        "founder_avatar_url": strip_s3_signature(founder.get("avatar_thumb_url")),
        "founder_linkedin": founder.get("linkedin_url") or None,
        "founder_twitter": founder.get("twitter_url") or None,
    }


def scrape_founder(slug: str) -> dict | None:
    """Fetch a single YC company page and extract founder data."""
    url = f"https://www.ycombinator.com/companies/{slug}"
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return None
        return parse_founders_from_html(resp.text)
    except Exception:
        return None


def scrape_all_founders(
    raw_path: str = RAW_DATA_PATH,
    output_path: str = FOUNDERS_OUTPUT_PATH,
):
    """Scrape founder data for all companies. Supports resume on interruption."""
    with open(raw_path) as f:
        companies = json.load(f)

    # Load existing results for resume support
    existing = {}
    if os.path.exists(output_path):
        with open(output_path) as f:
            for entry in json.load(f):
                existing[entry["company_name"]] = entry
        print(f"[INFO] Resuming — {len(existing)} companies already scraped")

    results = list(existing.values())
    scraped_names = set(existing.keys())
    total = len(companies)
    skipped = 0
    errors = 0

    for i, company in enumerate(companies):
        name = company["name"]
        slug = company.get("slug", "")

        if name in scraped_names:
            continue

        if not slug:
            skipped += 1
            results.append({
                "company_name": name,
                "founder_name": None,
                "founder_title": None,
                "founder_avatar_url": None,
                "founder_linkedin": None,
                "founder_twitter": None,
            })
            continue

        founder_data = scrape_founder(slug)

        if founder_data:
            founder_data["company_name"] = name
            results.append(founder_data)
        else:
            errors += 1
            results.append({
                "company_name": name,
                "founder_name": None,
                "founder_title": None,
                "founder_avatar_url": None,
                "founder_linkedin": None,
                "founder_twitter": None,
            })

        # Progress logging
        done = i + 1
        if done % LOG_EVERY == 0 or done == total:
            print(f"[INFO] {done}/{total} companies processed ({errors} errors, {skipped} skipped)")

        # Save periodically
        if done % LOG_EVERY == 0:
            with open(output_path, "w") as f:
                json.dump(results, f, indent=2)

        time.sleep(REQUEST_DELAY)

    # Final save
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    found = sum(1 for r in results if r.get("founder_name"))
    print(f"[DONE] {len(results)} companies, {found} founders found, {errors} errors, {skipped} no slug")
    return results


if __name__ == "__main__":
    scrape_all_founders()
