# Interest-Based Matching + Email Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace capability-based skill matching with interest/domain alignment using YC's own tags, resolve founder email addresses via a multi-source cascade, and enrich briefs with founder bios — all pipeline-first so data discovery informs API and frontend decisions.

**Architecture:** Three sequential phases. Phase 1 runs offline pipeline scripts on the dev machine to scrape new data (founder bios, has_email), curate YC tags into a clean vocabulary, resolve founder emails via website/GitHub/pattern-guessing, and upload everything to Supabase. Phase 2 rewrites the backend API to match on interests instead of capabilities, adds name search, enriches the email prompt with projects/founder_bio/URLs. Phase 3 rebuilds the frontend to use the new data. Each phase informs the next — no frozen contracts, real data drives decisions.

**Tech Stack:** Python 3, FastAPI, Supabase PostgreSQL, Next.js 16, Tailwind v4, pytest

---

## File Map

### Phase 1 — Pipeline (offline, dev machine)
| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `backend/pipeline/scrape_founders.py` | Extract `founder_bio` + `has_email` from YC pages |
| Modify | `tests/pipeline/test_scrape_founders.py` | Test new field extraction |
| Create | `backend/pipeline/curate_tags.py` | Collapse/filter 232 YC tags → curated vocabulary |
| Create | `tests/pipeline/test_curate_tags.py` | Test tag curation logic |
| Create | `backend/pipeline/resolve_emails.py` | Multi-source email resolution cascade |
| Create | `tests/pipeline/test_resolve_emails.py` | Test email extraction/verification |
| Modify | `backend/pipeline/supabase_write.py` | Write new fields to DB |
| Modify | `tests/pipeline/test_supabase_write.py` | Test new field merging |
| Create | `data/curated_tags.json` | Output: curated tag vocabulary |
| Create | `data/resolved_emails.json` | Output: resolved email addresses |

### Phase 2 — Backend API
| Action | File | Responsibility |
|--------|------|---------------|
| Create | `backend/interests.py` | Load curated tag vocabulary, expose categories + mapping |
| Modify | `backend/schemas.py` | Add new fields to UserProfile, UserUpdate, CompanyCard, CompanyBrief |
| Modify | `backend/matching/scorer.py` | Rewrite: interest overlap → sort by match then reachability |
| Modify | `backend/routers/companies.py` | Add `search` param, use interests for matching |
| Modify | `backend/routers/users.py` | Add `GET /interests` endpoint |
| Modify | `backend/email/prompt.py` | New prompt with projects, founder_bio, URLs |
| Modify | `backend/routers/email.py` | Pass new fields to email generation |
| Modify | `tests/matching/test_scorer.py` | Test new interest-based matching |
| Modify | `tests/email/test_prompt.py` | Test new prompt shape |
| Create | `tests/api/test_interests.py` | Test interests endpoint |
| Modify | `tests/api/test_companies.py` | Test search param |

### Phase 3 — Frontend
| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `frontend/lib/types.ts` | Add new fields to types |
| Create | `frontend/lib/interests.ts` | Interest vocabulary + labels (fetched from API) |
| Modify | `frontend/lib/api.ts` | Add `fetchInterests()`, update existing calls |
| Create | `frontend/components/InterestPicker.tsx` | Category-expandable interest selector, max 2 |
| Modify | `frontend/app/onboard/page.tsx` | Swap CapabilityPicker → InterestPicker |
| Modify | `frontend/app/profile/page.tsx` | InterestPicker + projects textarea + resume_url |
| Modify | `frontend/components/FounderCard.tsx` | Show YC tags + email availability badge |
| Modify | `frontend/app/feed/page.tsx` | Backend search, show YC tags |
| Modify | `frontend/components/FounderBrief.tsx` | Show founder_bio, YC tags, interest overlap |
| Modify | `frontend/components/EmailWorkspace.tsx` | Pre-fill recipient, confidence note, LinkedIn fallback |
| Delete | `frontend/components/SkillPicker.tsx` | Dead code |
| Delete | `frontend/lib/skills.ts` | Dead code (96KB) |
| Delete | `backend/ml/` | Deprecated XGBoost code |
| Delete | `backend/email/generate_test_batch.py` | Test script, not production |

---

## PHASE 1: PIPELINE DISCOVERY

---

### Task 1: Extract founder_bio and has_email from YC pages

**Files:**
- Modify: `backend/pipeline/scrape_founders.py:72-79`
- Modify: `tests/pipeline/test_scrape_founders.py`

- [ ] **Step 1: Write failing test for founder_bio extraction**

Add to `tests/pipeline/test_scrape_founders.py`:

```python
def test_parse_founders_extracts_bio_and_has_email():
    result = parse_founders_from_html(SAMPLE_HTML_WITH_FOUNDERS)
    assert result is not None
    assert "founder_bio" in result
    assert "has_email" in result


SAMPLE_HTML_WITH_BIO = '''
<html><body>
<div>&quot;founders&quot;:[{&quot;user_id&quot;:123,&quot;is_active&quot;:true,&quot;founder_bio&quot;:&quot;Alice is a serial entrepreneur who previously founded DataCo.&quot;,&quot;full_name&quot;:&quot;Alice Smith&quot;,&quot;title&quot;:&quot;CEO&quot;,&quot;avatar_thumb_url&quot;:&quot;https://bookface-images.s3.us-west-2.amazonaws.com/avatars/abc.jpg&quot;,&quot;linkedin_url&quot;:&quot;https://linkedin.com/in/alice&quot;,&quot;twitter_url&quot;:&quot;https://twitter.com/alice&quot;,&quot;has_email&quot;:true}],&quot;editUrl&quot;:&quot;x&quot;</div>
</body></html>
'''


def test_parse_founders_extracts_bio_text():
    result = parse_founders_from_html(SAMPLE_HTML_WITH_BIO)
    assert result["founder_bio"] == "Alice is a serial entrepreneur who previously founded DataCo."
    assert result["has_email"] is True


SAMPLE_HTML_NO_BIO = '''
<html><body>
<div>&quot;founders&quot;:[{&quot;user_id&quot;:456,&quot;is_active&quot;:true,&quot;full_name&quot;:&quot;Bob Jones&quot;,&quot;title&quot;:&quot;CTO&quot;,&quot;avatar_thumb_url&quot;:&quot;&quot;,&quot;linkedin_url&quot;:&quot;&quot;,&quot;twitter_url&quot;:&quot;&quot;,&quot;has_email&quot;:false}],&quot;editUrl&quot;:&quot;x&quot;</div>
</body></html>
'''


def test_parse_founders_handles_missing_bio():
    result = parse_founders_from_html(SAMPLE_HTML_NO_BIO)
    assert result["founder_bio"] is None
    assert result["has_email"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/pipeline/test_scrape_founders.py -v`
Expected: `test_parse_founders_extracts_bio_and_has_email` FAILS (KeyError: 'founder_bio')

- [ ] **Step 3: Update parse_founders_from_html to extract new fields**

In `backend/pipeline/scrape_founders.py`, replace lines 73-79:

```python
    return {
        "founder_name": founder.get("full_name") or None,
        "founder_title": founder.get("title") or None,
        "founder_avatar_url": strip_s3_signature(founder.get("avatar_thumb_url")),
        "founder_linkedin": founder.get("linkedin_url") or None,
        "founder_twitter": founder.get("twitter_url") or None,
        "founder_bio": founder.get("founder_bio") or None,
        "has_email": founder.get("has_email", False),
    }
```

Also update the fallback dict in `scrape_all_founders` (lines 126-131 and 142-147) to include the new fields:

```python
            results.append({
                "company_name": name,
                "founder_name": None,
                "founder_title": None,
                "founder_avatar_url": None,
                "founder_linkedin": None,
                "founder_twitter": None,
                "founder_bio": None,
                "has_email": False,
            })
```

There are two fallback dicts in the function — update both (the no-slug case and the error case).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/pipeline/test_scrape_founders.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/scrape_founders.py tests/pipeline/test_scrape_founders.py
git commit -m "feat: extract founder_bio and has_email from YC pages"
```

- [ ] **Step 6: Run the re-scrape**

```bash
python -m backend.pipeline.scrape_founders
```

This takes ~25 minutes (1,517 companies × 1s delay). It will resume if interrupted — existing results are preserved.

- [ ] **Step 7: Print discovery stats**

```bash
python -c "
import json
with open('data/founders.json') as f:
    data = json.load(f)
total = len(data)
has_bio = sum(1 for f in data if f.get('founder_bio'))
has_email = sum(1 for f in data if f.get('has_email'))
bio_lengths = [len(f['founder_bio']) for f in data if f.get('founder_bio')]
print(f'Total founders: {total}')
print(f'With bio: {has_bio} ({has_bio/total*100:.1f}%)')
print(f'With has_email=true: {has_email} ({has_email/total*100:.1f}%)')
if bio_lengths:
    print(f'Bio length: avg={sum(bio_lengths)//len(bio_lengths)}, min={min(bio_lengths)}, max={max(bio_lengths)}')
"
```

**CHECKPOINT:** Review stats. If bio coverage is below 50%, investigate why — some pages may have changed format. Report findings before proceeding.

---

### Task 2: Curate YC tags into interest vocabulary

**Files:**
- Create: `backend/pipeline/curate_tags.py`
- Create: `tests/pipeline/test_curate_tags.py`
- Output: `data/curated_tags.json`

- [ ] **Step 1: Write failing tests for tag curation**

Create `tests/pipeline/test_curate_tags.py`:

```python
"""Tests for YC tag curation logic."""

