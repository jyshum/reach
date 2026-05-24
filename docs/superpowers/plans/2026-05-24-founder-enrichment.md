# Founder Enrichment Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scrape founder data (name, title, headshot, LinkedIn) and company logos from YC, store in Supabase alongside existing company data.

**Architecture:** Two pipeline changes — update the Algolia scraper to extract slug + logo URL, and a new founder scraper that fetches each company's YC page and parses the embedded JSON for founder details. Then update supabase_write to include the new fields. Schema migration adds 4 new columns.

**Tech Stack:** Python 3.12, requests, Supabase Python SDK, pytest

**Spec:** `docs/superpowers/specs/2026-05-24-founder-enrichment-design.md`

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Modify | `backend/pipeline/scrape_yc.py` | Add `slug` and `small_logo_thumb_url` to extracted fields |
| Create | `backend/pipeline/scrape_founders.py` | Scrape YC company pages for founder data |
| Modify | `backend/pipeline/supabase_write.py` | Include founder + logo fields in upsert |
| Modify | `backend/db/schema.sql` | Add new columns (reference doc) |
| Modify | `backend/schemas.py` | Add new fields to CompanyCard and CompanyBrief |
| Create | `tests/pipeline/test_scrape_founders.py` | Tests for founder scraping logic |

---

### Task 1: Update scrape_yc.py — Extract slug + logo

**Files:**
- Modify: `backend/pipeline/scrape_yc.py:20-39`

- [ ] **Step 1: Add slug and logo to extract_company()**

In `backend/pipeline/scrape_yc.py`, add two lines to the `extract_company()` function's return dict, after the `"all_locations"` line:

```python
def extract_company(hit: dict) -> dict:
    """Extract relevant fields from a single Algolia hit."""
    return {
        "name": hit.get("name", ""),
        "description": hit.get("one_liner", ""),
        "batch": hit.get("batch", ""),
        "tags": hit.get("tags", []),
        "website": hit.get("website", ""),
        "team_size": hit.get("team_size", None),
        "stage": hit.get("stage", ""),
        "status": hit.get("status", ""),
        "is_hiring": hit.get("isHiring", False),
        "top_company": hit.get("top_company", False),
        "launched_at": hit.get("launched_at", None),
        "nonprofit": hit.get("nonprofit", False),
        "industries": hit.get("industries", []),
        "subindustry": hit.get("subindustry", ""),
        "long_description": hit.get("long_description", ""),
        "all_locations": hit.get("all_locations", ""),
        "slug": hit.get("slug", ""),
        "small_logo_thumb_url": hit.get("small_logo_thumb_url", ""),
    }
```

- [ ] **Step 2: Re-run the scraper to regenerate raw_companies.json**

```bash
python3.12 -m backend.pipeline.scrape_yc
```

Expected: `[DONE] Wrote 1519 companies to data/raw_companies.json` (count may vary slightly).

- [ ] **Step 3: Verify slug and logo are present**

```bash
python3.12 -c "
import json
d = json.load(open('data/raw_companies.json'))
has_slug = sum(1 for c in d if c.get('slug'))
has_logo = sum(1 for c in d if c.get('small_logo_thumb_url'))
print(f'Companies: {len(d)}, with slug: {has_slug}, with logo: {has_logo}')
print(f'Sample: slug={d[0][\"slug\"]}, logo={d[0][\"small_logo_thumb_url\"][:60]}...')
"
```

Expected: Most companies have both slug and logo.

- [ ] **Step 4: Commit**

```bash
git add backend/pipeline/scrape_yc.py data/raw_companies.json
git commit -m "feat: extract slug and logo URL from YC Algolia data"
```

---

### Task 2: Create scrape_founders.py

**Files:**
- Create: `backend/pipeline/scrape_founders.py`
- Create: `tests/pipeline/test_scrape_founders.py`

- [ ] **Step 1: Write tests for the parsing logic**

Create `tests/pipeline/__init__.py` if it doesn't exist:

```bash
touch tests/pipeline/__init__.py
```

Create `tests/pipeline/test_scrape_founders.py`:

