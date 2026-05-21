# Backend API + Auth — Design Spec

*Date: 2026-05-21*

---

## Overview

FastAPI server deployed on Railway (~$5/mo) that sits between the Next.js frontend and Supabase database. Handles auth verification, company browsing with match-based ranking, brief access gating, outreach tracking, and user profile management.

## Architecture

```
Frontend (Next.js/Vercel)
  ├── Supabase Auth (signup/login directly)
  └── FastAPI (all data requests, JWT in header)
        └── Supabase (Postgres database)
```

- Supabase Auth handles signup/login — frontend calls Supabase directly
- FastAPI verifies JWTs using Supabase's JWT secret (no network call needed per request)
- FastAPI queries Supabase as a Postgres database via supabase-py client
- User profile auto-created on first API call after signup

## Auth Flow

### Signup
1. Frontend calls `supabase.auth.signUp(email, password)` directly
2. Supabase hashes password, creates auth user, returns JWT
3. Frontend stores JWT, calls `GET /me` with `Authorization: Bearer <jwt>`
4. FastAPI sees unknown user ID → creates bare profile (tier=free, skills=empty)
5. Frontend redirects to onboarding

### Login
1. Frontend calls `supabase.auth.signInWithPassword(email, password)`
2. Supabase verifies, returns JWT
3. Frontend calls `GET /me` → gets existing profile

### Request Authentication
1. Every request includes `Authorization: Bearer <jwt>` header
2. FastAPI middleware decodes JWT, verifies signature with Supabase JWT secret
3. Valid → extracts user ID, attaches to request
4. Invalid/expired → returns 401

### Brief Limit Enforcement
1. On `GET /companies/{id}`, check user tier
2. If `free` → count rows in `brief_views` for this user
3. If count >= 3 and this company not already viewed → return 403
4. Otherwise → insert into `brief_views`, return brief data

## Database Schema

### `users`

Created on first API call after Supabase Auth signup.

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | PK, matches Supabase Auth user ID |
| `email` | text | From JWT |
| `school` | text | Nullable |
| `grad_year` | int | Nullable |
| `skills` | text[] | Canonical skill tags from vocabulary |
| `bio` | text | Nullable |
| `github_url` | text | Nullable |
| `portfolio_url` | text | Nullable |
| `tier` | text | `free`, `unlocked`, `paid`. Default `free` |
| `created_at` | timestamptz | Auto-set |
| `updated_at` | timestamptz | Auto-updated |

### `companies`

Populated by pipeline's `supabase_write` step.

| Column | Type | Notes |
|---|---|---|
| `id` | serial | PK |
| `name` | text | Unique |
| `yc_batch` | text | e.g., "Winter 2024" |
| `description` | text | Raw one-liner from YC |
| `long_description` | text | Full description |
| `summary` | text | LLM-generated 2-sentence summary |
| `one_liner` | text | LLM-generated short form |
| `website` | text | |
| `industry` | text | From canonical list |
| `stage` | text | Raw stage from YC |
| `stage_detail` | text | building-mvp/launched/growing/scaling |
| `technical_level` | text | technical/mixed/non-technical |
| `team_size` | int | Nullable |
| `need_tags` | text[] | Canonical skill tags |
| `specific_projects` | text[] | 2 project suggestions |
| `is_hiring` | boolean | |
| `status` | text | Active/Inactive/Acquired |
| `reachability_score` | text | high/medium/low |
| `reachability_probability` | float | 0.0-1.0 |
| `founder_name` | text | Nullable |
| `founder_title` | text | Nullable |
| `founder_linkedin` | text | Nullable |
| `founder_twitter` | text | Nullable |
| `all_locations` | text | |
| `tags` | text[] | Raw YC tags |
| `industries` | text[] | Raw YC industries |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |

### `brief_views`

Tracks which briefs a user has viewed (enforces free tier limit).

| Column | Type | Notes |
|---|---|---|
| `id` | serial | PK |
| `user_id` | uuid | FK → users |
| `company_id` | int | FK → companies |
| `viewed_at` | timestamptz | Auto-set |
| | unique | (user_id, company_id) — one record per pair |

### `outreach_log`

Tracks emails sent and their outcomes.

