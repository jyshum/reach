# Frontend Round 1: Landing + Feed + Brief — Design Spec

*2026-05-21*

---

## Overview

Round 1 of the REACH frontend: three core pages (landing, feed, brief) that let students discover reachable YC founders and write cold emails. Next.js + Tailwind, client-side data fetching from FastAPI backend, Supabase Auth for login/signup. Light theme, clean and approachable.

Round 2 (onboarding profile + outreach tracker) is a separate spec.

---

## Stack

- **Framework:** Next.js (App Router)
- **Styling:** Tailwind CSS
- **Auth:** Supabase Auth JS (client-side, email+password)
- **Data:** Client-side fetch to FastAPI backend (`GET /companies`, `GET /companies/{id}`, `GET /me`, `PUT /me`)
- **Deploy:** Vercel (free tier)
- **No SSR for authenticated pages** — client-side fetch with loading states

---

## Pages & Routes

| Route | Page | Auth Required | Description |
|---|---|---|---|
| `/` | Landing | No | Hero headline, live search bar with floating founder cards |
| `/feed` | Feed | Yes | Search + wide founder cards, filters, "Load more" pagination |
| `/founder/[id]` | Brief | Yes (+ brief limit) | Full enriched data, guidance card, email workspace |
| `/login` | Login | No | Email + password form |
| `/signup` | Signup | No | Email + password form, redirect to feed |

**Auth redirects:**
- Unauthenticated user hitting `/feed` or `/founder/[id]` → redirect to `/login`
- Logged-in user visiting `/` → redirect to `/feed`
- After signup → redirect to `/feed`
- Search query preserved in URL params across login redirect (e.g., `/login?q=biotech` → after login → `/feed?q=biotech`)

---

## Landing Page (`/`)

**Layout:** Single centered column, full viewport height.

**Hero section (above fold):**
- Headline: **"You don't need connections. You need the right founder."**
- Search bar below headline, large and rectangular
- Search bar placeholder text: *"Cold email the founders who actually respond"*
- 5-6 founder cards floating behind the search bar at slight angles, low opacity, subtle drift animation
- Cards show real data from unauthenticated `GET /companies` call

**Search behavior:**
- On typing: debounced API call (~300ms), floating cards swap to show matching results with fade+slide animation
- On pressing Enter or clicking a card: redirect to `/login?q={search-term}`
- Cards remain floating/scattered, not a list

**Below the fold:**
- One-liner: "A curated directory of 750+ reachable YC founders"
- "Sign up free" button
- No feature tour, no testimonials for V1

---

## Feed Page (`/feed`)

**Layout:** Search bar at top, founder cards below, "Load more" at bottom.

**Search bar:** Same component as landing page, but searches update the card list below instead of floating cards.

**Filter bar:** Below search bar.
- Industry dropdown (from the 30 enrichment industries)
- Reachability filter chips: All / High / Medium / Low

**Founder cards:** Wide horizontal cards in a single column, 20 per batch.
- Each card shows: initials avatar, founder name (or company name if no founder data), role, company, one-liner, industry tag, team size tag, reachability badge, skill match count (if applicable)
- Cards ranked by match+reachability score (60/40 weighting from backend)
- Click a card → navigate to `/founder/[id]`

**Pagination:** "Load more" button at bottom, loads next 20. Not infinite scroll.

**Empty state:** "No founders match your search. Try different keywords."

---

## Brief Page (`/founder/[id]`)

**Layout:** Single column, full page, four sections top to bottom.

### Section 1: Founder Header
- Large initials avatar (placeholder until photo enrichment)
- Company name (primary) + "Founder" as placeholder title
- Metadata row: YC batch badge, industry, team size, reachability signal
- Link icons: website, LinkedIn, Twitter (open in new tab, only shown if URL exists)

### Section 2: Company Info
- Summary (2 sentences from enrichment)
- One-liner
- Stage detail + technical level
- Need tags (as pills/chips)
- Specific projects header: "What you could help with"
  - 2 bullet points from `specific_projects`

### Section 3: Guidance Card
- Visually distinct: light teal background (`#f0fdfa`), left border accent (`#0d9488`)
- Header: "Your Approach"
- Four labeled fields:
  - **Your angle** — from `guidance.your_angle`
  - **Reference this** — from `guidance.reference_this`
  - **Don't say** — from `guidance.dont_say`
  - **Your ask** — from `guidance.your_ask`
- If user has no skills set: show message "Add skills to your profile to get personalized guidance" with link to profile

### Section 4: Email Workspace
- Textarea with placeholder: "Write your email here..."
- Word count indicator below textarea
  - Default: gray text showing count
  - At 120+ words: turns yellow/amber
  - At 150+ words: turns red
  - Target label: "Aim for under 150 words"