import pytest
from backend.pipeline.curate_tags import (
    collapse_duplicates,
    filter_by_frequency,
    build_categories,
)


SAMPLE_TAG_COUNTS = {
    "Artificial Intelligence": 422,
    "AI": 381,
    "Machine Learning": 51,
    "B2B": 351,
    "SaaS": 249,
    "Developer Tools": 191,
    "Generative AI": 143,
    "Fintech": 118,
    "Healthcare": 65,
    "Open Source": 66,
    "Biotech": 35,
    "Niche Tag": 3,
}

# Collapse map: keys are raw tags, values are the canonical name they merge into
COLLAPSE_MAP = {
    "AI": "AI / Machine Learning",
    "Artificial Intelligence": "AI / Machine Learning",
    "Machine Learning": "AI / Machine Learning",
}


def test_collapse_duplicates_merges_counts():
    collapsed = collapse_duplicates(SAMPLE_TAG_COUNTS, COLLAPSE_MAP)
    # AI + Artificial Intelligence + Machine Learning = 422 + 381 + 51 = 854
    assert collapsed["AI / Machine Learning"] == 854
    assert "AI" not in collapsed
    assert "Artificial Intelligence" not in collapsed
    assert "Machine Learning" not in collapsed
    # Unaffected tags remain
    assert collapsed["Developer Tools"] == 191


def test_filter_by_frequency_removes_extremes():
    tag_counts = {
        "Too Broad": 400,
        "Good Tag": 50,
        "Also Good": 20,
        "Too Niche": 3,
    }
    filtered = filter_by_frequency(tag_counts, min_count=5, max_count=300)
    assert "Good Tag" in filtered
    assert "Also Good" in filtered
    assert "Too Broad" not in filtered
    assert "Too Niche" not in filtered


def test_build_categories_groups_tags():
    tags = ["Generative AI", "Developer Tools", "Open Source", "Fintech", "Biotech"]
    # Category assignments map tag -> category name
    category_assignments = {
        "Generative AI": "AI / Machine Learning",
        "Developer Tools": "Developer Tools & Infrastructure",
        "Open Source": "Developer Tools & Infrastructure",
        "Fintech": "Finance",
        "Biotech": "Healthcare & Bio",
    }
    categories = build_categories(tags, category_assignments)
    ai_cat = next(c for c in categories if c["name"] == "AI / Machine Learning")
    assert "Generative AI" in ai_cat["tags"]
    devtools_cat = next(c for c in categories if c["name"] == "Developer Tools & Infrastructure")
    assert "Developer Tools" in devtools_cat["tags"]
    assert "Open Source" in devtools_cat["tags"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/pipeline/test_curate_tags.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'backend.pipeline.curate_tags')

- [ ] **Step 3: Implement curate_tags.py**

Create `backend/pipeline/curate_tags.py`:

```python
"""Curate YC's 232 raw tags into a clean interest vocabulary.

Collapses duplicates, removes too-broad/too-niche tags, groups into
visual categories for the frontend interest picker.
"""

import json
import os
from collections import Counter

_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
RAW_DATA_PATH = os.path.join(_ROOT, "data", "raw_companies.json")
OUTPUT_PATH = os.path.join(_ROOT, "data", "curated_tags.json")

MIN_TAG_COUNT = 5
MAX_TAG_COUNT = 300

# Tags that should be merged into a single canonical tag.
# Key = raw YC tag, Value = canonical name.
COLLAPSE_MAP = {
    "AI": "AI / Machine Learning",
    "Artificial Intelligence": "AI / Machine Learning",
    "Machine Learning": "AI / Machine Learning",
    "AIOps": "AI / Machine Learning",
    "Enterprise": "Enterprise Software",
    "Enterprise Software": "Enterprise Software",
}

# Manual assignment of curated tags to visual categories.
# Tags not listed here go into an "Other" category.
CATEGORY_ASSIGNMENTS = {
    "Generative AI": "AI / Machine Learning",
    "AI Assistant": "AI / Machine Learning",
    "Conversational AI": "AI / Machine Learning",
    "Computer Vision": "AI / Machine Learning",
    "NLP": "AI / Machine Learning",
    "Developer Tools": "Developer Tools & Infrastructure",
    "Infrastructure": "Developer Tools & Infrastructure",
    "Open Source": "Developer Tools & Infrastructure",
    "API": "Developer Tools & Infrastructure",
    "DevOps": "Developer Tools & Infrastructure",
    "Fintech": "Finance & Payments",
    "Payments": "Finance & Payments",
    "Finance": "Finance & Payments",
    "Healthcare": "Healthcare & Bio",
    "Health Tech": "Healthcare & Bio",
    "Biotech": "Healthcare & Bio",
    "Drug Discovery": "Healthcare & Bio",
    "Diagnostics": "Healthcare & Bio",
    "Analytics": "Data & Analytics",
    "Data Engineering": "Data & Analytics",
    "Automation": "Operations & Automation",
    "Workflow Automation": "Operations & Automation",
    "Logistics": "Operations & Automation",
    "Sales": "Sales & Marketing",
    "Marketing": "Sales & Marketing",
    "Compliance": "Security & Compliance",
    "Security": "Security & Compliance",
    "Education": "Education & Research",
    "Climate": "Climate & Energy",
    "Robotics": "Hardware & Robotics",
    "Consumer": "Consumer",
    "Productivity": "Productivity",
}


def count_raw_tags(raw_path: str = RAW_DATA_PATH) -> dict[str, int]:
    """Count occurrences of each tag across all companies."""
    with open(raw_path) as f:
        companies = json.load(f)
    counts: dict[str, int] = Counter()
    for company in companies:
        for tag in company.get("tags", []):
            counts[tag] += 1
    return dict(counts)


def collapse_duplicates(
    tag_counts: dict[str, int], collapse_map: dict[str, str]
) -> dict[str, int]:
    """Merge duplicate tags into canonical names, summing their counts."""
    collapsed: dict[str, int] = {}
    for tag, count in tag_counts.items():
        canonical = collapse_map.get(tag, tag)
        collapsed[canonical] = collapsed.get(canonical, 0) + count
    return collapsed


def filter_by_frequency(
    tag_counts: dict[str, int],
    min_count: int = MIN_TAG_COUNT,
    max_count: int = MAX_TAG_COUNT,
) -> dict[str, int]:
    """Remove tags that are too broad or too niche."""
    return {
        tag: count
        for tag, count in tag_counts.items()
        if min_count <= count <= max_count
    }


def build_categories(
    tags: list[str], category_assignments: dict[str, str]
) -> list[dict]:
    """Group tags into named categories for the frontend picker."""
    cat_map: dict[str, list[str]] = {}
    for tag in sorted(tags):
        category = category_assignments.get(tag, "Other")
        cat_map.setdefault(category, []).append(tag)

    return [{"name": name, "tags": tags} for name, tags in sorted(cat_map.items())]


def map_company_tags(
    company_raw_tags: list[str],
    collapse_map: dict[str, str],
    valid_tags: set[str],
) -> list[str]:
    """Map a company's raw YC tags to curated tags, dropping invalid ones."""
    mapped = set()
    for tag in company_raw_tags:
        canonical = collapse_map.get(tag, tag)
        if canonical in valid_tags:
            mapped.add(canonical)
    return sorted(mapped)


def curate_tags(raw_path: str = RAW_DATA_PATH, output_path: str = OUTPUT_PATH):
    """Full curation pipeline: count → collapse → filter → categorize → save."""
    raw_counts = count_raw_tags(raw_path)
    print(f"[INFO] Raw unique tags: {len(raw_counts)}")

    collapsed = collapse_duplicates(raw_counts, COLLAPSE_MAP)
    print(f"[INFO] After collapsing duplicates: {len(collapsed)}")

    filtered = filter_by_frequency(collapsed)
    print(f"[INFO] After frequency filter ({MIN_TAG_COUNT}-{MAX_TAG_COUNT}): {len(filtered)}")

    valid_tags = set(filtered.keys())
    categories = build_categories(list(valid_tags), CATEGORY_ASSIGNMENTS)

    # Build reverse mapping: tag -> category
    tag_to_category = {}
    for cat in categories:
        for tag in cat["tags"]:
            tag_to_category[tag] = cat["name"]

    # Track what was removed and why
    removed = {
        "too_broad": {t: c for t, c in collapsed.items() if c > MAX_TAG_COUNT},
        "too_niche": {t: c for t, c in collapsed.items() if c < MIN_TAG_COUNT},
        "collapsed_into": {k: v for k, v in COLLAPSE_MAP.items() if k != v},
    }

    output = {
        "categories": categories,
        "tag_to_category": tag_to_category,
        "valid_tags": sorted(valid_tags),
        "removed": removed,
        "stats": {
            "raw_unique": len(raw_counts),
            "after_collapse": len(collapsed),
            "final_curated": len(filtered),
            "num_categories": len(categories),
        },
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"[DONE] {len(filtered)} curated tags in {len(categories)} categories → {output_path}")

    # Print distribution
    for cat in categories:
        print(f"  {cat['name']}: {', '.join(cat['tags'])}")

    return output


if __name__ == "__main__":
    curate_tags()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/pipeline/test_curate_tags.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/curate_tags.py tests/pipeline/test_curate_tags.py
git commit -m "feat: add YC tag curation pipeline script"
```

- [ ] **Step 6: Run the curation**

```bash
python -m backend.pipeline.curate_tags
```

- [ ] **Step 7: Review output and print per-company stats**