| Column | Type | Notes |
|---|---|---|
| `id` | serial | PK |
| `user_id` | uuid | FK → users |
| `company_id` | int | FK → companies |
| `status` | text | sent/replied/meeting/no-response |
| `sent_at` | timestamptz | Nullable |
| `followup_date` | timestamptz | Auto-computed: sent_at + 5 days |
| `notes` | text | Nullable |
| `created_at` | timestamptz | |

## API Endpoints

### Auth/Profile

| Method | Path | Description | Auth |
|---|---|---|---|
| `GET` | `/me` | Get current user profile (auto-creates if first call) | Yes |
| `PUT` | `/me` | Update profile (skills, bio, school, grad_year, github_url, portfolio_url) | Yes |

### Companies

| Method | Path | Description | Auth |
|---|---|---|---|
| `GET` | `/companies` | Browse company cards. Query params: `industry`, `reachability`, `page`, `limit`. Sorted by match score if logged in, reachability if anonymous. | Optional |
| `GET` | `/companies/{id}` | Get full brief. Gated by tier (free = 3 unique briefs). | Yes |

### Outreach

| Method | Path | Description | Auth |
|---|---|---|---|
| `GET` | `/outreach` | List user's outreach log + follow-up reminders (sent_at + 5 days) | Yes |
| `POST` | `/outreach` | Log new outreach (company_id, status, notes) | Yes |
| `PUT` | `/outreach/{id}` | Update outreach status or notes | Yes |

### Admin

| Method | Path | Description | Auth |
|---|---|---|---|
| `POST` | `/admin/upload` | Upsert enriched companies to Supabase (CLI or API key gated) | Admin key |

## Match Scoring (Request Time)

When `GET /companies` is called for a logged-in user:

1. Query all active companies from Supabase
2. Compute match score per company: count of overlapping tags between `user.skills` and `company.need_tags`
3. Compute final rank: `(reachability_weight * reachability_probability) + (match_weight * match_score)`
4. Sort descending, paginate, return

For anonymous users (no JWT), sort by reachability_probability only.

~1500 companies with array intersection is trivial compute — no pre-computation needed.

## File Structure

```
backend/
├── main.py              # FastAPI app, CORS, startup
├── auth.py              # JWT verification (Supabase JWT secret)
├── db.py                # Supabase client setup
├── routers/
│   ├── users.py         # GET /me, PUT /me
│   ├── companies.py     # GET /companies, GET /companies/{id}
│   └── outreach.py      # GET/POST/PUT /outreach
├── matching/
│   └── scorer.py        # match_score(user_skills, company_need_tags)
├── pipeline/
│   ├── scrape_yc.py     # existing
│   ├── enrich.py        # existing
│   ├── enrich_config.py # existing
│   ├── normalize_tags.py # existing
│   └── supabase_write.py # NEW — upsert enriched data to Supabase
└── ml/                  # existing, no changes
```

## Supabase Write Step

**File:** `backend/pipeline/supabase_write.py`

Pipeline step that uploads enriched + scored data to Supabase.

1. Read `data/enriched_companies.json` (LLM-generated fields)
2. Read `data/reachability_scores.json` (ML scores)
3. Merge by company name
4. Upsert into `companies` table (insert new, update existing, keyed on `name`)

Uses Supabase service role key (env var `SUPABASE_KEY`) which bypasses row-level security. Only runs on dev machine.

Pipeline order:
```
scrape_yc → ml_predict → enrich → normalize_tags → supabase_write
```

## Environment Variables

| Variable | Where used | Description |
|---|---|---|
| `SUPABASE_URL` | FastAPI + pipeline | Supabase project URL |
| `SUPABASE_KEY` | Pipeline only | Service role key (full access, for upserts) |
| `SUPABASE_ANON_KEY` | FastAPI | Anon key (for client queries with RLS) |
| `SUPABASE_JWT_SECRET` | FastAPI | JWT secret for token verification |

## Deployment

- FastAPI on Railway (~$5/mo)
- Environment variables set in Railway dashboard
- CORS configured for frontend domain (Vercel URL)

## Dependencies (new)

- `fastapi`
- `uvicorn`
- `supabase` (supabase-py)
- `python-jose[cryptography]` (JWT decoding)
- `pydantic` (request/response models, comes with FastAPI)