- "Open in Gmail" button (mailto: link with pre-filled subject if founder email exists)
  - Disabled/hidden until founder email enrichment is done for V1

**Brief limit (free tier):** 3 briefs. On the 4th attempt, show a paywall message instead of the brief content: "You've used your 3 free briefs. Complete your profile to unlock unlimited access." (Backend enforces this via 403 response.)

---

## Components

| Component | File | Used on | Purpose |
|---|---|---|---|
| `SearchBar` | `components/SearchBar.tsx` | Landing, Feed | Large input, placeholder motto, triggers search |
| `FounderCard` | `components/FounderCard.tsx` | Landing, Feed | Wide horizontal card with founder/company info |
| `FloatingCards` | `components/FloatingCards.tsx` | Landing | Cards floating behind search bar with animations |
| `FounderBrief` | `components/FounderBrief.tsx` | Brief page | Full enriched data display |
| `GuidanceCard` | `components/GuidanceCard.tsx` | Brief page | Distinct card with 4 guidance fields |
| `EmailWorkspace` | `components/EmailWorkspace.tsx` | Brief page | Textarea + word count + Gmail button |
| `AuthForm` | `components/AuthForm.tsx` | Login, Signup | Shared email+password form |
| `Navbar` | `components/Navbar.tsx` | All pages | Logo + nav + auth state |
| `LoadMoreButton` | `components/LoadMoreButton.tsx` | Feed | Loads next 20 results |
| `FilterBar` | `components/FilterBar.tsx` | Feed | Industry dropdown + reachability chips |

---

## Data Flow

**Landing page:**
1. Page loads → unauthenticated `GET /companies?limit=6` → populate floating cards
2. User types → debounced `GET /companies?search={query}&limit=6` → swap floating cards
3. User clicks card or presses Enter → redirect to `/login?q={query}`

**Feed page:**
1. Page loads → `GET /me` to get user skills → `GET /companies?limit=20` with auth header → render ranked cards
2. User searches → `GET /companies?search={query}&limit=20` → replace cards
3. User filters → append `&industry=X` or `&reachability=Y` to query
4. User clicks "Load more" → `GET /companies?page=2&limit=20` → append cards
5. User clicks card → navigate to `/founder/[id]`

**Brief page:**
1. Page loads → `GET /companies/{id}` with auth header → render brief
2. If 403 → show paywall message
3. If 404 → show "Founder not found"
4. Guidance card populated from `response.guidance` (null if no skills)
5. Email workspace is local state only — no API calls

**Auth flow:**
1. Signup → `supabase.auth.signUp({email, password})` → redirect to `/feed`
2. Login → `supabase.auth.signInWithPassword({email, password})` → redirect to `/feed` (or `/feed?q=X` if query preserved)
3. Auth token automatically included in API calls via Supabase client
4. Navbar checks auth state → shows login/signup buttons or user profile link

---

## Design System

### Colors
- Background: `#fafafa` (off-white)
- Card background: `#ffffff`
- Primary text: `#1a1a1a`
- Secondary text: `#666666`
- Tertiary text: `#999999`
- Accent: `#0d9488` (teal)
- Reachability HIGH: `#16a34a` (green)
- Reachability MED: `#d97706` (amber)
- Reachability LOW: `#9ca3af` (gray)
- Guidance card background: `#f0fdfa`
- Guidance card border: `#0d9488`
- Card border: `#e5e5e5`

### Typography
- Headlines: distinctive serif or display font (chosen during implementation)
- Body: clean sans-serif (chosen during implementation)
- No generic fonts (Inter, Roboto, Arial)

### Cards
- White background, `1px solid #e5e5e5` border, `border-radius: 12px`
- Subtle shadow: `0 1px 3px rgba(0,0,0,0.08)`
- Hover: slight lift with increased shadow
- No harsh drop shadows

### Overall feel
Clean, breathable, confident but not intimidating. A student opens this and thinks "I can do this."

---

## Founder Data — Current State

The enriched data currently does NOT include:
- `founder_name` — show company name as primary, "Founder" as title placeholder
- `founder_email` — "Open in Gmail" button hidden/disabled for V1
- `founder_photo` — use initials avatar

The frontend components accept these fields and will populate them automatically once founder enrichment runs. No frontend changes needed later.

---

## What This Spec Does NOT Cover

- Onboarding/profile page (Round 2)
- Outreach tracker (Round 2)
- SEO/SSR optimization (post-V1)
- Founder name/email/photo enrichment (separate pipeline spec)
- Payment/Stripe integration (post-V1)
- Mobile responsiveness fine-tuning (post-V1, basic responsive via Tailwind)