```bash
python -c "
import json
with open('data/curated_tags.json') as f:
    curated = json.load(f)
print('=== CURATED TAGS ===')
for cat in curated['categories']:
    print(f\"  {cat['name']}: {cat['tags']}\")
print(f\"Total tags: {curated['stats']['final_curated']}\")
print(f\"Categories: {curated['stats']['num_categories']}\")
print()

# Check per-company distribution
from backend.pipeline.curate_tags import map_company_tags, COLLAPSE_MAP
valid = set(curated['valid_tags'])
with open('data/raw_companies.json') as f:
    companies = json.load(f)
tag_counts = [len(map_company_tags(c.get('tags', []), COLLAPSE_MAP, valid)) for c in companies]
zero = sum(1 for t in tag_counts if t == 0)
print(f'Companies with 0 curated tags: {zero}/{len(companies)}')
print(f'Avg curated tags per company: {sum(tag_counts)/len(tag_counts):.1f}')
print(f'Distribution: {dict(sorted(Counter(tag_counts).items()))}')
" 2>&1
```

**CHECKPOINT:** Review the categories. Do they feel natural? Are there too many "Other" tags? Is the per-company tag count reasonable (1-3 is ideal)? Adjust `COLLAPSE_MAP`, `CATEGORY_ASSIGNMENTS`, `MIN_TAG_COUNT`, and `MAX_TAG_COUNT` constants and re-run if needed. Report findings before proceeding.

---

### Task 3: Email resolution — website scraping

**Files:**
- Create: `backend/pipeline/resolve_emails.py`
- Create: `tests/pipeline/test_resolve_emails.py`
- Output: `data/resolved_emails.json`

- [ ] **Step 1: Write failing tests for email extraction helpers**

Create `tests/pipeline/test_resolve_emails.py`:

```python
"""Tests for email resolution — parsing logic only (no network)."""

import pytest
from backend.pipeline.resolve_emails import (
    extract_domain,
    extract_emails_from_html,
    filter_generic_emails,
    guess_email_patterns,
    match_founder_email,
)


def test_extract_domain_simple():
    assert extract_domain("https://www.pando.bio/") == "pando.bio"
    assert extract_domain("https://yuma.ai") == "yuma.ai"
    assert extract_domain("http://metal.so") == "metal.so"


def test_extract_domain_with_subdomain():
    assert extract_domain("https://app.example.com") == "example.com"


def test_extract_domain_none():
    assert extract_domain(None) is None
    assert extract_domain("") is None


def test_extract_emails_from_html_finds_mailto():
    html = '<a href="mailto:alice@example.com">Contact</a>'
    emails = extract_emails_from_html(html, "example.com")
    assert "alice@example.com" in emails


def test_extract_emails_from_html_finds_plain_text():
    html = "<p>Reach us at bob@startup.io for inquiries</p>"
    emails = extract_emails_from_html(html, "startup.io")
    assert "bob@startup.io" in emails


def test_extract_emails_filters_wrong_domain():
    html = '<a href="mailto:user@gmail.com">Email</a> and alice@example.com'
    emails = extract_emails_from_html(html, "example.com")
    assert "alice@example.com" in emails
    assert "user@gmail.com" not in emails


def test_filter_generic_emails():
    emails = ["info@co.com", "hello@co.com", "alice@co.com", "support@co.com", "sales@co.com"]
    filtered = filter_generic_emails(emails)
    assert filtered == ["alice@co.com"]


def test_guess_email_patterns():
    patterns = guess_email_patterns("Alice", "Smith", "example.com")
    assert "alice@example.com" in patterns
    assert "alice.smith@example.com" in patterns
    assert "alicesmith@example.com" in patterns
    assert "a.smith@example.com" in patterns


def test_match_founder_email_picks_best():
    emails = ["alice@example.com", "bob@example.com"]
    result = match_founder_email(emails, "Alice", "Smith")
    assert result == "alice@example.com"


def test_match_founder_email_no_match():
    emails = ["jobs@example.com"]
    result = match_founder_email(emails, "Alice", "Smith")
    # Returns first non-generic email even if name doesn't match
    assert result == "jobs@example.com"


def test_match_founder_email_empty():
    result = match_founder_email([], "Alice", "Smith")
    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/pipeline/test_resolve_emails.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement resolve_emails.py**

Create `backend/pipeline/resolve_emails.py`:

```python
"""Resolve founder email addresses from multiple sources.

Cascade: website scrape → GitHub → pattern guess + SMTP verify.
Runs offline on dev machine. Only attempts founders with has_email=True.
"""

import json
import os
import re
import smtplib
import socket
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
FOUNDERS_PATH = os.path.join(_ROOT, "data", "founders.json")
RAW_DATA_PATH = os.path.join(_ROOT, "data", "raw_companies.json")
OUTPUT_PATH = os.path.join(_ROOT, "data", "resolved_emails.json")

REQUEST_DELAY = 1.0
REQUEST_TIMEOUT = 10
LOG_EVERY = 25

GENERIC_PREFIXES = {
    "info", "hello", "hi", "contact", "support", "help", "team",
    "admin", "sales", "press", "media", "jobs", "careers", "hr",
    "billing", "legal", "privacy", "security", "noreply", "no-reply",
}

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

WEBSITE_PATHS = ["", "/contact", "/about", "/team", "/about-us", "/contact-us"]

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def extract_domain(url: str | None) -> str | None:
    """Extract the root domain from a URL (strip www, path, etc)."""
    if not url:
        return None
    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        host = parsed.hostname or ""
        # Strip www prefix
        if host.startswith("www."):
            host = host[4:]
        # For subdomains like app.example.com, keep example.com
        parts = host.split(".")
        if len(parts) > 2:
            host = ".".join(parts[-2:])
        return host if host else None
    except Exception:
        return None


def extract_emails_from_html(html: str, domain: str) -> list[str]:
    """Extract all email addresses matching a domain from HTML content."""
    all_emails = EMAIL_REGEX.findall(html.lower())
    return list(set(e for e in all_emails if e.endswith(f"@{domain}")))


def filter_generic_emails(emails: list[str]) -> list[str]:
    """Remove generic addresses (info@, support@, etc)."""
    return [e for e in emails if e.split("@")[0] not in GENERIC_PREFIXES]


def guess_email_patterns(first_name: str, last_name: str, domain: str) -> list[str]:
    """Generate candidate email addresses from name + domain."""
    first = first_name.lower().strip()
    last = last_name.lower().strip()
    if not first or not domain:
        return []
    patterns = [
        f"{first}@{domain}",
        f"{first}.{last}@{domain}",
        f"{first}{last}@{domain}",
    ]
    if last:
        patterns.append(f"{first[0]}.{last}@{domain}")
    return patterns


def match_founder_email(
    emails: list[str], first_name: str, last_name: str
) -> str | None:
    """Pick the email most likely belonging to the founder."""
    if not emails:
        return None
    first = first_name.lower().strip()
    last = last_name.lower().strip()
    # Prefer emails containing the founder's first name
    for email in emails:
        local = email.split("@")[0]
        if first in local:
            return email
    # Then try last name
    for email in emails:
        local = email.split("@")[0]
        if last and last in local:
            return email
    # Fallback: return first email
    return emails[0]


def fetch_page(url: str) -> str | None:
    """Fetch a web page, return HTML or None on failure."""
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        resp = urlopen(req, timeout=REQUEST_TIMEOUT)
        return resp.read().decode("utf-8", errors="ignore")
    except (HTTPError, URLError, socket.timeout, Exception):
        return None


def scrape_website_for_email(
    website: str, domain: str, founder_first: str, founder_last: str
) -> str | None:
    """Crawl a company website for the founder's email address."""
    base = website.rstrip("/")
    all_emails = []

    for path in WEBSITE_PATHS:
        url = base + path
        html = fetch_page(url)
        if html:
            found = extract_emails_from_html(html, domain)
            all_emails.extend(found)
        time.sleep(0.5)

    personal = filter_generic_emails(all_emails)
    if personal:
        return match_founder_email(personal, founder_first, founder_last)
    return None


