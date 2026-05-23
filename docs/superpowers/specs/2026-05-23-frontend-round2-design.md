# Frontend Round 2: Onboarding + Profile + Outreach Tracker — Design Spec

*2026-05-23*

---

## Overview

Round 2 of the REACH frontend: lightweight skill-selection onboarding, profile editing page, and outreach tracker. Builds on the existing Round 1 pages (landing, feed, brief, login/signup). Same stack: Next.js 16 App Router, Tailwind v4, Supabase Auth, client-side fetch to FastAPI backend.

---

## Stack

Same as Round 1:
- **Framework:** Next.js 16 (App Router), Tailwind v4 (@theme inline)
- **Auth:** Supabase Auth JS (client-side, email+password)
- **Data:** Client-side fetch to FastAPI backend
- **Fonts:** Instrument Serif (display), DM Sans (body)

---

## Pages & Routes

| Route | Page | Auth Required | Description |
|---|---|---|---|
| `/onboard` | Onboarding | Yes | Single-screen skill picker, shown after first signup |
| `/profile` | Profile | Yes | Edit skills + profile details (school, bio, etc.) |
| `/tracker` | Outreach Tracker | Yes | Stats header, outreach list with filters, follow-up banner |

**Existing pages modified:**
- `/founder/[id]` — add outreach logging + history section below email workspace
- Navbar — add "Tracker" and "Profile" links for logged-in users

**Onboarding redirect logic:**
- After signup → redirect to `/onboard` (instead of `/feed`)
- After login → redirect to `/feed` (user already onboarded)
- On `/onboard` → if user already has skills set, redirect to `/feed`
- "Skip for now" link on `/onboard` → go to `/feed` without skills

---

## Onboarding Page (`/onboard`)

**Layout:** Single centered column, vertically centered.

**Headline:** "What are you good at?"
**Subtitle:** "Pick 3-5 skills so we can match you with the right founders."

**Popular skills section:**
- 30 most common skills from enriched data, displayed as clickable chips
- Chips toggle on/off on click
- Selected chips get accent background (`bg-accent text-white`), unselected get card style (`bg-card border border-card-border`)

**Top 30 skills (by frequency across 1519 companies):**
Python scripting, API integration, data analysis, data visualization, AI model training, workflow automation, cloud infrastructure, React frontend, SQL queries, scientific writing, content writing, healthcare compliance, financial modeling, user interface design, CRM integration, user experience design, chatbot development, CI/CD pipelines, financial reporting, CI/CD pipeline configuration, API development, lab data analysis, payment processing, AI prompt engineering, financial data analysis, machine learning model training, API integration testing, debugging tools, UI/UX design, email automation

**Search section:**
- Below popular chips: search bar with placeholder "Search for more skills..."
- Debounced (300ms), filters the full need_tags list (3,128 unique tags)
- Matching results appear as clickable chips below the search bar (max 20 shown)
- Full tag list stored as a static JSON import in the frontend

**Selected skills display:**
- Horizontal row at bottom showing selected skills as chips with X button to remove
- Counter text: "3 of 5 selected" (updates live)
- If > 5 selected, counter turns amber: "6 of 5 selected — try to narrow down"

**Actions:**
- "Continue" button — enabled when >= 3 skills selected. Calls `PUT /me` with `{skills: [...]}`. Redirects to `/feed`.
- "Skip for now" link (text only, below button) — redirects to `/feed` without saving skills.

---

## Profile Page (`/profile`)

**Layout:** Single centered column, max-w-2xl (same as brief page).

**Section 1: Skills**
- Same `SkillPicker` component as onboarding page
- Shows currently selected skills as highlighted chips
- Add/remove skills inline
- Auto-saves skills via `PUT /me` on change (debounced 500ms)

**Section 2: Profile Details**
- Form fields:
  - School (text input)
  - Graduation year (number input)
  - Bio (textarea, 3 rows)
  - GitHub URL (text input)
  - Portfolio URL (text input)
- "Save" button — calls `PUT /me` with all fields
- Success message: brief "Saved" text that fades after 2 seconds
- Pre-populated from `GET /me` on page load

**Section 3: Account Info (read-only)**
- Email (from auth session)
- Tier badge: "Free" or "Unlocked"
- If free: message "Complete your profile to unlock unlimited briefs"

**Navbar:** Add "Profile" link. Logged-in navbar order: Feed | Tracker | Profile | Sign out

---

## Outreach Tracker Page (`/tracker`)

**Layout:** Single centered column, max-w-3xl (same as feed).

### Stats Header

Three count boxes in a horizontal row:
- **Sent** — count of entries with status "sent"
- **Replied** — count of entries with status "replied"
- **Meetings** — count of entries with status "meeting"

Each box: card background, large number, label below. Accent color for "Meetings" count.

### Follow-up Banner

If any entries have status "sent" and `followup_date` is in the past (compared to current date): show a teal banner at the top of the list.
- Text: "You have X follow-up(s) due"
- Banner style: `bg-guidance-bg border-l-4 border-guidance-border` (same as guidance card)

### Filter Chips

Below stats: All | Sent | Replied | Meeting | No Response
- Same toggle chip style as feed reachability filter
- Filters the list below

### Outreach List

