# REACH — PROJECT STATE DOC
*Handoff document. Architecture-focused. No code blocks.*
*Last updated: May 27, 2026*

---

## WHAT WE'RE BUILDING

A web app that takes ambitious high schoolers and first/second-year uni students from "I want to work at a startup" to "I sent a great cold email to the right founder" — in one workflow.

**Core edge:** REACH is a curated directory of early-stage YC founders who are realistically reachable by someone without experience or connections. The database is intentionally small. Every company in it was chosen because the founder is likely to respond to a thoughtful cold email from a young person. That curation is the product.

**Motto:** *Cold email the founders who actually respond.*

**The problem we solve:** The bottleneck isn't finding companies or finding emails. It's knowing who is actually reachable, why you specifically fit, and what to say without sounding generic. REACH handles all three.

**What we are not:** A job board. A Hunter.io wrapper. A company directory.

**Current product direction:** Backend is feature-complete through Phase 1 of the email pipeline. Gmail OAuth is live and tested. Email generation (Claude Haiku), sending via Gmail API, and reply detection are all wired up. Frontend has been updated to connect all email features to the UI. Visual overhaul of landing/feed/brief pages is ongoing per `jared_ques.txt`.

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
| Email LLM | Claude Haiku (claude-haiku-4-5-20251001) via Anthropic API |
| Email Sending | Gmail API via user OAuth |
| Local LLM | Qwen3 4B / Llama 3.2 3B via Ollama (offline pipeline) |
| Encryption | Fernet symmetric encryption for Gmail refresh tokens |

---

## DATA PIPELINE (OFFLINE, RUNS ON DEV MACHINE) — ALL COMPLETE

Pipeline runs on developer's M2 Mac. Not user-facing. Scheduled manually on batch release.

**Sources:** YC directory only. 7 batches: W23, S23, W24, S24, W25, S25, W26. 1517 companies total after dedup.

**Pipeline order:**
```
scrape_yc → scrape_founders → enrich (LLM) → normalize_tags → enrich_capabilities → supabase_write
```

### Step 1: YC Scraper — COMPLETE
**File:** `backend/pipeline/scrape_yc.py`
Pulls company data from YC's Algolia API for all target batches.
**Output:** `data/raw_companies.json`

### Step 1b: Founder Scraper — COMPLETE
**File:** `backend/pipeline/scrape_founders.py`
Scrapes individual YC company pages for founder data. 1509/1517 founders found (99.5% coverage).
**Output:** `data/founders.json`

### Step 2: LLM Enrichment — COMPLETE
**Files:** `backend/pipeline/enrich.py`, `enrich_config.py`, `normalize_tags.py`
Qwen3 4B via Ollama. Generates: summary, one_liner, need_tags, industry, technical_level, stage_detail, specific_projects.
**Output:** `data/enriched_companies.json`

### Step 2b: Capability Re-Enrichment — COMPLETE
**File:** `backend/pipeline/enrich_capabilities.py`
Llama 3.2 3B via Ollama. Maps free-form need_tags to constrained two-tier capability vocabulary (20 tier-2 options). 1419/1517 companies tagged (93.5% coverage).
**Output:** `capability_tags[]` column in Supabase

### Step 3: Supabase Write — COMPLETE
**File:** `backend/pipeline/supabase_write.py`
Merges all data sources, upserts to Supabase in batches of 500. 1519 companies loaded.

---

## REACHABILITY SCORING — COMPLETE (RULE-BASED)

**File:** `backend/scoring/reachability.py`

Replaced the original XGBoost ML model with a weighted rule-based system. Simpler, more transparent, no training data dependency.

**Factors (weights):**
- Team size ≤ 10 (0.30)
- Stage = building-mvp (0.25)
- Is hiring (0.20)
- Location proximity to user (0.15)
- Has LinkedIn or Twitter (0.10)

**Thresholds:** high ≥ 0.70, medium ≥ 0.40, low < 0.40

Returns score + list of human-readable contributing factors shown on brief page.

**Note:** `backend/ml/` still contains the deprecated XGBoost code. Tests pass but it's no longer used at runtime.

---

## CAPABILITY MATCHING — COMPLETE (TWO-TIER SYSTEM)

**Files:** `backend/capabilities.py`, `backend/matching/scorer.py`, `frontend/lib/capabilities.ts`

### Vocabulary
**Tier 1 (5 categories, user picks max 2):** Engineering, Data & ML, Design & UX, Content & Research, Business & Ops

**Tier 2 (20 capabilities, user picks max 3):** frontend-development, backend-apis, mobile-development, devops-infrastructure, systems-programming, deep-learning, nlp-language-models, computer-vision, data-pipelines, analytics-visualization, ml-ops, ui-design, ux-research, product-design, technical-writing, market-research, scientific-writing, sales-outreach, operations-process, financial-analysis, growth-marketing