def check_mx_records(domain: str) -> bool:
    """Check if domain has MX records (accepts email)."""
    import subprocess
    try:
        result = subprocess.run(
            ["dig", "+short", "MX", domain],
            capture_output=True, text=True, timeout=5,
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def verify_smtp(email: str, domain: str) -> bool:
    """Attempt SMTP verification of an email address.

    Connects to the domain's MX server and issues RCPT TO
    without actually sending. Many servers block this, so
    a False result is inconclusive.
    """
    import subprocess
    try:
        # Get MX server
        result = subprocess.run(
            ["dig", "+short", "MX", domain],
            capture_output=True, text=True, timeout=5,
        )
        mx_lines = result.stdout.strip().split("\n")
        if not mx_lines or not mx_lines[0]:
            return False
        # Take lowest priority MX
        mx_host = mx_lines[0].split()[-1].rstrip(".")

        server = smtplib.SMTP(timeout=5)
        server.connect(mx_host, 25)
        server.helo("reach-verify.local")
        server.mail("verify@reach-verify.local")
        code, _ = server.rcpt(email)
        server.quit()
        return code == 250
    except Exception:
        return False


def split_founder_name(full_name: str) -> tuple[str, str]:
    """Split 'First Last' into (first, last). Handles edge cases."""
    if not full_name:
        return ("", "")
    parts = full_name.strip().split()
    first = parts[0] if parts else ""
    last = parts[-1] if len(parts) > 1 else ""
    return (first, last)


def resolve_all_emails(
    founders_path: str = FOUNDERS_PATH,
    raw_path: str = RAW_DATA_PATH,
    output_path: str = OUTPUT_PATH,
):
    """Run the full email resolution cascade."""
    with open(founders_path) as f:
        founders = json.load(f)
    with open(raw_path) as f:
        raw = json.load(f)

    website_map = {c["name"]: c.get("website", "") for c in raw}

    # Load existing results for resume support
    existing = {}
    if os.path.exists(output_path):
        with open(output_path) as f:
            for entry in json.load(f):
                existing[entry["company_name"]] = entry

    results = list(existing.values())
    resolved_names = set(existing.keys())

    stats = {"website": 0, "pattern": 0, "skipped": 0, "no_email_flag": 0, "failed": 0}

    eligible = [f for f in founders if f.get("has_email") and f["company_name"] not in resolved_names]
    print(f"[INFO] {len(eligible)} founders to resolve ({len(resolved_names)} already done)")

    for i, founder in enumerate(eligible):
        name = founder["company_name"]
        founder_name = founder.get("founder_name") or ""
        website = website_map.get(name, "")
        domain = extract_domain(website)
        first, last = split_founder_name(founder_name)

        resolved_email = None
        source = None
        confidence = None

        # Step 1: Website scrape
        if domain and website:
            resolved_email = scrape_website_for_email(website, domain, first, last)
            if resolved_email:
                source = "website"
                confidence = "high"
                stats["website"] += 1

        # Step 2: Pattern guess + MX/SMTP verify
        if not resolved_email and domain and first:
            candidates = guess_email_patterns(first, last, domain)
            if check_mx_records(domain):
                for candidate in candidates:
                    if verify_smtp(candidate, domain):
                        resolved_email = candidate
                        source = "pattern"
                        confidence = "medium"
                        stats["pattern"] += 1
                        break

        if not resolved_email:
            stats["failed"] += 1

        results.append({
            "company_name": name,
            "founder_email": resolved_email,
            "email_source": source,
            "email_confidence": confidence,
        })

        done = i + 1
        if done % LOG_EVERY == 0 or done == len(eligible):
            print(f"[INFO] {done}/{len(eligible)} processed | website={stats['website']} pattern={stats['pattern']} failed={stats['failed']}")

        # Save periodically
        if done % LOG_EVERY == 0:
            with open(output_path, "w") as f:
                json.dump(results, f, indent=2)

        time.sleep(REQUEST_DELAY)

    # Final save
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    total_resolved = stats["website"] + stats["pattern"]
    print(f"[DONE] Resolved {total_resolved}/{len(eligible)} emails")
    print(f"  Website: {stats['website']}")
    print(f"  Pattern+SMTP: {stats['pattern']}")
    print(f"  Failed: {stats['failed']}")
    return results


if __name__ == "__main__":
    resolve_all_emails()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/pipeline/test_resolve_emails.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/resolve_emails.py tests/pipeline/test_resolve_emails.py
git commit -m "feat: add email resolution cascade (website scrape + pattern guess)"
```

- [ ] **Step 6: Run the email resolution**

```bash
python -m backend.pipeline.resolve_emails
```

This will take a while (~1,500 founders × multiple page fetches × delays). It supports resume on interruption.

- [ ] **Step 7: Print discovery stats**

```bash
python -c "
import json
from collections import Counter
with open('data/resolved_emails.json') as f:
    data = json.load(f)
total = len(data)
by_source = Counter(e.get('email_source') for e in data if e.get('founder_email'))
by_confidence = Counter(e.get('email_confidence') for e in data if e.get('founder_email'))
resolved = sum(1 for e in data if e.get('founder_email'))
print(f'Total processed: {total}')
print(f'Resolved: {resolved} ({resolved/total*100:.1f}%)')
print(f'By source: {dict(by_source)}')
print(f'By confidence: {dict(by_confidence)}')
print(f'Unresolved: {total - resolved}')
"
```

**CHECKPOINT:** Review resolution rates. Key questions:
- What % resolved via website scraping? (target: 20-40%)
- What % via pattern+SMTP? (target: 10-20%)
- Total coverage? (target: 50%+ for the spec's success criteria)
- Any false positives spotted? Sample 5-10 resolved emails and manually verify.

Report findings before proceeding.

---

### Task 4: Update Supabase write to include new fields

**Files:**
- Modify: `backend/pipeline/supabase_write.py`
- Modify: `tests/pipeline/test_supabase_write.py`

- [ ] **Step 1: Write failing test for new field merging**

Add to `tests/pipeline/test_supabase_write.py`:

```python
def test_merge_includes_new_fields():
    enriched = [{"name": "TestCo", "description": "test", "summary": "test"}]
    scores = [{"name": "TestCo", "reachability_score": "high", "reachability_probability": 0.8}]
    raw = [{"name": "TestCo", "slug": "testco", "small_logo_thumb_url": "logo.png", "tags": ["AI", "Fintech"]}]
    founders = [{
        "company_name": "TestCo",
        "founder_name": "Alice",
        "founder_title": "CEO",
        "founder_avatar_url": "avatar.jpg",
        "founder_linkedin": "https://linkedin.com/in/alice",
        "founder_twitter": None,
        "founder_bio": "Alice is a serial entrepreneur.",
        "has_email": True,
    }]
    emails = [{"company_name": "TestCo", "founder_email": "alice@testco.com", "email_source": "website", "email_confidence": "high"}]

    # Will need to import the curated tag mapping
    curated_tags = {"AI / Machine Learning": ["AI"], "Finance & Payments": ["Fintech"]}
    tag_to_curated = {"AI": "AI / Machine Learning", "Fintech": "Finance & Payments"}

    merged = merge_company_data(enriched, scores, raw, founders, emails, tag_to_curated)
    assert len(merged) == 1
    company = merged[0]
    assert company["founder_bio"] == "Alice is a serial entrepreneur."
    assert company["has_email"] is True
    assert company["founder_email"] == "alice@testco.com"
    assert company["email_source"] == "website"
    assert company["email_confidence"] == "high"
    assert "AI / Machine Learning" in company["yc_tags"]
    assert "Finance & Payments" in company["yc_tags"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/pipeline/test_supabase_write.py::test_merge_includes_new_fields -v`
Expected: FAIL (merge_company_data signature changed)

- [ ] **Step 3: Update supabase_write.py**

In `backend/pipeline/supabase_write.py`:

Update `COMPANY_COLUMNS` to include new fields:

```python
COMPANY_COLUMNS = [
    "name", "yc_batch", "description", "long_description", "summary", "one_liner",
    "website", "industry", "stage", "stage_detail", "technical_level", "team_size",
    "need_tags", "specific_projects", "is_hiring", "status", "reachability_score",
    "reachability_probability", "all_locations", "tags", "industries",
    "slug", "small_logo_url",
    "founder_name", "founder_title", "founder_avatar_url",
    "founder_linkedin", "founder_twitter", "founder_email",
    "founder_bio", "has_email", "email_source", "email_confidence", "yc_tags",
]
```

Add paths for new data files:

```python
RESOLVED_EMAILS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "resolved_emails.json")
CURATED_TAGS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "curated_tags.json")
```

Update `merge_company_data` signature and implementation:

```python
def merge_company_data(
    enriched: list[dict],
    scores: list[dict],
    raw: list[dict],
    founders: list[dict],
    emails: list[dict] | None = None,
    tag_to_curated: dict[str, str] | None = None,
) -> list[dict]:
    """Merge enriched company data with scores, raw fields, founder data, emails, and curated tags."""
    score_map = {s["name"]: s for s in scores}
    raw_map = {r["name"]: r for r in raw}
    founder_map = {f["company_name"]: f for f in founders}
    email_map = {e["company_name"]: e for e in (emails or [])}

    merged = []
    for company in enriched:
        name = company["name"]
        score_data = score_map.get(name, {})
        raw_data = raw_map.get(name, {})
        founder_data = founder_map.get(name, {})
        email_data = email_map.get(name, {})

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
        record["founder_bio"] = founder_data.get("founder_bio")
        record["has_email"] = founder_data.get("has_email", False)

        # Add resolved email
        record["founder_email"] = email_data.get("founder_email")
        record["email_source"] = email_data.get("email_source")
        record["email_confidence"] = email_data.get("email_confidence")

        # Map raw YC tags to curated tags
        raw_tags = raw_data.get("tags", [])
        if tag_to_curated:
            curated = set()
            for tag in raw_tags:
                canonical = tag_to_curated.get(tag)
                if canonical:
                    curated.add(canonical)
            record["yc_tags"] = sorted(curated)
        else:
            record["yc_tags"] = []

        merged.append(record)

    return merged