Each row is a card showing:
- Company name (links to `/founder/[company_id]`)
- Status badge (colored pill):
  - sent: `bg-tertiary/10 text-tertiary`
  - replied: `bg-reach-high/10 text-reach-high`
  - meeting: `bg-accent/10 text-accent`
  - no-response: `bg-reach-med/10 text-reach-med`
- Sent date (formatted: "May 23, 2026")
- Notes preview (truncated to 1 line)
- Click status badge → dropdown with 4 status options → `PUT /outreach/{id}`

**Sorted:** Most recent first (backend default).

**Empty state:** "No outreach logged yet. Visit a founder's brief to send your first email." with a link to `/feed`.

---

## Brief Page Updates (`/founder/[id]`)

**Add below the email workspace:**

### Outreach Section

**"Log this outreach" button** — teal accent, same style as other action buttons.

On click, expands an inline form (not a modal):
- Status dropdown: sent (default) | replied | meeting | no-response
- Notes textarea (optional, 2 rows, placeholder: "Any notes...")
- Sent at: defaults to current datetime (hidden, auto-set)
- "Save" button → `POST /outreach` with `{company_id, status, notes, sent_at}`
- On success: collapse form, show new entry in history below

**Outreach history for this company:**
- If user has logged outreach for this company before, show entries below the log button
- Same `OutreachRow` component as tracker page (company name omitted since we're already on the brief)
- Status editable inline via dropdown
- Fetched by filtering `GET /outreach` results client-side by company_id

---

## Components

| Component | File | Used on | Purpose |
|---|---|---|---|
| `SkillPicker` | `components/SkillPicker.tsx` | Onboard, Profile | Popular chips + search + selected display |
| `OutreachForm` | `components/OutreachForm.tsx` | Brief page, Tracker | Inline form to log new outreach |
| `OutreachRow` | `components/OutreachRow.tsx` | Brief page, Tracker | Single outreach entry with editable status |
| `StatsHeader` | `components/StatsHeader.tsx` | Tracker | Three count boxes + follow-up banner |

**Existing components modified:**
- `Navbar` — add Tracker and Profile links for authenticated users

---

## Data Flow

**Onboarding:**
1. Signup → Supabase Auth → redirect to `/onboard`
2. `/onboard` loads → check `GET /me` → if skills already set, redirect to `/feed`
3. User picks skills → "Continue" → `PUT /me {skills}` → redirect to `/feed`

**Profile:**
1. Page loads → `GET /me` → populate form
2. Skill changes → debounced `PUT /me {skills}` (auto-save)
3. Profile details → "Save" button → `PUT /me {school, grad_year, bio, ...}`

**Tracker:**
1. Page loads → `GET /outreach` → compute stats, check follow-ups, render list
2. Filter chips → client-side filter on status
3. Status badge click → dropdown → `PUT /outreach/{id} {status}`

**Brief page outreach:**
1. Brief loads (existing) → also fetch `GET /outreach` → filter by company_id → show history
2. "Log this outreach" → expand form → submit → `POST /outreach` → append to history
3. Status update → `PUT /outreach/{id}`

**Skill search (on onboard + profile):**
- Full tag list loaded as a static import (JSON file bundled at build time)
- Search filters client-side — no API call needed
- Top 30 popular skills hardcoded as a constant

---

## API Endpoints Used

| Action | Method | Endpoint | Body |
|---|---|---|---|
| Get profile | GET | `/me` | — |
| Save skills | PUT | `/me` | `{skills: string[]}` |
| Save profile | PUT | `/me` | `{school, grad_year, bio, github_url, portfolio_url}` |
| List outreach | GET | `/outreach` | — |
| Log outreach | POST | `/outreach` | `{company_id, status, sent_at?, notes?}` |
| Update outreach | PUT | `/outreach/{id}` | `{status?, notes?}` |

No new backend endpoints required.

---

## New Files

| Action | File | Responsibility |
|---|---|---|
| Create | `frontend/app/onboard/page.tsx` | Skill selection onboarding |
| Create | `frontend/app/profile/page.tsx` | Profile editing page |
| Create | `frontend/app/tracker/page.tsx` | Outreach tracker page |
| Create | `frontend/components/SkillPicker.tsx` | Skill chip grid + search |
| Create | `frontend/components/OutreachForm.tsx` | Inline outreach log form |
| Create | `frontend/components/OutreachRow.tsx` | Single outreach entry row |
| Create | `frontend/components/StatsHeader.tsx` | Stats boxes + follow-up banner |
| Create | `frontend/lib/skills.ts` | Top 30 skills constant + full tag list for search |
| Modify | `frontend/components/Navbar.tsx` | Add Tracker + Profile links |
| Modify | `frontend/components/AuthForm.tsx` | Signup redirects to `/onboard` instead of `/feed` |
| Modify | `frontend/app/founder/[id]/page.tsx` | Add outreach section below email workspace |
| Modify | `frontend/lib/api.ts` | Add fetchOutreach, createOutreach, updateOutreach, updateProfile |

---

## What This Spec Does NOT Cover

- Tier upgrade logic (free → unlocked based on profile completeness) — deferred
- Stripe payment integration — post-MVP
- Founder name/email/photo enrichment — separate pipeline spec
- Mobile responsiveness fine-tuning — post-V1