### Matching Logic
- match_score = count of overlapping tier-2 capabilities (0–3)
- rank_score = 0.4 * reachability + 0.6 * (match_count / 3)
- Falls back to `need_tags` if `capability_tags` empty

---

## GUIDANCE SYSTEM — COMPLETE

**File:** `backend/guidance/rules.py`

Composable rule-based engine. No AI, no API cost.
- 6 skill-type buckets × 4 stage rules × 8 industry clusters
- Template slot-filling with generic fallbacks
- Generates 4 fields: your_angle, reference_this, dont_say, your_ask
- 38 tests passing

---

## EMAIL PIPELINE — PHASE 1 COMPLETE

### Email Generation
**Files:** `backend/email/prompt.py`, `backend/email/generate.py`

Claude Haiku generates cold email drafts. 4 tones: **curious**, **friendly**, **scrappy**, **earnest**. Prompt enforces:
- High school student opener (pattern interrupt)
- 4–5 sentences max
- No filler enthusiasm, no company compliments
- Specific hook showing understanding of their work
- Capability overlap used as guidance angle

### Gmail OAuth
**File:** `backend/email/oauth.py`

Google OAuth 2.0 with `gmail.send` + `gmail.readonly` scopes. Refresh tokens encrypted with Fernet and stored in `gmail_tokens` table. Token exchange, refresh, encrypt/decrypt all tested.