```

Update `write_to_supabase` to load new files:

```python
def write_to_supabase(
    enriched_path: str = ENRICHED_OUTPUT_PATH,
    scores_path: str = SCORES_OUTPUT_PATH,
    raw_path: str = None,
    founders_path: str = FOUNDERS_PATH,
    emails_path: str = RESOLVED_EMAILS_PATH,
    curated_path: str = CURATED_TAGS_PATH,
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

    emails = []
    if os.path.exists(emails_path):
        with open(emails_path) as f:
            emails = json.load(f)

    tag_to_curated = {}
    if os.path.exists(curated_path):
        with open(curated_path) as f:
            curated = json.load(f)
        # Build reverse map: raw tag -> curated tag
        # The curated_tags.json has valid_tags and categories
        # We need to map raw YC tags to the curated canonical names
        from backend.pipeline.curate_tags import COLLAPSE_MAP
        valid_tags = set(curated.get("valid_tags", []))
        for raw_tag in set(t for c in raw for t in c.get("tags", [])):
            canonical = COLLAPSE_MAP.get(raw_tag, raw_tag)
            if canonical in valid_tags:
                tag_to_curated[raw_tag] = canonical

    print(f"[INFO] Loaded {len(enriched)} enriched, {len(scores)} scores, {len(raw)} raw, {len(founders)} founders, {len(emails)} emails")

    merged = merge_company_data(enriched, scores, raw, founders, emails, tag_to_curated)
    print(f"[INFO] Merged {len(merged)} companies")

    upload_to_supabase(merged)
    print(f"[DONE] Uploaded {len(merged)} companies to Supabase")
```

- [ ] **Step 4: Fix any existing tests that break due to signature change**

The existing tests in `test_supabase_write.py` call `merge_company_data` with the old 4-arg signature. Update them to pass `emails=None, tag_to_curated=None` or just rely on the defaults.

- [ ] **Step 5: Run all supabase_write tests**

Run: `python -m pytest tests/pipeline/test_supabase_write.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add backend/pipeline/supabase_write.py tests/pipeline/test_supabase_write.py
git commit -m "feat: include founder_bio, emails, and curated YC tags in Supabase write"
```

- [ ] **Step 7: Run DB migration**

Run this SQL in Supabase SQL Editor:

```sql
ALTER TABLE companies ADD COLUMN IF NOT EXISTS founder_bio text;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS has_email boolean DEFAULT false;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS email_source text;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS email_confidence text;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS yc_tags text[] DEFAULT '{}';
```

- [ ] **Step 8: Run the upload**

```bash
python -m backend.pipeline.supabase_write
```

- [ ] **Step 9: Verify data in Supabase**

```bash
python -c "
from backend.db import get_supabase_client
db = get_supabase_client()
result = db.table('companies').select('name, founder_bio, has_email, founder_email, email_confidence, yc_tags').limit(5).execute()
for r in result.data:
    print(r)
"
```

**PHASE 1 CHECKPOINT:** Review all data before proceeding to Phase 2:
- founder_bio coverage %
- email resolution coverage %
- curated tag distribution
- Sample 10 companies and verify data quality

Decide: which email confidence levels to surface in the UI. Recommend: only "high" and "medium". Report all findings.

---

## PHASE 2: BACKEND API CHANGES

---

### Task 5: Interest vocabulary module

**Files:**
- Create: `backend/interests.py`

- [ ] **Step 1: Create interests.py**

```python
"""Interest vocabulary — loads curated YC tags for matching and the frontend picker.

Replaces capabilities.py for matching purposes. capabilities.py is kept
for backwards compatibility but no longer used in ranking.
"""

import json
import os

_CURATED_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "curated_tags.json")

_CACHE: dict | None = None


def _load() -> dict:
    global _CACHE
    if _CACHE is None:
        with open(_CURATED_PATH) as f:
            _CACHE = json.load(f)
    return _CACHE


def get_categories() -> list[dict]:
    """Return list of {name, tags} for the frontend picker."""
    return _load()["categories"]


def get_valid_tags() -> set[str]:
    """Return the set of all valid curated tag strings."""
    return set(_load()["valid_tags"])


def get_tag_to_category() -> dict[str, str]:
    """Return mapping of curated tag -> category name."""
    return _load()["tag_to_category"]
```

- [ ] **Step 2: Commit**

```bash
git add backend/interests.py
git commit -m "feat: add interests module for curated tag vocabulary"
```

---

### Task 6: User schema changes

**Files:**
- Modify: `backend/schemas.py`

- [ ] **Step 1: Run DB migration for users table**

Run in Supabase SQL Editor:

```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS interests text[] DEFAULT '{}';
ALTER TABLE users ADD COLUMN IF NOT EXISTS projects text;
ALTER TABLE users ADD COLUMN IF NOT EXISTS resume_url text;
```

- [ ] **Step 2: Update UserProfile and UserUpdate schemas**

In `backend/schemas.py`, add new fields to `UserProfile`:

```python
class UserProfile(BaseModel):
    id: str
    email: str
    school: str | None = None
    grad_year: int | None = None
    skills: list[str] = []
    interests: list[str] = []
    location: str | None = None
    bio: str | None = None
    projects: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    resume_url: str | None = None
    tier: str = "free"
```

Add new fields to `UserUpdate`:

```python
class UserUpdate(BaseModel):
    school: str | None = None
    grad_year: int | None = None
    skills: list[str] | None = None
    interests: list[str] | None = None
    location: str | None = None
    bio: str | None = None
    projects: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    resume_url: str | None = None
```

Add new fields to `CompanyCard`:

```python
class CompanyCard(BaseModel):
    id: int
    name: str
    yc_batch: str | None = None
    one_liner: str | None = None
    industry: str | None = None
    stage_detail: str | None = None
    technical_level: str | None = None
    team_size: int | None = None
    reachability_score: str | None = None
    small_logo_url: str | None = None
    founder_name: str | None = None
    founder_title: str | None = None
    founder_avatar_url: str | None = None
    founder_email: str | None = None
    email_confidence: str | None = None
    has_email: bool = False
    need_tags: list[str] = []
    capability_tags: list[str] = []
    yc_tags: list[str] = []
    match_score: int = 0
    rank_score: float = 0.0
```

Add new fields to `CompanyBrief`:

```python
class CompanyBrief(BaseModel):
    id: int
    name: str
    yc_batch: str | None = None
    description: str | None = None
    summary: str | None = None
    one_liner: str | None = None
    website: str | None = None
    industry: str | None = None
    stage: str | None = None
    stage_detail: str | None = None
    technical_level: str | None = None
    team_size: int | None = None
    need_tags: list[str] = []
    capability_tags: list[str] = []
    yc_tags: list[str] = []
    specific_projects: list[str] = []
    reachability_score: str | None = None
    reachability_probability: float | None = None
    reachability_factors: list[str] = []
    founder_name: str | None = None
    founder_title: str | None = None
    founder_linkedin: str | None = None
    founder_twitter: str | None = None
    founder_avatar_url: str | None = None
    founder_email: str | None = None
    founder_bio: str | None = None
    email_confidence: str | None = None
    has_email: bool = False
    small_logo_url: str | None = None
    slug: str | None = None
    all_locations: str | None = None
    tags: list[str] = []
    industries: list[str] = []
    match_score: int = 0
    guidance: Guidance | None = None
```

- [ ] **Step 3: Run existing tests to check nothing breaks**

Run: `python -m pytest tests/api/ -v`
Expected: All PASS (new fields have defaults, so existing tests should be unaffected)

- [ ] **Step 4: Commit**

```bash
git add backend/schemas.py
git commit -m "feat: add interests, projects, resume_url, and company email fields to schemas"
```

---

### Task 7: Rewrite matching scorer

**Files:**
- Modify: `backend/matching/scorer.py`
- Modify: `tests/matching/test_scorer.py`

- [ ] **Step 1: Write new tests for interest-based matching**

Replace `tests/matching/test_scorer.py`:

```python
"""Tests for interest-based matching scorer."""

from backend.matching.scorer import match_score, rank_companies


def test_match_score_full_overlap():
    user_interests = ["Generative AI", "Developer Tools"]
    company_tags = ["Generative AI", "Developer Tools", "Open Source"]
    assert match_score(user_interests, company_tags) == 2


def test_match_score_partial_overlap():
    user_interests = ["Generative AI", "Fintech"]
    company_tags = ["Generative AI", "Healthcare"]
    assert match_score(user_interests, company_tags) == 1


def test_match_score_no_overlap():
    user_interests = ["Fintech", "Payments"]
    company_tags = ["Generative AI", "Developer Tools"]
    assert match_score(user_interests, company_tags) == 0


def test_match_score_empty():
    assert match_score([], ["Generative AI"]) == 0
    assert match_score(["Generative AI"], []) == 0
    assert match_score([], []) == 0


def test_rank_matches_first_then_reachability():
    companies = [
        {"id": 1, "name": "HighReachNoMatch", "yc_tags": ["Healthcare"], "reachability_probability": 0.95},
        {"id": 2, "name": "LowReachFullMatch", "yc_tags": ["Generative AI", "Fintech"], "reachability_probability": 0.3},
        {"id": 3, "name": "MidReachOneMatch", "yc_tags": ["Generative AI", "Healthcare"], "reachability_probability": 0.6},
    ]
    ranked = rank_companies(companies, ["Generative AI", "Fintech"])

    # Full match (2) comes first despite lowest reachability
    assert ranked[0]["name"] == "LowReachFullMatch"
    assert ranked[0]["match_score"] == 2
    # Partial match (1) second
    assert ranked[1]["name"] == "MidReachOneMatch"
    assert ranked[1]["match_score"] == 1
    # No match last despite highest reachability
    assert ranked[2]["name"] == "HighReachNoMatch"
    assert ranked[2]["match_score"] == 0


def test_rank_tiebreaks_by_reachability():
    companies = [
        {"id": 1, "name": "LowReach", "yc_tags": ["Generative AI"], "reachability_probability": 0.3},
        {"id": 2, "name": "HighReach", "yc_tags": ["Generative AI"], "reachability_probability": 0.9},
    ]
    ranked = rank_companies(companies, ["Generative AI"])

    # Same match score, higher reachability wins
    assert ranked[0]["name"] == "HighReach"
    assert ranked[1]["name"] == "LowReach"


