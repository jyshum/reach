# Design: `backend/pipeline/scrape_yc.py`
*Date: 2026-05-17*

---

## Goal

Scrape the YC company directory for the last 4 batches (W23, S23, W24, S24) and write raw company records to `data/raw_companies.json`. This is Step 1 of the offline data pipeline. No LLM, no filtering — just get the data.

---

## Approach

YC's public directory (ycombinator.com/companies) is powered by Algolia. The app ID and search API key are exposed in browser network requests — this is the intended public read interface. No HTML scraping, no headless browser, no rate-limit evasion.

**Algolia credentials (public, read-only):**
- App ID: `45BWZJ1SGC`
- Search API key: `be7591b7e2cc2a51d92e5ec0a1498399`
- Index: `YCCompany_production`

---

## Behavior

1. For each target batch (`W23`, `S23`, `W24`, `S24`), send a filtered Algolia search query.
2. Paginate through all results if needed (each batch ~150–200 companies, well under Algolia's 1000-hit limit — typically one page).
3. Extract the relevant fields from each Algolia hit.
4. Merge all batches into a single list and deduplicate by company name.
5. Write the result to `data/raw_companies.json` as a JSON array.
6. Print total count of records written.

---

## Field Mapping

| Output field  | Algolia field  | Notes                        |
|---------------|----------------|------------------------------|
| `name`        | `name`         | Company name                 |
| `description` | `one_liner`    | Short company description    |
| `batch`       | `batch`        | e.g. "W23"                   |
| `tags`        | `tags`         | List of strings              |
| `website`     | `website`      | Company URL                  |

---

## Output

**File:** `data/raw_companies.json`

**Format:** JSON array of flat dicts.

```json
[
  {
    "name": "Acme Corp",
    "description": "AI for supply chains.",
    "batch": "W24",
    "tags": ["B2B", "Supply Chain", "AI"],
    "website": "https://acmecorp.com"
  }
]
```

---

## Error Handling

- If a single batch query fails (network error, bad response), log the error and continue with remaining batches.
- Report total count of successfully fetched records at the end.
- If `data/` directory doesn't exist, create it before writing.

---

## Dependencies

- `requests` only. No external scraping libraries.
- Runnable standalone: `python backend/pipeline/scrape_yc.py`

---

## What This Is Not

- Not a live API called during user sessions.
- Not responsible for filtering dead companies (that's `activity_filter.py`).
- Not responsible for enrichment or LLM processing (that's `enrich.py`).

---

## Next Pipeline Step

Output feeds into `backend/pipeline/activity_filter.py`, which reads `data/raw_companies.json` and pings each company's website to check if it's still active.