**Google Cloud project:** REACH (project in Jared's Google account). OAuth consent screen configured, Gmail API enabled. Currently unverified (limited to 100 test users).

### Gmail Send + Reply Detection
**File:** `backend/email/gmail.py`

- `send_email()` — sends via Gmail API, returns message_id + thread_id
- `check_thread_for_reply()` — checks if thread has reply from someone other than sender
- Sent emails logged to `email_log` table and `outreach_log` table automatically

### Email Router
**File:** `backend/routers/email.py`

| Endpoint | Method | Purpose |
|---|---|---|
| `/email/gmail/auth-url` | GET | Returns Google OAuth consent URL |
| `/email/gmail/callback` | POST | Exchanges auth code for tokens, stores encrypted refresh token |
| `/email/gmail/status` | GET | Returns connection state + email |
| `/email/gmail/disconnect` | DELETE | Removes stored tokens |
| `/email/generate` | POST | Generates draft using Claude + company/user context |
| `/email/send` | POST | Sends via Gmail, logs to email_log + outreach_log |
| `/email/check-replies` | POST | Scans all sent threads for replies |

### Database Tables (Email)
- `gmail_tokens` — user_id (PK), encrypted_refresh_token, gmail_email. RLS enabled.
- `email_log` — full audit trail: original_draft, final_text, subject_line, tone, gmail_thread_id, status, sent_at, reply_detected_at. RLS enabled.

---

## BACKEND API — COMPLETE

**File:** `backend/main.py` — FastAPI app with CORS (localhost:3000). Loads .env via python-dotenv.

### Routers (all complete):

**`backend/routers/users.py`** — `GET /me`, `PUT /me` with auto-create on first call
**`backend/routers/companies.py`** — `GET /companies` (browse, ranked by match+reachability), `GET /companies/{id}` (brief with guidance)
**`backend/routers/outreach.py`** — `POST /outreach`, `GET /outreach`, `PUT /outreach/{id}`
**`backend/routers/email.py`** — Gmail OAuth, email generation, send, reply checking (7 endpoints)

### Auth: `backend/auth.py`
JWT verification supporting both ES256 (ECC P-256, current Supabase default) and HS256 (legacy). ES256 tokens verified via JWKS fetched from Supabase.

### Database: `backend/db.py` + `backend/db/schema.sql`
Supabase Python SDK singleton. Service role key for full access.

Tables: users, companies, brief_views, outreach_log, gmail_tokens, email_log. RLS on all tables except companies (read-only policy added).

### Environment (`backend/.env`):
- SUPABASE_URL, SUPABASE_KEY, SUPABASE_JWT_SECRET
- GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI
- TOKEN_ENCRYPTION_KEY (Fernet key for Gmail token encryption)
- ANTHROPIC_API_KEY (for Claude email generation)

---

## FRONTEND — FUNCTIONAL, VISUAL OVERHAUL PLANNED

**Stack:** Next.js 16 (App Router), Tailwind v4 (@theme inline), Supabase Auth JS, TypeScript
**Fonts:** Instrument Serif (display), DM Sans (body)
**Theme:** Light, off-white background (#fafafa), teal accent (#0d9488)

### Pages:

| Route | Page | Status |
|---|---|---|
| `/` | Landing | COMPLETE — Hero, search bar, auto-sliding founder card carousel, decorative background shapes, YC logo |
| `/login` | Login | COMPLETE |
| `/signup` | Signup | COMPLETE |
| `/onboard` | Onboarding | COMPLETE — Two-tier capability picker + location step |
| `/feed` | Feed | COMPLETE — Search + founder cards + industry/reachability filters + pagination |
| `/founder/[id]` | Brief | COMPLETE — Full brief, reachability factors, guidance card, email workspace with tone picker + generate + send via Gmail, outreach logging |
| `/profile` | Profile | COMPLETE — Capabilities, profile details, Gmail connect/disconnect section |
| `/tracker` | Tracker | COMPLETE — Outreach log with stats header, status dropdown, follow-up banner |
| `/gmail/callback` | OAuth callback | COMPLETE — Exchanges code, redirects to profile |

### Components (15 total):
AuthForm, Navbar, SearchBar, FounderCard, FloatingCards, FilterBar, LoadMoreButton, FounderBrief, GuidanceCard, EmailWorkspace, CapabilityPicker, SkillPicker (legacy/unused), OutreachRow, OutreachForm, StatsHeader

### Key Frontend Features:
- **EmailWorkspace** — 4-tone picker (curious/friendly/scrappy/earnest), "Generate draft" button (calls Claude), subject line field, "Send via Gmail" button (if connected) or "Connect Gmail to send" prompt, copy draft fallback, word counter
- **FounderCard + FounderBrief** — Show `capability_tags` with human-readable labels (falls back to `need_tags`)
- **Profile Gmail section** — Shows connected email + disconnect, or connect button
- **FloatingCards** — CSS-animated infinite auto-scroll marquee (no user interaction)
- **CapabilityPicker** — Two-tier selection (max 2 tier-1, max 3 tier-2)

### Lib:
- `types.ts` — CompanyCard, CompanyBrief, UserProfile, OutreachEntry, EmailDraft, GmailStatus, Guidance
- `api.ts` — 15 API functions including 7 email endpoints, auth header with proactive token refresh, Content-Type auto-set for JSON bodies
- `capabilities.ts` — Two-tier vocabulary with display labels
- `supabase.ts`, `useAuth.ts`

---

## TESTS — 167 PASSING

| Area | Count |
|---|---|
| ML (deprecated) | 26 |
| Pipeline | 8 |
| Matching | tests for scorer |
| Guidance | 38 |
| Scoring (reachability) | tests for rule-based |
| Email (prompt, oauth, gmail, generate) | 19 |
| API (email router) | 16 |
| API (users, companies, outreach) | ~60 |
| **Total** | **167 passed, 1 skipped** |

---

## FOLDER STRUCTURE

```
reach/
├── frontend/
│   ├── app/
│   │   ├── page.tsx                   # Landing — COMPLETE
│   │   ├── login/page.tsx             # Login — COMPLETE
│   │   ├── signup/page.tsx            # Signup — COMPLETE
│   │   ├── feed/page.tsx              # Feed — COMPLETE
│   │   ├── founder/[id]/page.tsx      # Brief page — COMPLETE
│   │   ├── onboard/page.tsx           # Onboarding — COMPLETE
│   │   ├── profile/page.tsx           # Profile — COMPLETE
│   │   ├── tracker/page.tsx           # Tracker — COMPLETE
│   │   └── gmail/callback/page.tsx    # OAuth callback — COMPLETE
│   ├── components/
│   │   ├── AuthForm.tsx               # COMPLETE
│   │   ├── Navbar.tsx                 # COMPLETE
│   │   ├── SearchBar.tsx              # COMPLETE
│   │   ├── FounderCard.tsx            # COMPLETE (capability_tags)
│   │   ├── FloatingCards.tsx          # COMPLETE (auto-scroll)
│   │   ├── FilterBar.tsx              # COMPLETE
│   │   ├── LoadMoreButton.tsx         # COMPLETE
│   │   ├── FounderBrief.tsx           # COMPLETE (capability_tags)
│   │   ├── GuidanceCard.tsx           # COMPLETE
│   │   ├── EmailWorkspace.tsx         # COMPLETE (generate + send)
│   │   ├── CapabilityPicker.tsx       # COMPLETE
│   │   ├── SkillPicker.tsx            # Legacy, unused
│   │   ├── OutreachRow.tsx            # COMPLETE
│   │   ├── OutreachForm.tsx           # COMPLETE
│   │   └── StatsHeader.tsx            # COMPLETE
│   └── lib/
│       ├── types.ts                   # COMPLETE
│       ├── supabase.ts                # COMPLETE
│       ├── api.ts                     # COMPLETE (15 functions)
│       ├── useAuth.ts                 # COMPLETE
│       ├── capabilities.ts            # COMPLETE (two-tier)
│       └── skills.ts                  # Legacy, unused
│
├── backend/
│   ├── main.py                        # COMPLETE — FastAPI + CORS + dotenv
│   ├── auth.py                        # COMPLETE — JWT (ES256 + HS256)
│   ├── db.py                          # COMPLETE — Supabase client
│   ├── schemas.py                     # COMPLETE — Pydantic models
│   ├── capabilities.py                # COMPLETE — Two-tier vocabulary
│   ├── routers/
│   │   ├── users.py                   # COMPLETE
│   │   ├── companies.py               # COMPLETE
│   │   ├── outreach.py                # COMPLETE
│   │   └── email.py                   # COMPLETE (7 endpoints)
│   ├── email/
│   │   ├── prompt.py                  # COMPLETE (4 tones)
│   │   ├── generate.py                # COMPLETE (Claude Haiku)
│   │   ├── oauth.py                   # COMPLETE (Google OAuth)
│   │   └── gmail.py                   # COMPLETE (send + reply check)
│   ├── scoring/
│   │   └── reachability.py            # COMPLETE (rule-based)
│   ├── matching/
│   │   └── scorer.py                  # COMPLETE (capability overlap)
│   ├── guidance/
│   │   └── rules.py                   # COMPLETE
│   ├── pipeline/                      # COMPLETE (all offline scripts)
│   ├── ml/                            # DEPRECATED (XGBoost, not used at runtime)
│   └── db/
│       └── schema.sql                 # COMPLETE (6 tables)
│
├── tests/                             # 167 passed, 1 skipped
├── data/                              # Pipeline outputs
├── docs/superpowers/                  # Design specs + implementation plans
├── PROJECT_STATE.md
├── jared_ques.txt                     # User's product questions + directions
└── requirements.txt
```

---

## BUILD ORDER

| Phase | Focus | Status |
|---|---|---|
| 1a | Pipeline: scrape_yc | COMPLETE |
| 1b | Pipeline: scrape_founders | COMPLETE |
| 1c | Pipeline: LLM enrichment + tag normalization | COMPLETE |
| 1d | Pipeline: capability re-enrichment (two-tier) | COMPLETE |
| 1e | Pipeline: supabase_write | COMPLETE |
| 2 | Backend API: FastAPI, auth, /companies, /me, /outreach | COMPLETE |
| 3a | Reachability scoring (rule-based, replaced ML) | COMPLETE |
| 3b | Capability matching (two-tier) | COMPLETE |
| 3c | Guidance rules engine | COMPLETE |
| 4a | Frontend Round 1: landing, login/signup, feed, brief | COMPLETE |
| 4b | Frontend Round 2: onboarding, profile, tracker | COMPLETE |
| 5a | Email pipeline: Gmail OAuth, generation, send, reply detection | COMPLETE |
| 5b | Frontend email integration: tone picker, generate, send, Gmail connect | COMPLETE |
| 5c | Frontend capability tag display update | COMPLETE |
| 6 | Landing/feed/brief visual overhaul | IN PROGRESS (per jared_ques.txt) |
| 7 | Polish + deploy: Vercel + Railway, custom domain | Not started |

---

## KNOWN ISSUES

- **Google OAuth unverified**: Limited to 100 manually-added test users until Google approves verification. Need terms/privacy pages.
- **Background reply polling not implemented**: Reply checking is manual-only (`POST /email/check-replies`). Spec calls for 4-hour auto-polling.
- **Deprecated ML code**: `backend/ml/` still in codebase, tests still pass, but not used at runtime. Should be cleaned up.
- **SkillPicker.tsx + skills.ts**: Legacy components replaced by CapabilityPicker. Dead code.
- **Free tier brief limit**: Enforcement code removed but `brief_views` table still exists in schema.
- **Companies RLS**: Supabase flagged RLS disabled on companies table. Should add read-only policy for authenticated users.
- **Supabase email confirmations**: Still using default Supabase-branded emails.

---

## WHAT TO BUILD NEXT

**Per `jared_ques.txt` — product/strategy questions to brainstorm:**
1. Reachability as ML portfolio piece — is the rule-based system enough, or should the "deep ML" angle be the email reply prediction model (Phase 2, needs real outreach data)?
2. Capability tags quality — are enriched tags good enough? Should search be overhauled?
3. Email as core feature — pipeline is built, but is it the right product direction?

**Immediate technical work:**
- Landing/feed/brief visual overhaul (per jared_ques.txt directions)
- Background reply polling (4-hour auto-check)
- Clean up deprecated ML code + legacy SkillPicker
- Companies table RLS policy
- Deploy (Vercel + Railway)

---

## V2 FEATURES (NOT MVP)

- Phase 2 email ML: reply prediction model trained on real outreach outcomes (needs ~100+ sent emails)
- Founder email resolution pipeline
- SEO/SSR optimization
- Stripe payment integration
- Mobile responsiveness fine-tuning
- Response rate analytics