def test_rank_no_interests_uses_reachability_only():
    companies = [
        {"id": 1, "name": "Low", "yc_tags": ["AI"], "reachability_probability": 0.3},
        {"id": 2, "name": "High", "yc_tags": ["AI"], "reachability_probability": 0.9},
    ]
    ranked = rank_companies(companies, user_interests=None)
    assert ranked[0]["name"] == "High"


def test_rank_zero_match_still_included():
    companies = [
        {"id": 1, "name": "NoMatch", "yc_tags": ["Healthcare"], "reachability_probability": 0.9},
    ]
    ranked = rank_companies(companies, ["Fintech"])
    assert len(ranked) == 1
    assert ranked[0]["match_score"] == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/matching/test_scorer.py -v`
Expected: FAIL (old function signatures)

- [ ] **Step 3: Rewrite scorer.py**

Replace `backend/matching/scorer.py`:

```python
"""Match scoring: rank companies by interest overlap, tiebreak by reachability.

Matching is now interest/domain alignment: how many of the student's
interest tags overlap with the startup's YC domain tags.
"""


def match_score(user_interests: list[str], company_yc_tags: list[str]) -> int:
    """Count overlapping tags between user interests and company YC tags."""
    if not user_interests or not company_yc_tags:
        return 0
    return len(set(user_interests) & set(company_yc_tags))


def rank_companies(
    companies: list[dict],
    user_interests: list[str] | None = None,
) -> list[dict]:
    """Rank companies: match count descending, then reachability descending.

    All companies are returned (including zero-match). Matches appear first.
    """
    scored = []
    for company in companies:
        company_tags = company.get("yc_tags") or []
        reachability = company.get("reachability_probability", 0.0) or 0.0

        if user_interests:
            ms = match_score(user_interests, company_tags)
        else:
            ms = 0

        scored.append({**company, "match_score": ms, "rank_score": 0.0})

    # Sort: match_score descending, then reachability descending
    scored.sort(key=lambda c: (c["match_score"], c.get("reachability_probability", 0.0)), reverse=True)
    return scored
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/matching/test_scorer.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/matching/scorer.py tests/matching/test_scorer.py
git commit -m "feat: rewrite matching to use interest/domain overlap with reachability tiebreak"
```

---

### Task 8: Add search and interests to companies endpoint

**Files:**
- Modify: `backend/routers/companies.py`
- Modify: `backend/routers/users.py`
- Modify: `tests/api/test_companies.py`

- [ ] **Step 1: Update companies.py — add search param + use interests**

In `backend/routers/companies.py`, update the `list_companies` function:

```python
@router.get("/companies", response_model=list[CompanyCard])
def list_companies(
    request: Request,
    industry: str | None = Query(None),
    reachability: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
):
    """Browse company cards. Ranked by interest match if authenticated."""
    db = get_db()
    user_id = get_optional_user(request)

    # Build query
    query = db.table("companies").select("*").eq("status", "Active")

    if industry:
        query = query.eq("industry", industry)
    if reachability:
        query = query.eq("reachability_score", reachability)
    if search:
        query = query.or_(f"name.ilike.%{search}%,founder_name.ilike.%{search}%")

    result = query.execute()
    companies = result.data

    # Get user interests and location if authenticated
    user_interests = None
    student_location = None
    if user_id:
        user_result = db.table("users").select("interests, location").eq("id", user_id).execute()
        if user_result.data:
            user_interests = user_result.data[0].get("interests")
            student_location = user_result.data[0].get("location")

    # Compute reachability scores on the fly
    for company in companies:
        score, factors = compute_reachability(company, student_location)
        company["reachability_probability"] = score
        company["reachability_score"] = bucket_score(score)

    # Rank and paginate
    ranked = rank_companies(companies, user_interests)
    start = (page - 1) * limit
    return ranked[start:start + limit]