```python
"""Tests for founder scraping — parsing logic only (no network)."""

import pytest
from backend.pipeline.scrape_founders import parse_founders_from_html, strip_s3_signature


def test_strip_s3_signature_removes_query_params():
    url = "https://bookface-images.s3.us-west-2.amazonaws.com/avatars/abc123.jpg?X-Amz-Algorithm=AWS4&X-Amz-Credential=FAKE"
    result = strip_s3_signature(url)
    assert result == "https://bookface-images.s3.us-west-2.amazonaws.com/avatars/abc123.jpg"


def test_strip_s3_signature_preserves_clean_url():
    url = "https://bookface-images.s3.us-west-2.amazonaws.com/avatars/abc123.jpg"
    result = strip_s3_signature(url)
    assert result == url


def test_strip_s3_signature_empty_string():
    assert strip_s3_signature("") == ""


def test_strip_s3_signature_none():
    assert strip_s3_signature(None) is None


SAMPLE_HTML_WITH_FOUNDERS = '''
<html><body>
<div>&quot;company&quot;:{&quot;name&quot;:&quot;TestCo&quot;,&quot;founders&quot;:[{&quot;user_id&quot;:123,&quot;is_active&quot;:true,&quot;full_name&quot;:&quot;Alice Smith&quot;,&quot;title&quot;:&quot;CEO&quot;,&quot;avatar_thumb_url&quot;:&quot;https://bookface-images.s3.us-west-2.amazonaws.com/avatars/abc.jpg?X-Amz-Algorithm=AWS4&quot;,&quot;linkedin_url&quot;:&quot;https://linkedin.com/in/alice&quot;,&quot;twitter_url&quot;:&quot;https://twitter.com/alice&quot;,&quot;has_email&quot;:true}],&quot;editUrl&quot;:&quot;https://bookface.ycombinator.com&quot;}</div>
</body></html>
'''


def test_parse_founders_extracts_first_active():
    result = parse_founders_from_html(SAMPLE_HTML_WITH_FOUNDERS)
    assert result is not None
    assert result["founder_name"] == "Alice Smith"
    assert result["founder_title"] == "CEO"
    assert result["founder_avatar_url"] == "https://bookface-images.s3.us-west-2.amazonaws.com/avatars/abc.jpg"
    assert result["founder_linkedin"] == "https://linkedin.com/in/alice"
    assert result["founder_twitter"] == "https://twitter.com/alice"


SAMPLE_HTML_NO_FOUNDERS = '''
<html><body>
<div>&quot;company&quot;:{&quot;name&quot;:&quot;EmptyCo&quot;,&quot;founders&quot;:[],&quot;editUrl&quot;:&quot;https://bookface.ycombinator.com&quot;}</div>
</body></html>
'''


def test_parse_founders_returns_none_when_empty():
    result = parse_founders_from_html(SAMPLE_HTML_NO_FOUNDERS)
    assert result is None


def test_parse_founders_returns_none_for_bad_html():
    result = parse_founders_from_html("<html><body>no data here</body></html>")
    assert result is None


SAMPLE_HTML_INACTIVE_FOUNDER = '''
<html><body>
<div>&quot;founders&quot;:[{&quot;user_id&quot;:1,&quot;is_active&quot;:false,&quot;full_name&quot;:&quot;Gone Guy&quot;,&quot;title&quot;:&quot;Ex-CEO&quot;,&quot;avatar_thumb_url&quot;:&quot;&quot;,&quot;linkedin_url&quot;:&quot;&quot;,&quot;twitter_url&quot;:&quot;&quot;,&quot;has_email&quot;:false},{&quot;user_id&quot;:2,&quot;is_active&quot;:true,&quot;full_name&quot;:&quot;Active Alice&quot;,&quot;title&quot;:&quot;CEO&quot;,&quot;avatar_thumb_url&quot;:&quot;https://bookface-images.s3.us-west-2.amazonaws.com/avatars/xyz.jpg&quot;,&quot;linkedin_url&quot;:&quot;https://linkedin.com/in/active&quot;,&quot;twitter_url&quot;:&quot;&quot;,&quot;has_email&quot;:true}],&quot;editUrl&quot;:&quot;x&quot;</div>
</body></html>
'''


def test_parse_founders_skips_inactive():
    result = parse_founders_from_html(SAMPLE_HTML_INACTIVE_FOUNDER)
    assert result is not None
    assert result["founder_name"] == "Active Alice"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3.12 -m pytest tests/pipeline/test_scrape_founders.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'backend.pipeline.scrape_founders'`

- [ ] **Step 3: Implement scrape_founders.py**

Create `backend/pipeline/scrape_founders.py`:

```python
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
    # Find the encoded JSON blob containing founders
    match = re.search(
        r'&quot;founders&quot;:\[(.+?)\],?\s*&quot;(?:editUrl|jobPostings)',
        page_html,
    )
    if not match:
        return None

    # Decode HTML entities and parse
    raw = "[" + html.unescape(match.group(1)) + "]"
    try:
        founders = json.loads(raw)
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3.12 -m pytest tests/pipeline/test_scrape_founders.py -v
```

Expected: All 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/scrape_founders.py tests/pipeline/
git commit -m "feat: add founder scraper — extract name, title, photo, LinkedIn from YC pages"
```

---

### Task 3: Run the founder scraper

**Files:** None (execution only)

- [ ] **Step 1: Run the founder scraper**

```bash
python3.12 -m backend.pipeline.scrape_founders
```

Expected: ~25 minutes. Progress logged every 50 companies. Output: `data/founders.json`.

If interrupted (Ctrl+C), re-running will resume from where it left off.

- [ ] **Step 2: Verify the output**

```bash
python3.12 -c "
import json
d = json.load(open('data/founders.json'))
total = len(d)
has_name = sum(1 for f in d if f.get('founder_name'))
has_avatar = sum(1 for f in d if f.get('founder_avatar_url'))
has_linkedin = sum(1 for f in d if f.get('founder_linkedin'))
print(f'Total: {total}')
print(f'With name: {has_name}')
print(f'With avatar: {has_avatar}')
print(f'With LinkedIn: {has_linkedin}')
print(f'Sample: {json.dumps(d[0], indent=2)}')
"
```

Expected: Most companies have founder names and avatars.

- [ ] **Step 3: Commit founders data**

```bash
git add data/founders.json
git commit -m "data: add scraped founder data for 1519 companies"
```

---

### Task 4: Update schema + supabase_write + schemas

**Files:**
- Modify: `backend/db/schema.sql`
- Modify: `backend/pipeline/supabase_write.py`
- Modify: `backend/schemas.py`

- [ ] **Step 1: Update schema.sql with new columns**

In `backend/db/schema.sql`, add 4 new columns to the companies table definition. After the `founder_twitter text,` line, add:

```sql
  founder_avatar_url text,
  founder_email text,
  slug text,
  small_logo_url text,
```

The full companies column list should now include:
```
founder_name, founder_title, founder_linkedin, founder_twitter, founder_avatar_url, founder_email, slug, small_logo_url
```

- [ ] **Step 2: Run migration SQL in Supabase**

Run this in the Supabase SQL Editor:

```sql
ALTER TABLE companies ADD COLUMN IF NOT EXISTS slug text;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS small_logo_url text;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS founder_avatar_url text;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS founder_email text;
```

Expected: `Success. No rows returned.`

- [ ] **Step 3: Update COMPANY_COLUMNS in supabase_write.py**

In `backend/pipeline/supabase_write.py`, update the `COMPANY_COLUMNS` list to include the new fields:

```python
COMPANY_COLUMNS = [
    "name", "yc_batch", "description", "long_description", "summary", "one_liner",
    "website", "industry", "stage", "stage_detail", "technical_level", "team_size",
    "need_tags", "specific_projects", "is_hiring", "status", "reachability_score",
    "reachability_probability", "all_locations", "tags", "industries",
    "slug", "small_logo_url",
    "founder_name", "founder_title", "founder_avatar_url",
    "founder_linkedin", "founder_twitter", "founder_email",
]
```

- [ ] **Step 4: Update merge_company_data to include founder and logo data**

Replace the `merge_company_data` function in `backend/pipeline/supabase_write.py`:

```python
FOUNDERS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "founders.json")


