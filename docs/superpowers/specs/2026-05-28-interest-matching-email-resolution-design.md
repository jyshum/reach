# REACH Overhaul: Interest-Based Matching + Email Resolution

*Design spec — May 28, 2026*
*Sequential execution, single CLI agent, pipeline-first discovery*

---

## Problem Statement

Two product-breaking issues:

1. **Skill tags are useless for discovery.** The 20-tag capability vocabulary produces identical tags across all 1,519 companies. Users scroll endlessly with no differentiation. The fundamental issue: the system asks "what can this startup use?" when it should ask "what is this startup about?"

2. **No founder email addresses.** The entire email pipeline (generate, send, track) exists but has no recipient address. The `founder_email` column exists in the DB but is never populated.

---

## Core Reframe

The old model: **skill-gap filling** ("I can help you with frontend development")

The new model: **interest/domain alignment** ("I'm into the same stuff you're building")

A YC founder responds to a high schooler not because they fill a skill gap, but because the student shows genuine interest and relevant experience in their domain.

This reframe cascades through every layer: onboarding, matching, feed display, briefs, email generation.

---

## Phase 1: Pipeline Discovery (run first, informs everything else)

Pipeline runs offline on dev machine. Purpose: populate the DB with new data and discover what we're actually working with before making API/frontend decisions.

### 1A: Re-scrape Founders

**File:** `backend/pipeline/scrape_founders.py` (modify existing)

Extract two new fields from YC company pages:
- `founder_bio` (string) — founder's self-written biographical paragraph
- `has_email` (boolean) — whether YC has an email on file

These fields exist in the embedded JSON on every YC company page alongside the fields we already extract (name, title, avatar, linkedin, twitter).

**Output:** Updated `data/founders.json` with new fields.

**Discovery questions this answers:**
- What % of founders have a bio? (expect high based on 4/4 sample)
- What's the average bio length? Are any empty strings vs null?
- What % have `has_email: true`?

### 1B: Curate YC Tags

**File:** `backend/pipeline/curate_tags.py` (new script)

The raw YC data has 232 unique tags across 1,519 companies. Many are duplicates or too broad.

Steps:
1. Load all tags from `data/raw_companies.json`
2. Collapse obvious duplicates ("AI" + "Artificial Intelligence" + "Machine Learning" -> "AI / Machine Learning")
3. Remove tags that appear on 300+ companies (too broad to differentiate — e.g., "B2B" at 351)
4. Remove tags that appear on fewer than 5 companies (too niche to be useful as a filter)
5. Group remaining tags into ~8-10 visual categories for the interest picker
6. Output a mapping file: `data/curated_tags.json`

**Output format:**
```json
{
  "categories": [
    {
      "name": "AI / Machine Learning",
      "tags": ["Generative AI", "Computer Vision", "NLP", "ML Infrastructure", "AI Assistant", "Conversational AI"]
    },
    {
      "name": "Developer Tools",
      "tags": ["Infrastructure", "Open Source", "API", "DevOps"]
    }
  ],
  "tag_to_category": {
    "Generative AI": "AI / Machine Learning",
    "Open Source": "Developer Tools"
  },
  "removed_tags": {
    "too_broad": ["B2B", "SaaS", "AI", "Artificial Intelligence"],
    "too_niche": ["..."],
    "collapsed_into": {"Machine Learning": "AI / Machine Learning", "AI": "AI / Machine Learning"}
  }
}
```

**Discovery questions this answers:**
- How many curated tags do we end up with after collapsing and filtering?
- How many categories? Do they feel natural?
- What's the distribution — are results actually differentiated now?
- How many tags does the average company have after curation? (if still 5+, might need tighter filtering)

### 1C: Email Resolution Cascade

**File:** `backend/pipeline/resolve_emails.py` (new script)

Runs only on founders where `has_email` is true (from step 1A). Writes results to `data/resolved_emails.json`.

**Cascade order (each step only runs on founders not yet resolved):**

**Step 1: Website scrape**
- For each company with a `website` URL, fetch the homepage + `/contact`, `/about`, `/team` pages
- Parse for email addresses: `mailto:` links, text matching `*@{company_domain}`
- Filter out generic addresses (info@, hello@, support@, sales@)
- If a personal email matching the founder's name pattern is found, mark as `source: "website"`, `confidence: "high"`

**Step 2: GitHub discovery**
- Extract GitHub usernames from founder LinkedIn bios or company website (look for github.com links)
- If found, hit GitHub API (`GET /users/{username}`) for public email field
- If no public email, check the company's GitHub org for public repos, scan recent commit authors for emails matching the company domain
- Mark as `source: "github"`, `confidence: "high"`