```

Also update `get_brief` to use interests:

```python
@router.get("/companies/{company_id}", response_model=CompanyBrief)
def get_brief(
    company_id: int,
    request: Request,
    user_id: str = Depends(get_current_user),
):
    """Get full company brief."""
    db = get_db()

    result = db.table("companies").select("*").eq("id", company_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Company not found")
    company = result.data[0]

    user_result = db.table("users").select("interests, location").eq("id", user_id).execute()
    user = user_result.data[0] if user_result.data else {"interests": [], "location": None}

    try:
        db.table("brief_views").insert({"user_id": user_id, "company_id": company_id}).execute()
    except Exception:
        pass

    user_interests = user.get("interests", []) or []
    student_location = user.get("location")
    score, factors = compute_reachability(company, student_location)
    company["reachability_probability"] = score
    company["reachability_score"] = bucket_score(score)
    company["reachability_factors"] = factors

    ms = match_score(user_interests, company.get("yc_tags") or [])
    company["match_score"] = ms
    company["guidance"] = generate_guidance(user_interests, company)

    return company
```

- [ ] **Step 2: Add interests endpoint to users.py**

Add to `backend/routers/users.py`:

```python
from backend.interests import get_categories


@router.get("/interests")
def list_interests():
    """Return curated interest categories for the frontend picker."""
    return {"categories": get_categories()}
```

- [ ] **Step 3: Run all API tests**

Run: `python -m pytest tests/api/ -v`

Fix any tests that break due to the `skills` → `interests` change in the companies endpoint. The existing test mocks may need updating if they mock user data with `skills` field — add `interests` field to those mocks.

- [ ] **Step 4: Commit**

```bash
git add backend/routers/companies.py backend/routers/users.py
git commit -m "feat: add name search, interest matching, and interests endpoint"
```

---

### Task 9: Rework email prompt

**Files:**
- Modify: `backend/email/prompt.py`
- Modify: `backend/routers/email.py`
- Modify: `tests/email/test_prompt.py`

- [ ] **Step 1: Write new tests for the updated prompt**

Replace `tests/email/test_prompt.py`:

```python
"""Tests for the interest-aligned email prompt."""

from backend.email.prompt import build_email_prompt, TONES


def test_prompt_includes_student_projects():
    result = build_email_prompt(
        student_bio="HS junior",
        student_projects="Built a CNN plant disease classifier using PyTorch",
        student_interests=["Generative AI", "Healthcare"],
        portfolio_url="https://alice.dev",
        github_url="https://github.com/alice",
        resume_url=None,
        company_name="Pando Bioscience",
        company_summary="AI-driven enzyme engineering",
        specific_projects=["Enzyme screening pipeline"],
        founder_name="Will Cao",
        founder_bio="Will changed her major from engineering machines to engineering bacteria.",
        tone="curious",
    )
    assert "plant disease classifier" in result
    assert "Pando Bioscience" in result
    assert "Will Cao" in result
    assert "alice.dev" in result
    assert "github.com/alice" in result


def test_prompt_includes_founder_bio():
    result = build_email_prompt(
        student_bio="Student",
        student_projects=None,
        student_interests=["Developer Tools"],
        portfolio_url=None,
        github_url=None,
        resume_url=None,
        company_name="TestCo",
        company_summary="Dev tools for teams",
        specific_projects=[],
        founder_name="Bob",
        founder_bio="Bob spent 10 years at Google building infrastructure tools.",
        tone="friendly",
    )
    assert "10 years at Google" in result


def test_prompt_handles_all_none_optionals():
    result = build_email_prompt(
        student_bio="Student",
        student_projects=None,
        student_interests=[],
        portfolio_url=None,
        github_url=None,
        resume_url=None,
        company_name="TestCo",
        company_summary="Building things",
        specific_projects=[],
        founder_name="Sam",
        founder_bio=None,
        tone="curious",
    )
    assert "TestCo" in result
    assert "Sam" in result


def test_prompt_includes_resume_url():
    result = build_email_prompt(
        student_bio="Student",
        student_projects=None,
        student_interests=[],
        portfolio_url=None,
        github_url=None,
        resume_url="https://docs.google.com/my-resume",
        company_name="TestCo",
        company_summary="Building things",
        specific_projects=[],
        founder_name="Sam",
        founder_bio=None,
        tone="earnest",
    )
    assert "docs.google.com/my-resume" in result


def test_tone_changes_voice():
    base = dict(
        student_bio="Student",
        student_projects=None,
        student_interests=[],
        portfolio_url=None,
        github_url=None,
        resume_url=None,
        company_name="TestCo",
        company_summary="Test",
        specific_projects=[],
        founder_name="Sam",
        founder_bio=None,
    )
    curious = build_email_prompt(**base, tone="curious")
    scrappy = build_email_prompt(**base, tone="scrappy")
    assert "curious" in curious.lower()
    assert "Resourceful" in scrappy


def test_prompt_emphasizes_domain_alignment():
    result = build_email_prompt(
        student_bio="Student",
        student_projects="Built a trading bot",
        student_interests=["Fintech", "Payments"],
        portfolio_url=None,
        github_url=None,
        resume_url=None,
        company_name="PayCo",
        company_summary="Payment infrastructure for SMBs",
        specific_projects=[],
        founder_name="Jane",
        founder_bio=None,
        tone="curious",
    )
    # Prompt should emphasize interest alignment, not skill-gap filling
    assert "interest" in result.lower() or "into" in result.lower() or "domain" in result.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/email/test_prompt.py -v`
Expected: FAIL (new function signature)

- [ ] **Step 3: Rewrite prompt.py**

Replace `backend/email/prompt.py`:

```python
"""Prompt template for cold email generation.

Email angle: interest/domain alignment — "I'm into the same stuff
you're building" rather than "I can help with X."
"""

TONES = {
    "curious": {
        "label": "Curious",
        "voice": "Genuinely curious and a bit nerdy. You're interested in their problem and want to learn by helping. Humble but not timid.",
        "ask": 'End with a question about their work that opens a conversation (e.g. "I\'m curious how you handle X — could I take a look and share what I find?")',
    },
    "friendly": {
        "label": "Friendly",
        "voice": "Warm and personable. You come across as someone who would be fun to work with. Light touch, not overly casual.",
        "ask": 'End with a low-pressure suggestion (e.g. "Happy to hop on a quick call if you want to chat about it")',
    },
    "scrappy": {
        "label": "Scrappy",
        "voice": "Resourceful and action-oriented. You've already tried things, built things, figured things out on your own. You're not asking for permission — you're showing up with proof of work.",
        "ask": 'End by offering something concrete you\'ve already done or could do immediately (e.g. "I already prototyped X — want me to send it over?")',
    },
    "earnest": {
        "label": "Earnest",
        "voice": "Sincere and straightforward. You genuinely care about the problem they're solving and want to contribute meaningfully. No games, no tricks — just honest interest.",
        "ask": 'End with a simple, direct ask that shows commitment (e.g. "I\'d be glad to put in a few hours on X if that would be useful")',
    },
}

DEFAULT_TONE = "curious"


def build_email_prompt(
    student_bio: str,
    student_projects: str | None,
    student_interests: list[str],
    portfolio_url: str | None,
    github_url: str | None,
    resume_url: str | None,
    company_name: str,
    company_summary: str,
    specific_projects: list[str],
    founder_name: str,
    founder_bio: str | None = None,
    tone: str = DEFAULT_TONE,
) -> str:
    """Build a prompt for generating a cold email draft.

    Returns the full prompt string to send to an LLM.
    """
    tone_config = TONES.get(tone, TONES[DEFAULT_TONE])

    # Student context
    projects_section = ""
    if student_projects:
        projects_section = f"\nProjects: {student_projects}"

    interests_section = ""
    if student_interests:
        interests_section = f"\nDomain interests: {', '.join(student_interests)}"

    links_section = ""
    links = []
    if portfolio_url:
        links.append(f"Portfolio: {portfolio_url}")
    if github_url:
        links.append(f"GitHub: {github_url}")
    if resume_url:
        links.append(f"Resume: {resume_url}")
    if links:
        links_section = "\nLinks (include naturally if relevant, don't force all of them): " + " | ".join(links)

    # Founder context
    founder_bio_section = ""
    if founder_bio:
        founder_bio_section = f"\nFounder background: {founder_bio}"

    company_projects_section = ""
    if specific_projects:
        company_projects_section = "\nThey need help with: " + "; ".join(specific_projects)

    return f"""Write a cold email from a high school student to a startup founder.

VOICE: {tone_config["voice"]}

STRICT RULES:
- Open by establishing you're a high school student (this is your biggest pattern interrupt — founders don't get emails from high schoolers).
- Maximum 4-5 sentences. Shorter is better.
- Sound like a real student, not a professional.
- NO filler enthusiasm ("I'm really excited", "I'd love to", "I'm passionate about")
- NO compliments about the company ("I admire your work", "Your company is amazing")
- Show genuine interest in their DOMAIN — you care about the same problems they're solving
- If the student has built something relevant, reference it as proof of genuine interest (not as a credential)
- Include ONE specific hook showing you actually understand what they build
- {tone_config["ask"]}
- Do NOT use a formal sign-off. Just the student's first name.

STUDENT CONTEXT:
Bio: {student_bio}{projects_section}{interests_section}{links_section}

COMPANY CONTEXT:
Company: {company_name}
Founder: {founder_name}{founder_bio_section}
What they do: {company_summary}{company_projects_section}

Write the email body only. No subject line. No "Dear" or "Hi {founder_name}," — start directly with the hook."""
```

- [ ] **Step 4: Update email router to pass new fields**

In `backend/routers/email.py`, update the `generate_email` endpoint (line ~100):

```python
@router.post("/generate", response_model=EmailDraft)
def generate_email(body: EmailGenerate, user_id: str = Depends(get_current_user)):
    """Generate a cold email draft for a company."""
    db = get_db()

    company_result = db.table("companies").select("*").eq("id", body.company_id).execute()
    if not company_result.data:
        raise HTTPException(status_code=404, detail="Company not found")
    company = company_result.data[0]

    user_result = db.table("users").select(
        "interests, projects, bio, portfolio_url, github_url, resume_url, location"
    ).eq("id", user_id).execute()
    user = user_result.data[0] if user_result.data else {}

    draft = generate_draft(
        student_bio=user.get("bio") or "High school student",
        student_projects=user.get("projects"),
        student_interests=user.get("interests") or [],
        portfolio_url=user.get("portfolio_url"),
        github_url=user.get("github_url"),
        resume_url=user.get("resume_url"),
        company_name=company.get("name", ""),
        company_summary=company.get("summary") or company.get("description") or "",
        specific_projects=company.get("specific_projects") or [],
        founder_name=company.get("founder_name") or "the founder",
        founder_bio=company.get("founder_bio"),
        tone=body.tone,
    )

    return {
        "draft": draft,
        "tone": body.tone,
        "company_id": body.company_id,
        "company_name": company.get("name", ""),
        "founder_name": company.get("founder_name"),
    }
```

- [ ] **Step 5: Update generate_draft in generate.py to match new signature**

In `backend/email/generate.py`, update the `generate_draft` function to accept and pass through the new parameters. The function calls `build_email_prompt` — update the call to pass all new fields.

- [ ] **Step 6: Run all tests**

Run: `python -m pytest tests/email/ tests/api/test_email_router.py -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add backend/email/prompt.py backend/email/generate.py backend/routers/email.py tests/email/test_prompt.py
git commit -m "feat: rework email prompt for interest alignment with projects, founder_bio, URLs"
```

---

### Task 10: Run full backend test suite

- [ ] **Step 1: Run all tests**

```bash
python -m pytest tests/ -v --tb=short
```

- [ ] **Step 2: Fix any failures**

Address test failures one at a time. Common issues:
- Old tests referencing `skills` where endpoint now reads `interests`
- Mock data missing new required fields
- Import paths changed

- [ ] **Step 3: Commit fixes**

```bash
git add -A
git commit -m "fix: update tests for interest-based matching overhaul"
```

**PHASE 2 CHECKPOINT:** All backend tests pass. API serves new fields. Email prompt uses new context. Matching uses interest overlap. Search works by name. Report status.

---

## PHASE 3: FRONTEND OVERHAUL

---

### Task 11: Update frontend types and API

**Files:**
- Modify: `frontend/lib/types.ts`
- Modify: `frontend/lib/api.ts`
- Create: `frontend/lib/interests.ts`

- [ ] **Step 1: Update types.ts**

Add new fields to `CompanyCard`:

```typescript
export interface CompanyCard {
  // ... existing fields ...
  founder_email: string | null;
  email_confidence: string | null;
  has_email: boolean;
  yc_tags: string[];
  // keep existing: need_tags, capability_tags, match_score, rank_score
}
```

Add new fields to `CompanyBrief`:

```typescript
export interface CompanyBrief {
  // ... existing fields ...
  founder_bio: string | null;
  founder_email: string | null;
  email_confidence: string | null;
  has_email: boolean;
  yc_tags: string[];
}
```

Add new fields to `UserProfile`:

```typescript
export interface UserProfile {
  // ... existing fields ...
  interests: string[];
  projects: string | null;
  resume_url: string | null;
}
```

- [ ] **Step 2: Add fetchInterests to api.ts**

```typescript
export interface InterestCategory {
  name: string;
  tags: string[];
}

export async function fetchInterests(): Promise<InterestCategory[]> {
  const res = await apiFetch("/interests");
  const data = await res.json();
  return data.categories;
}
```

Also update `fetchCompanies` to accept a `search` parameter:

```typescript
export async function fetchCompanies(
  page = 1,
  limit = 50,
  industry?: string,
  reachability?: string,
  search?: string,
): Promise<CompanyCard[]> {
  const params = new URLSearchParams({ page: String(page), limit: String(limit) });
  if (industry) params.set("industry", industry);
  if (reachability) params.set("reachability", reachability);
  if (search) params.set("search", search);
  const res = await apiFetch(`/companies?${params}`);
  return res.json();
}
```

- [ ] **Step 3: Create interests.ts**

```typescript
/** Interest tag labels — maps curated tag keys to display names.
 * Since curated tags are already human-readable (e.g., "Generative AI"),
 * this is mostly a pass-through, but provides a place for any overrides.
 */
export function interestLabel(tag: string): string {
  return tag;
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/types.ts frontend/lib/api.ts frontend/lib/interests.ts
git commit -m "feat: update frontend types and API for interest matching"
```

---

### Task 12: Build InterestPicker component

**Files:**
- Create: `frontend/components/InterestPicker.tsx`

- [ ] **Step 1: Create InterestPicker.tsx**

Build a category-expandable interest picker:
- Fetches categories from `GET /interests`
- Displays ~8-10 category cards in a grid
- Clicking a category expands it to show its specific tags
- User picks up to 2 specific tags (not categories)
- Selected tags are highlighted
- Calls `onChange(selectedTags: string[])` when selection changes

```typescript
"use client";

import { useEffect, useState } from "react";
import { fetchInterests, InterestCategory } from "@/lib/api";

interface InterestPickerProps {
  selected: string[];
  onChange: (interests: string[]) => void;
  maxSelections?: number;
}

export default function InterestPicker({
  selected,
  onChange,
  maxSelections = 2,
}: InterestPickerProps) {
  const [categories, setCategories] = useState<InterestCategory[]>([]);
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);

  useEffect(() => {
    fetchInterests().then(setCategories).catch(() => {});
  }, []);

  function toggleTag(tag: string) {
    if (selected.includes(tag)) {
      onChange(selected.filter((t) => t !== tag));
    } else if (selected.length < maxSelections) {
      onChange([...selected, tag]);
    }
  }

  function toggleCategory(name: string) {
    setExpandedCategory(expandedCategory === name ? null : name);
  }

  // Check if a category has any selected tags
  function categoryHasSelection(cat: InterestCategory): boolean {
    return cat.tags.some((t) => selected.includes(t));
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-neutral-500">
        Pick up to {maxSelections} domains that excite you
      </p>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {categories.map((cat) => (
          <div key={cat.name}>
            <button
              onClick={() => toggleCategory(cat.name)}
              className={`w-full rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                expandedCategory === cat.name
                  ? "border-teal-500 bg-teal-50 text-teal-800"
                  : categoryHasSelection(cat)
                    ? "border-teal-300 bg-teal-50/50"
                    : "border-neutral-200 hover:border-neutral-300"
              }`}
            >
              {cat.name}
              {categoryHasSelection(cat) && (
                <span className="ml-1 text-teal-600">
                  ({cat.tags.filter((t) => selected.includes(t)).length})
                </span>
              )}
            </button>
            {expandedCategory === cat.name && (
              <div className="mt-1 flex flex-wrap gap-1 pl-1">
                {cat.tags.map((tag) => (
                  <button
                    key={tag}
                    onClick={() => toggleTag(tag)}
                    disabled={
                      !selected.includes(tag) && selected.length >= maxSelections
                    }
                    className={`rounded-full px-2.5 py-1 text-xs transition-colors ${
                      selected.includes(tag)
                        ? "bg-teal-600 text-white"
                        : selected.length >= maxSelections
                          ? "bg-neutral-100 text-neutral-400 cursor-not-allowed"
                          : "bg-neutral-100 text-neutral-700 hover:bg-neutral-200"
                    }`}
                  >
                    {tag}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      {selected.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {selected.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center gap-1 rounded-full bg-teal-100 px-2.5 py-1 text-xs text-teal-800"
            >
              {tag}
              <button
                onClick={() => onChange(selected.filter((t) => t !== tag))}
                className="ml-0.5 text-teal-600 hover:text-teal-900"
              >
                x
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/InterestPicker.tsx
git commit -m "feat: add InterestPicker component with expandable categories"
```

---

### Task 13: Update onboarding and profile pages

**Files:**
- Modify: `frontend/app/onboard/page.tsx`
- Modify: `frontend/app/profile/page.tsx`

- [ ] **Step 1: Update onboarding to use InterestPicker**

In `frontend/app/onboard/page.tsx`:
- Replace `import CapabilityPicker` with `import InterestPicker from "@/components/InterestPicker"`
- Replace the CapabilityPicker usage with InterestPicker
- Change the label from skill-related to "What domains excite you?"
- Save selected interests to `interests` field via `updateProfile({ interests: [...] })`

- [ ] **Step 2: Update profile page**

In `frontend/app/profile/page.tsx`:
- Replace CapabilityPicker with InterestPicker
- Add `projects` textarea field with placeholder: "Briefly describe something you've built or worked on (e.g., 'Built a trading bot in Python that tracks crypto prices')"
- Add `resume_url` text input with placeholder: "Link to your resume (Google Doc, Dropbox, etc.)"
- Ensure `portfolio_url` and `github_url` fields are visible (they already exist but verify they're rendered)
- Wire all new fields into the `updateProfile` save handler

- [ ] **Step 3: Commit**

```bash
git add frontend/app/onboard/page.tsx frontend/app/profile/page.tsx
git commit -m "feat: swap CapabilityPicker for InterestPicker on onboard and profile"
```

---

### Task 14: Update feed page and FounderCard

**Files:**
- Modify: `frontend/app/feed/page.tsx`
- Modify: `frontend/components/FounderCard.tsx`

- [ ] **Step 1: Update FounderCard to show YC tags + email badge**

In `frontend/components/FounderCard.tsx`:
- Replace `capability_tags` / `need_tags` display with `yc_tags`
- Add a small email availability indicator: a mail icon (or text) if `email_confidence` is "high" or "medium", greyed out otherwise
- Remove the `TIER2_LABELS` import — YC tags are already human-readable

- [ ] **Step 2: Update feed page to use backend search**

In `frontend/app/feed/page.tsx`:
- Pass the `search` query param to `fetchCompanies()` instead of doing client-side filtering
- Remove client-side name/founder filtering logic (the backend handles it now)
- Keep client-side tag/industry filtering if it supplements backend filters

- [ ] **Step 3: Commit**

```bash
git add frontend/app/feed/page.tsx frontend/components/FounderCard.tsx
git commit -m "feat: show YC tags and email badge on feed cards, add server-side search"
```

---

### Task 15: Update brief page and FounderBrief

**Files:**
- Modify: `frontend/components/FounderBrief.tsx`
- Modify: `frontend/app/founder/[id]/page.tsx`

- [ ] **Step 1: Update FounderBrief**

In `frontend/components/FounderBrief.tsx`:
- Add `founder_bio` display — a prominent section above or below the company summary, showing the founder's own words. Use a distinct visual treatment (e.g., slightly different background, quote-style formatting)
- Replace `capability_tags` / `need_tags` display with `yc_tags`
- Add interest overlap indicator: compare user's interests with company's `yc_tags` and show matches (e.g., "You're both into Generative AI")
- Show email availability status clearly
- Change reachability label from "HIGH" to "HIGH REACHABILITY" (etc.)

- [ ] **Step 2: Update founder page**

In `frontend/app/founder/[id]/page.tsx`:
- Ensure the user's profile (including `interests`) is fetched so FounderBrief can compute overlap
- Pass user interests to FounderBrief or compute overlap in the page

- [ ] **Step 3: Commit**

```bash
git add frontend/components/FounderBrief.tsx frontend/app/founder/[id]/page.tsx
git commit -m "feat: show founder_bio, YC tags, interest overlap, and email status on brief"
```

---

### Task 16: Update EmailWorkspace

**Files:**
- Modify: `frontend/components/EmailWorkspace.tsx`

- [ ] **Step 1: Add recipient email handling**

In `frontend/components/EmailWorkspace.tsx`:
- If `founder_email` exists and `email_confidence` is "high": pre-fill the recipient field, show the email
- If `email_confidence` is "medium": pre-fill but show a subtle note: "This email was auto-detected — verify before sending"
- If no email: show "Email not available — reach out via LinkedIn" with the `founder_linkedin` link
- The "Send via Gmail" button should be disabled when there's no founder email

- [ ] **Step 2: Commit**

```bash
git add frontend/components/EmailWorkspace.tsx
git commit -m "feat: pre-fill recipient email with confidence indicator and LinkedIn fallback"
```

---

### Task 17: Delete dead code

**Files:**
- Delete: `frontend/components/SkillPicker.tsx`
- Delete: `frontend/lib/skills.ts`
- Delete: `backend/ml/` (entire directory)
- Delete: `backend/email/generate_test_batch.py`
- Delete: `tests/ml/` (entire directory)

- [ ] **Step 1: Verify nothing imports the files being deleted**

```bash
# Frontend
grep -r "SkillPicker" frontend/ --include="*.tsx" --include="*.ts"
grep -r "skills" frontend/lib/ --include="*.ts" | grep -v "node_modules" | grep import

# Backend
grep -r "from backend.ml" backend/ --include="*.py" | grep -v "backend/ml/"
grep -r "generate_test_batch" backend/ --include="*.py"
```

Expected: No imports found (SkillPicker is unused, ML is not imported by runtime code).

- [ ] **Step 2: Delete the files**

```bash
rm frontend/components/SkillPicker.tsx
rm frontend/lib/skills.ts
rm -rf backend/ml/
rm -rf tests/ml/
rm backend/email/generate_test_batch.py
```

- [ ] **Step 3: Run all tests to confirm nothing breaks**

```bash
python -m pytest tests/ -v --tb=short
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove dead code (SkillPicker, skills.ts, ML module, test batch script)"
```

---

### Task 18: Quick fixes from jared_ques.txt

- [ ] **Step 1: Fix Navbar REACH link**

In `frontend/components/Navbar.tsx`, change the REACH logo link to always go to `/`:

```tsx
<Link href="/" className="font-display text-xl">
  REACH
</Link>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/Navbar.tsx
git commit -m "fix: REACH navbar button always links to homepage"
```

---

### Task 19: Final verification

- [ ] **Step 1: Run full backend test suite**

```bash
python -m pytest tests/ -v --tb=short
```

Expected: All pass (minus deleted ML tests)

- [ ] **Step 2: Run frontend dev server**

```bash
cd frontend && npm run dev
```

Manual verification checklist:
- [ ] Landing page loads, search works
- [ ] Onboarding shows InterestPicker with expandable categories
- [ ] Profile page shows interests, projects textarea, resume_url, portfolio_url, github_url
- [ ] Feed shows YC tags on cards, email badge visible
- [ ] Founder brief shows founder_bio, YC tags, interest overlap, reachability label
- [ ] EmailWorkspace shows pre-filled email (if available) or LinkedIn fallback
- [ ] REACH navbar button goes to homepage

- [ ] **Step 3: Commit any final fixes**

```bash
git add -A
git commit -m "fix: final adjustments from manual testing"
```
