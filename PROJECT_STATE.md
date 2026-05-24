# REACH — PROJECT STATE DOC
*Handoff document. Architecture-focused. No code blocks.*
*Last updated: May 24, 2026*

---

## WHAT WE'RE BUILDING

A web app that takes ambitious high schoolers and first/second-year uni students from "I want to work at a startup" to "I sent a great cold email to the right founder" — in one workflow.

**Core edge:** REACH is a curated directory of early-stage YC founders who are realistically reachable by someone without experience or connections. The database is intentionally small. Every company in it was chosen because the founder is likely to respond to a thoughtful cold email from a young person. That curation is the product.

**Motto:** *Cold email the founders who actually respond.*

**The problem we solve:** The bottleneck isn't finding companies or finding emails. It's knowing who is actually reachable, why you specifically fit, and what to say without sounding generic. REACH handles all three.

**What we are not:** A job board. A Hunter.io wrapper. A company directory. An AI email writer.

**Not building in MVP:** AI-generated emails, location-based filtering, automated sending, multi-org track, Hunter.io dependency, email resolution as a core feature.

---

## HOW WE'RE DIFFERENT FROM COMPETITORS

| Platform | What they do | Why REACH is different |
|---|---|---|
| **WellFound (AngelList)** | Companies post open roles → students apply → HR decides | REACH needs no open roles. Students cold-email founders directly with specific offers. |
| **LinkedIn** | Professional networking, job search, recruiter-driven | REACH targets founders who respond to cold emails from nobodies. LinkedIn rewards existing connections. |
| **YC Company Directory** | Raw list of all YC companies, no curation | REACH curates for reachability — small team, early stage, likely to respond. |
| **Hunter.io** | Email finding tool | REACH is not an email finder. The value is knowing *who* to email and *what* to say. |
| **Handshake** | Campus recruiting platform for employers | Employer-driven, formal applications. REACH is student-initiated cold outreach to founders. |

---

## STACK

| Layer | Tool |
|---|---|
| Frontend | Next.js 16 + Tailwind v4 (Vercel) |
| Backend | FastAPI (Railway ~$5/mo) |
| Database | Supabase PostgreSQL (free tier) |
| Auth | Supabase Auth (email+password, ES256 JWT) |
| Local LLM | Qwen3 4B via Ollama (offline pipeline, runs on M2 Mac) |
| ML Model | XGBoost (offline scoring, runs on dev machine) |

---

## DATA PIPELINE (OFFLINE, RUNS ON DEV MACHINE) — ALL COMPLETE

Pipeline runs on developer's M2 Mac. Not user-facing. Scheduled manually on batch release.

**Sources:** YC directory only. 7 batches: W23, S23, W24, S24, W25, S25, W26. 1517 companies total after dedup (count varies slightly per run).

**Pipeline order:**
```
scrape_yc → scrape_founders → ml_predict → enrich (LLM) → normalize_tags → supabase_write
```

### Step 1: YC Scraper — COMPLETE
**File:** `backend/pipeline/scrape_yc.py`
Pulls company data from YC's Algolia API for all target batches. Extracts slug, small_logo_thumb_url, and all other company fields.
**Output:** `data/raw_companies.json`

### Step 1b: Founder Scraper — COMPLETE
**File:** `backend/pipeline/scrape_founders.py`
Scrapes individual YC company pages (`ycombinator.com/companies/{slug}`) for founder data. Parses HTML-entity-encoded JSON embedded in page HTML using bracket-matching. Extracts first active founder's name, title, avatar URL (stripped of AWS signatures), LinkedIn, and Twitter. Rate limited at 1 req/sec with resume support on interruption.
- 1509/1517 founders found (99.5% coverage)
- 1504 with LinkedIn URLs
- 8 tests passing
**Output:** `data/founders.json`

### Step 2: ML Reachability Scoring — COMPLETE
**Files:** `backend/ml/` — features.py, train.py, predict.py, labeling.py, config.py, plus artifacts/
- XGBoost binary classifier, F1 = 0.907 (5-fold CV)
- 200 hand-labeled companies, 10 features
- Thresholds: high >= 0.95, medium >= 0.7, low < 0.7
- Distribution: 755 high / 396 medium / 368 low
- 26 tests passing
**Output:** `data/reachability_scores.json`