**Step 3: Pattern guess + verification**
- Generate candidate emails from founder name + company domain:
  - `first@domain.com`
  - `firstname@domain.com`
  - `first.last@domain.com`
  - `firstlast@domain.com`
- Check domain MX records first (skip if no MX = domain doesn't receive email)
- SMTP mailbox verification on candidates (connect to MX server, RCPT TO, don't send)
- Mark verified as `source: "pattern"`, `confidence: "medium"`
- Mark MX-valid but SMTP-unverified as `source: "pattern"`, `confidence: "low"` — DO NOT surface these to users

**Step 4 (optional, manual):** API lookup via Hunter.io/Apollo free tier for high-value remaining founders.

**Output format per founder:**
```json
{
  "company_name": "Pando Bioscience",
  "founder_email": "will@pando.bio",
  "email_source": "website",
  "email_confidence": "high"
}
```

**Discovery questions this answers:**
- What % of emails can we resolve via website scraping alone?
- How many companies block web crawlers?
- What % of founders have GitHub profiles discoverable from their YC/LinkedIn data?
- Does SMTP verification actually work on most YC startup mail servers, or do they block it?
- What's the final coverage: how many founders have a usable (high/medium confidence) email?

### 1D: Write to Supabase

**File:** `backend/pipeline/supabase_write.py` (modify existing)

After all discovery steps, merge everything and upsert:
- `founder_bio` — text, nullable
- `has_email` — boolean
- `founder_email` — text, nullable
- `email_source` — text, nullable ("website", "github", "pattern", "api")
- `email_confidence` — text, nullable ("high", "medium")
- `yc_tags` — text[], the company's curated tags (mapped from raw tags via curated_tags.json)

**DB schema changes (new columns on companies table):**
```sql
ALTER TABLE companies ADD COLUMN IF NOT EXISTS founder_bio text;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS has_email boolean DEFAULT false;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS email_source text;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS email_confidence text;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS yc_tags text[] DEFAULT '{}';
```

### Phase 1 Checkpoint

**STOP after Phase 1.** Review actual data before proceeding:
- Print coverage stats: bio %, email resolution %, tag distribution
- Review curated tag categories — do they feel right?
- Decide which confidence levels to surface in the UI
- Lock the API contract based on real data, not assumptions

---

## Phase 2: Backend API Changes (after Phase 1 data review)

### 2A: Interest Vocabulary

**File:** `backend/interests.py` (new, replaces `capabilities.py` at runtime)

Load curated tag vocabulary from Phase 1 output. Expose:
- List of categories + tags for the frontend picker
- Mapping function: raw YC tag -> curated tag

### 2B: User Schema Changes

**File:** `backend/schemas.py`

New/modified fields on UserProfile and UserUpdate:
- `interests: list[str]` — curated tag keys, max 2 (replaces `skills` for matching)
- `projects: str | None` — free-text, one textarea ("what have you built?")
- `resume_url: str | None` — link to external resume (Google Doc, PDF, etc.)

Existing fields kept: `bio`, `github_url`, `portfolio_url`, `skills` (deprecated, kept for backwards compat)

**DB migration:**
```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS interests text[] DEFAULT '{}';
ALTER TABLE users ADD COLUMN IF NOT EXISTS projects text;
ALTER TABLE users ADD COLUMN IF NOT EXISTS resume_url text;
```

### 2C: Matching Rework

**File:** `backend/matching/scorer.py` (rewrite)

New matching logic:
- `match_score` = count of overlapping curated tags between user's `interests` and company's `yc_tags`
- Sort order: match_score descending, then reachability_probability descending
- No weighted formula. No black box. Matches first, reachability as tiebreaker.
- Companies with zero overlap still returned, ranked below matches

### 2D: Companies Endpoint

**File:** `backend/routers/companies.py`

Changes:
- Add `search` query param — Supabase `ilike` on `name` and `founder_name`
- Response includes new fields: `yc_tags`, `founder_bio`, `founder_email`, `email_confidence`, `has_email`
- Matching uses interests instead of capabilities

### 2E: Email Prompt Rework

**File:** `backend/email/prompt.py`

The prompt now receives:
- `student_projects` — free-text project descriptions
- `student_interests` — domain interests (for context/angle)
- `student_bio` — if provided
- `portfolio_url`, `github_url`, `resume_url` — included as optional links in the email
- `founder_bio` — for referencing something specific about the founder
- `founder_name`, `company_name`, `company_summary`, `specific_projects` — already wired

Email angle shifts to: "I'm into the same space you're building in, here's proof" rather than "I can help with X."

### 2F: Interest Endpoint

**File:** `backend/routers/users.py` or new router

New endpoint: `GET /interests` — returns the curated tag vocabulary (categories + tags) for the frontend picker to consume.

### 2G: Tests

Update/add tests for:
- New matching logic (interest overlap sorting)
- Companies search param
- Updated email prompt
- User schema with new fields
- Interest endpoint

---

## Phase 3: Frontend Overhaul (after Phase 2 API is working)

### 3A: InterestPicker Component

**File:** `frontend/components/InterestPicker.tsx` (new, replaces CapabilityPicker)

- Fetches categories + tags from `GET /interests`
- 8-10 visual category cards that expand to show specific tags
- Max 2 specific tag selections (not categories — categories are just visual grouping)
- Example: student opens "AI / Machine Learning" category, picks "Generative AI". Opens "Healthcare", picks "Drug Discovery". Done — 2 picks, 2 different domains.
- Used on onboarding + profile pages

### 3B: Onboarding Page

**File:** `frontend/app/onboard/page.tsx`

- Swap CapabilityPicker for InterestPicker
- Question changes from "What can you do?" to "What domains excite you?"

### 3C: Profile Page

**File:** `frontend/app/profile/page.tsx`

- Replace CapabilityPicker with InterestPicker
- Add projects textarea: "Briefly describe something you've built or worked on"
- Add resume_url field: "Link to your resume (Google Doc, PDF, etc.)"
- Keep portfolio_url and github_url (already exist)
- Keep bio (already exists)

### 3D: Feed Page + FounderCard

**Files:** `frontend/app/feed/page.tsx`, `frontend/components/FounderCard.tsx`

- Cards show curated YC tags instead of capability tags
- Small email availability indicator on each card (e.g., mail icon if `email_confidence` is high/medium, greyed out if null)
- Search bar now hits backend search (company name + founder name)

### 3E: Brief Page + FounderBrief

**Files:** `frontend/app/founder/[id]/page.tsx`, `frontend/components/FounderBrief.tsx`

- Display `founder_bio` prominently — the founder's own words
- Show curated YC tags
- Show interest overlap: "You're both into Computer Vision"
- Show email availability status
- Reachability label: "HIGH REACHABILITY" instead of "HIGH"

### 3F: EmailWorkspace

**File:** `frontend/components/EmailWorkspace.tsx`

- Recipient email field pre-filled from `founder_email` (if available)
- If no email: show "Email not available — reach out via LinkedIn" with LinkedIn link
- If medium confidence: show subtle note "This email was auto-detected — verify before sending"

### 3G: Type Updates

**File:** `frontend/lib/types.ts`

Add to CompanyCard/CompanyBrief:
- `yc_tags: string[]`
- `founder_bio: string | null`
- `founder_email: string | null`
- `email_confidence: "high" | "medium" | null`
- `has_email: boolean`

Add to UserProfile:
- `interests: string[]`
- `projects: string | null`
- `resume_url: string | null`

### 3H: Cleanup

Delete dead code:
- `frontend/components/SkillPicker.tsx`
- `frontend/lib/skills.ts` (96KB)
- `backend/ml/` directory (deprecated XGBoost)
- `backend/email/generate_test_batch.py`

Deprecate (keep but stop using):
- `frontend/lib/capabilities.ts` — replaced by interests fetched from API
- `frontend/components/CapabilityPicker.tsx` — replaced by InterestPicker

---

## Independent Quick Fixes (can be done anytime)

These are not part of the overhaul but were flagged in `jared_ques.txt`:

1. **Navbar REACH button** — change link from `/feed` to `/` for authenticated users (one line in `Navbar.tsx`)
2. **Loading performance** — add debounce to landing page search, add loading skeletons
3. **Wire portfolio_url + github_url into email prompt** — already in schema, just not passed to `build_email_prompt()`

---

## What This Spec Does NOT Decide (deferred to Phase 1 data review)

- Exact curated tag list (depends on Phase 1B output)
- Exact number of curated categories (depends on what collapses cleanly)
- Email confidence thresholds for display (depends on Phase 1C resolution rates)
- Whether to show medium-confidence emails or only high (depends on false positive rate)
- Whether `skills` column is dropped or kept alongside `interests` (depends on migration complexity)
- API response shapes for new fields (locked after Phase 1 checkpoint)

---

## Success Criteria

1. A student opens the feed and immediately sees differentiated cards — each startup feels distinct based on its domain tags
2. A student picks 2 interests during onboarding and gets a feed of relevant startups, not everything
3. The brief page shows who the founder actually is (their bio, their story)
4. At least 50% of founders have a resolved email address the student can send to directly
5. The email generated references the student's actual projects and the founder's actual background
6. No student sends an email to a wrong address — only high/medium confidence emails are surfaced