def merge_company_data(enriched: list[dict], scores: list[dict], raw: list[dict], founders: list[dict]) -> list[dict]:
    """Merge enriched company data with scores, raw fields, and founder data."""
    score_map = {s["name"]: s for s in scores}
    raw_map = {r["name"]: r for r in raw}
    founder_map = {f["company_name"]: f for f in founders}

    merged = []
    for company in enriched:
        name = company["name"]
        score_data = score_map.get(name, {})
        raw_data = raw_map.get(name, {})
        founder_data = founder_map.get(name, {})

        record = {}
        for col in COMPANY_COLUMNS:
            if col in company:
                record[col] = company[col]
            elif col in score_data:
                record[col] = score_data[col]

        # Map 'batch' field name to 'yc_batch'
        if "yc_batch" not in record and "batch" in company:
            record["yc_batch"] = company["batch"]

        # Default reachability if missing
        record.setdefault("reachability_score", "low")
        record.setdefault("reachability_probability", 0.0)

        # Add slug and logo from raw Algolia data
        record["slug"] = raw_data.get("slug") or None
        record["small_logo_url"] = raw_data.get("small_logo_thumb_url") or None

        # Add founder data
        record["founder_name"] = founder_data.get("founder_name")
        record["founder_title"] = founder_data.get("founder_title")
        record["founder_avatar_url"] = founder_data.get("founder_avatar_url")
        record["founder_linkedin"] = founder_data.get("founder_linkedin")
        record["founder_twitter"] = founder_data.get("founder_twitter")
        record["founder_email"] = None  # Placeholder for future email resolution

        merged.append(record)

    return merged
```

- [ ] **Step 5: Update write_to_supabase to load raw and founders data**

Replace the `write_to_supabase` function:

```python
def write_to_supabase(
    enriched_path: str = ENRICHED_OUTPUT_PATH,
    scores_path: str = SCORES_OUTPUT_PATH,
    raw_path: str = None,
    founders_path: str = FOUNDERS_PATH,
):
    """Full pipeline step: read files, merge, upload."""
    if raw_path is None:
        raw_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw_companies.json")

    with open(enriched_path) as f:
        enriched = json.load(f)

    with open(scores_path) as f:
        scores = json.load(f)

    with open(raw_path) as f:
        raw = json.load(f)

    founders = []
    if os.path.exists(founders_path):
        with open(founders_path) as f:
            founders = json.load(f)

    print(f"[INFO] Loaded {len(enriched)} enriched, {len(scores)} scores, {len(raw)} raw, {len(founders)} founders")

    merged = merge_company_data(enriched, scores, raw, founders)
    print(f"[INFO] Merged {len(merged)} companies")

    upload_to_supabase(merged)
    print(f"[DONE] Uploaded {len(merged)} companies to Supabase")
```

- [ ] **Step 6: Add new fields to backend schemas**

In `backend/schemas.py`, add to `CompanyCard` (after `reachability_score`):

```python
    small_logo_url: str | None = None
```

Add to `CompanyBrief` (after `founder_twitter`):

```python
    founder_avatar_url: str | None = None
    founder_email: str | None = None
    small_logo_url: str | None = None
    slug: str | None = None
```

- [ ] **Step 7: Commit**

```bash
git add backend/db/schema.sql backend/pipeline/supabase_write.py backend/schemas.py
git commit -m "feat: update schema and supabase_write to include founder and logo data"
```

---

### Task 5: Upload enriched data to Supabase

**Files:** None (execution only)

- [ ] **Step 1: Run supabase_write**

```bash
python3.12 -m backend.pipeline.supabase_write
```

Expected: Upserts ~1519 companies in 3-4 batches. All founder fields populated where available.

- [ ] **Step 2: Verify in Supabase**

```bash
python3.12 -c "
from dotenv import load_dotenv
load_dotenv('backend/.env')
from backend.db import get_supabase_client
db = get_supabase_client()
result = db.table('companies').select('name, founder_name, founder_avatar_url, small_logo_url, slug').limit(5).execute()
for r in result.data:
    print(r)
"
```

Expected: Companies show founder_name, avatar URL, logo URL, and slug.

- [ ] **Step 3: Count enrichment coverage**

```bash
python3.12 -c "
from dotenv import load_dotenv
load_dotenv('backend/.env')
from backend.db import get_supabase_client
db = get_supabase_client()
total = db.table('companies').select('id', count='exact').execute()
with_founder = db.table('companies').select('id', count='exact').not_.is_('founder_name', 'null').execute()
with_logo = db.table('companies').select('id', count='exact').not_.is_('small_logo_url', 'null').execute()
print(f'Total: {total.count}')
print(f'With founder: {with_founder.count}')
print(f'With logo: {with_logo.count}')
"
```

- [ ] **Step 4: Run existing API tests to check nothing broke**

```bash
python3.12 -m pytest tests/api/ -v
```

Expected: All tests pass (the pre-existing ranking test may still fail — that's unrelated).

- [ ] **Step 5: Commit any remaining changes**

```bash
git add -A
git commit -m "data: upload founder-enriched company data to Supabase"
```