### Step 3: LLM Enrichment — COMPLETE
**Files:** `backend/pipeline/enrich.py`, `enrich_config.py`, `normalize_tags.py`
Qwen3 4B via Ollama. Generates: summary, one_liner, need_tags, industry, technical_level, stage_detail, specific_projects.
**Output:** `data/enriched_companies.json`, `data/skill_vocabulary.json`

### Step 4: Supabase Write — COMPLETE
**File:** `backend/pipeline/supabase_write.py`
Merges enriched + scored + raw + founder data, upserts to Supabase companies table in batches of 500.
1519 companies loaded to production Supabase (project: kclvufnaebzqfjwrelbv).
Includes: slug, small_logo_url, founder_name, founder_title, founder_avatar_url, founder_linkedin, founder_twitter, founder_email (placeholder null).

---

## BACKEND API — COMPLETE

**File:** `backend/main.py` — FastAPI app with CORS (localhost:3000). Loads .env via python-dotenv.

### Routers (all complete):

**`backend/routers/users.py`** — `GET /me`, `PUT /me` with auto-create on first call
**`backend/routers/companies.py`** — `GET /companies` (browse, ranked by match+reachability), `GET /companies/{id}` (brief with guidance, 3-brief free limit)
**`backend/routers/outreach.py`** — `POST /outreach`, `GET /outreach`, `PUT /outreach/{id}` with status enum enforcement

### Auth: `backend/auth.py`
JWT verification supporting both ES256 (ECC P-256, current Supabase default) and HS256 (legacy). ES256 tokens verified via JWKS fetched from Supabase. JWKS response is cached in memory. Extracts user_id from `sub` claim with `audience="authenticated"`.

### Database: `backend/db.py` + `backend/db/schema.sql`
Supabase Python SDK singleton. Service role key for full access.

Tables: users, companies, brief_views, outreach_log. RLS on users/brief_views/outreach_log. Companies table is public (no RLS).

**Companies table columns include:** name, yc_batch, description, long_description, summary, one_liner, website, industry, stage, stage_detail, technical_level, team_size, need_tags, specific_projects, is_hiring, status, reachability_score, reachability_probability, founder_name, founder_title, founder_linkedin, founder_twitter, founder_avatar_url, founder_email, slug, small_logo_url, all_locations, tags, industries.

---

## MATCHING + GUIDANCE — COMPLETE

### Skill Matching: `backend/matching/scorer.py`
- match_score = overlap between user skills[] and company need_tags[]
- rank_score = 0.6 * match + 0.4 * reachability
- rank_companies() sorts all companies by rank_score desc

### Outreach Guidance: `backend/guidance/rules.py`
Composable rule-based engine. No AI, no API cost.
- 6 skill-type buckets (coding, design, data, marketing, operations, writing)
- 4 stage rules (building-mvp, launched, growing, scaling)
- 8 industry clusters (30 enrichment industries → 8 clusters + general fallback)
- Template slot-filling with generic fallbacks for missing values
- Generates 4 fields: your_angle, reference_this, dont_say, your_ask
- 38 tests passing

---

## FRONTEND ROUND 1 — COMPLETE

