# Founder Enrichment Pipeline — Design Spec

*2026-05-24*

---

## Overview

Add founder-level data (name, title, headshot, LinkedIn, email placeholder) and company logos to the REACH pipeline. Offline pipeline steps that run on the dev machine, same as existing scrape/enrich/score steps. No frontend changes — data lands in Supabase ready for future UI work.

---

## Data Sources

**Algolia API (already used by scrape_yc.py):**
- `slug` — company URL slug on YC (e.g. "pando-bioscience")
- `small_logo_thumb_url` — company logo hosted on bookface-images S3

**YC Company Pages (`ycombinator.com/companies/{slug}`):**
- Founder data embedded as HTML-entity-encoded JSON in page HTML
- Each founder object contains: `full_name`, `title`, `founder_bio`, `avatar_thumb_url`, `linkedin_url`, `twitter_url`, `has_email`, `is_active`
- Avatar URLs work without AWS query signatures (base URL is publicly accessible)
- First active founder used as primary founder per company

---

## Pipeline Changes

### Step 1: Update scrape_yc.py

Add two fields to `extract_company()`:
- `slug` — from `hit.get("slug", "")`
- `small_logo_thumb_url` — from `hit.get("small_logo_thumb_url", "")`

Re-run scraper to regenerate `data/raw_companies.json` with new fields. Existing fields unchanged.

### Step 2: New scrape_founders.py

New pipeline step: `backend/pipeline/scrape_founders.py`

**Input:** `data/raw_companies.json` (needs `name` and `slug` fields)

**Process:**
1. For each company with a non-empty slug, fetch `https://www.ycombinator.com/companies/{slug}`
2. Parse HTML to find the HTML-entity-encoded JSON blob containing founder data
3. Extract the first active founder's: `full_name`, `title`, `avatar_thumb_url` (strip AWS signature query params), `linkedin_url`, `twitter_url`
4. Rate limit: 1 request per second (sleep between requests)
5. Log progress every 50 companies
6. Handle errors gracefully: if a page 404s or has no founders, store nulls and continue

**Output:** `data/founders.json` — array of objects:
```json
{
  "company_name": "Pando Bioscience",
  "founder_name": "Will Cao",
  "founder_title": "Founder",
  "founder_avatar_url": "https://bookface-images.s3.us-west-2.amazonaws.com/avatars/xxx.jpg",
  "founder_linkedin": "https://www.linkedin.com/in/willcao/",
  "founder_twitter": "https://twitter.com/cao_will"
}
```

Companies with no founders found get null values for all founder fields.

**Runtime:** ~25 minutes for 1519 companies at 1 req/sec.

**Resume support:** If `data/founders.json` already exists, load it, skip companies already scraped, append new results. This avoids re-scraping on interruption.

### Step 3: Update supabase_write.py

Merge founder data from `data/founders.json` into the company upsert. Also include `slug` and `small_logo_thumb_url` from raw_companies.

New fields in upsert payload:
- `slug` (from raw_companies)
- `small_logo_url` (from raw_companies `small_logo_thumb_url`)
- `founder_name` (from founders.json)
- `founder_title` (from founders.json)
- `founder_avatar_url` (from founders.json)
- `founder_linkedin` (from founders.json)
- `founder_twitter` (from founders.json)
- `founder_email` (null — placeholder for future email resolution)

---

## Schema Migration

Add new columns to the `companies` table. Existing columns `founder_name`, `founder_title`, `founder_linkedin`, `founder_twitter` already exist in the schema but are unpopulated.

**New columns to add (via SQL in Supabase SQL Editor):**
```sql
ALTER TABLE companies ADD COLUMN IF NOT EXISTS slug text;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS small_logo_url text;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS founder_avatar_url text;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS founder_email text;
```

**Update schema.sql** to include these columns for documentation (the actual migration runs via SQL Editor, schema.sql is the reference doc).

---

## Updated Pipeline Order

```
scrape_yc → scrape_founders → ml_predict → enrich (LLM) → normalize_tags → supabase_write
```

`scrape_founders` runs after `scrape_yc` (needs slugs) and before `supabase_write` (provides founder data for upsert). It's independent of ML and LLM enrichment steps.

---

## Files

| Action | File | Responsibility |
|---|---|---|
| Modify | `backend/pipeline/scrape_yc.py` | Add slug + small_logo_thumb_url extraction |
| Create | `backend/pipeline/scrape_founders.py` | Scrape YC company pages for founder data |
| Modify | `backend/pipeline/supabase_write.py` | Include founder + logo fields in upsert |
| Modify | `backend/db/schema.sql` | Add new columns (reference doc) |
| Modify | `backend/schemas.py` | Add new fields to response schemas |

---

## What This Spec Does NOT Cover

- Frontend display of founder data (deferred to visual overhaul)
- Founder email resolution (future pipeline step, schema ready)
- Multiple founders per company (only primary/first active founder stored)
- Downloading/re-hosting images (direct link to bookface S3, publicly accessible)
- Founder bio storage (available in scraped data but not stored — not needed for MVP)