**Stack:** Next.js 16 (App Router), Tailwind v4 (@theme inline), Supabase Auth JS, TypeScript
**Fonts:** Instrument Serif (display), DM Sans (body)
**Theme:** Light, off-white background (#fafafa), teal accent (#0d9488)

### Pages:

| Route | Page | Auth | Status |
|---|---|---|---|
| `/` | Landing | No | COMPLETE — Hero headline, live search bar, floating founder cards with drift animation. Visible to both logged-in and logged-out users. |
| `/login` | Login | No | COMPLETE — Email+password form, preserves ?q= across redirect |
| `/signup` | Signup | No | COMPLETE — Email+password form, redirects to /onboard |
| `/feed` | Feed | Yes | COMPLETE — Search + wide founder cards + industry/reachability filters + load more |
| `/founder/[id]` | Brief | Yes | COMPLETE — Full enriched data, guidance card, email workspace with word count, outreach logging |
| `/onboard` | Onboarding | Yes | COMPLETE — Skill selection (popular chips + search), saves to profile |
| `/profile` | Profile | Yes | COMPLETE — Edit school, grad year, skills, bio, GitHub, portfolio |
| `/tracker` | Tracker | Yes | COMPLETE — Outreach log with stats header, status dropdown, follow-up banner |

### Components (16 total):
AuthForm, Navbar, SearchBar, FounderCard, FloatingCards, FilterBar, LoadMoreButton, FounderBrief, GuidanceCard, EmailWorkspace, SkillPicker, OutreachRow, OutreachForm, StatsHeader

### Lib (5 files):
types.ts (matches backend schemas), supabase.ts (client singleton), api.ts (fetch wrapper with auth headers + token auto-refresh), useAuth.ts (session hook + requireAuth redirect), skills.ts (3128 skill tags + top 30 popular)

### Data flow:
- Landing: unauthenticated GET /companies?limit=6 → floating cards. Search filters client-side.
- Feed: authenticated GET /companies with industry/reachability params. Client-side search on name/one_liner/industry. Pagination via load more (20 per page).
- Brief: GET /companies/{id} → full brief with guidance. 403 = paywall (3 free briefs). Email workspace is local state only. Outreach section for logging.
- Tracker: GET /outreach → list with inline status editing.

---

## ENVIRONMENT CONFIGURATION

### Backend (`backend/.env`):
- SUPABASE_URL — Supabase project URL
- SUPABASE_KEY — Service role key (bypasses RLS)
- SUPABASE_JWT_SECRET — For HS256 fallback (ES256 uses JWKS)

### Frontend (`frontend/.env.local`):
- NEXT_PUBLIC_SUPABASE_URL — Supabase project URL
- NEXT_PUBLIC_SUPABASE_ANON_KEY — Anon/public key
- NEXT_PUBLIC_API_URL — Backend URL (localhost:8000 for dev)

### Deployment (not yet done):
- Frontend: Vercel — add same 3 env vars, change API_URL to production backend
- Backend: Railway/Render — add same 3 env vars
- CORS: Update backend/main.py allow_origins with production domain
- Supabase: Add production URL to Auth > URL Configuration

---

## FOLDER STRUCTURE

```
reach/
├── frontend/
│   ├── app/
│   │   ├── page.tsx                   # Landing page — COMPLETE
│   │   ├── login/page.tsx             # Login — COMPLETE
│   │   ├── signup/page.tsx            # Signup — COMPLETE
│   │   ├── feed/page.tsx              # Feed — COMPLETE
│   │   ├── founder/[id]/page.tsx      # Brief page — COMPLETE
│   │   ├── onboard/page.tsx           # Onboarding — COMPLETE
│   │   ├── profile/page.tsx           # Profile — COMPLETE
│   │   └── tracker/page.tsx           # Tracker — COMPLETE
│   ├── components/
│   │   ├── AuthForm.tsx               # COMPLETE
│   │   ├── Navbar.tsx                 # COMPLETE
│   │   ├── SearchBar.tsx              # COMPLETE
│   │   ├── FounderCard.tsx            # COMPLETE
│   │   ├── FloatingCards.tsx          # COMPLETE
│   │   ├── FilterBar.tsx              # COMPLETE
│   │   ├── LoadMoreButton.tsx         # COMPLETE
│   │   ├── FounderBrief.tsx           # COMPLETE
│   │   ├── GuidanceCard.tsx           # COMPLETE
│   │   ├── EmailWorkspace.tsx         # COMPLETE
│   │   ├── SkillPicker.tsx            # COMPLETE
│   │   ├── OutreachRow.tsx            # COMPLETE
│   │   ├── OutreachForm.tsx           # COMPLETE
│   │   └── StatsHeader.tsx            # COMPLETE
│   └── lib/
│       ├── types.ts                   # COMPLETE
│       ├── supabase.ts                # COMPLETE
│       ├── api.ts                     # COMPLETE
│       ├── useAuth.ts                 # COMPLETE
│       └── skills.ts                  # COMPLETE
│
├── backend/
│   ├── main.py                        # COMPLETE — FastAPI + CORS + dotenv
│   ├── auth.py                        # COMPLETE — JWT verification (ES256 + HS256)
│   ├── db.py                          # COMPLETE — Supabase client
│   ├── schemas.py                     # COMPLETE — Pydantic models
│   ├── routers/
│   │   ├── users.py                   # COMPLETE
│   │   ├── companies.py               # COMPLETE
│   │   └── outreach.py                # COMPLETE
│   ├── pipeline/
│   │   ├── scrape_yc.py               # COMPLETE — extracts slug + logo
│   │   ├── scrape_founders.py         # COMPLETE — scrapes founder data from YC pages
│   │   ├── enrich.py                  # COMPLETE
│   │   ├── enrich_config.py           # COMPLETE
│   │   ├── normalize_tags.py          # COMPLETE
│   │   └── supabase_write.py          # COMPLETE — merges enriched + scores + raw + founders
│   ├── ml/
│   │   ├── config.py                  # COMPLETE
│   │   ├── features.py                # COMPLETE
│   │   ├── train.py                   # COMPLETE
│   │   ├── predict.py                 # COMPLETE
│   │   ├── labeling.py                # COMPLETE
│   │   └── artifacts/                 # COMPLETE
│   ├── matching/
│   │   └── scorer.py                  # COMPLETE
│   ├── guidance/
│   │   └── rules.py                   # COMPLETE
│   └── db/
│       └── schema.sql                 # COMPLETE
│
├── data/
│   ├── raw_companies.json             # 1517 companies (with slug + logo)
│   ├── founders.json                  # 1509 founders scraped
│   ├── reachability_scores.json       # 1519 scored
│   ├── enriched_companies.json        # 1519 enriched
│   ├── skill_vocabulary.json          # Canonical skill taxonomy
│   └── labeling/                      # 200 hand-labeled
│
├── tests/
│   ├── ml/                            # 26 tests
│   ├── matching/                      # Tests for scorer
│   ├── guidance/                      # 38 tests
│   ├── pipeline/                      # 8 tests (founder scraper)
│   └── api/                           # 87 tests (some need auth mock update for ES256)
│
├── docs/superpowers/
│   ├── specs/                         # Design specs
│   └── plans/                         # Implementation plans
│
├── PROJECT_STATE.md
└── requirements.txt
```

---

## BUILD ORDER

| Phase | Focus | Status |
|---|---|---|
| 1a | Pipeline: scrape_yc | COMPLETE |
| 1b | Pipeline: scrape_founders (founder name, title, avatar, LinkedIn, Twitter) | COMPLETE |
| 1c | ML: reachability model + scoring | COMPLETE |
| 1d | Pipeline: LLM enrichment + tag normalization | COMPLETE |
| 1e | Pipeline: supabase_write (enriched + scores + raw + founders) | COMPLETE |
| 2 | Backend API: FastAPI, auth, /companies, /me, /outreach | COMPLETE |
| 3 | Matching + guidance: scorer, rules engine | COMPLETE (38 tests) |
| 4a | Frontend Round 1: landing, login/signup, feed, brief | COMPLETE |
| 4b | Frontend Round 2: onboarding, profile, tracker | COMPLETE |
| 5 | Frontend visual overhaul | PLANNED — user designing aesthetics direction |
| 6 | Polish + deploy: Vercel + Railway, custom domain, E2E | Not started |

---

## KNOWN ISSUES

- **API tests**: 11 tests fail because test auth mocks target `backend.auth._decode_token` but need updating for ES256 JWKS flow. Non-blocking — production auth works correctly.
- **Supabase email confirmations**: Still using default Supabase-branded emails. User aware, deferring to polish phase.
- **Pre-existing test**: `test_get_companies_with_auth_ranked` fails due to ranking order assertion — unrelated to recent changes.

---

## WHAT TO BUILD NEXT

**Frontend Visual Overhaul** — User is planning a full aesthetics redesign. No piecemeal frontend changes until design direction is set.

**After that:**
- Deploy (Vercel + Railway)
- Founder email resolution (schema column `founder_email` already exists as placeholder)

---

## V2 FEATURES (NOT MVP)

- Personalized reachability scoring (user-company pair, composed scoring)
- Feedback loop from outreach outcomes → updated reachability scores
- Founder email resolution pipeline
- SEO/SSR optimization
- Stripe payment integration ($9 one-time)
- Mobile responsiveness fine-tuning
- AI writing feedback on email drafts
- Response rate analytics
- Direct email sending via Gmail OAuth
