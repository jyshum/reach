# Frontend Visual Workflow Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refresh Reach's landing, feed, profile skill selection, and email workspace so the product feels founder-specific, polished, and launch-ready without adding Gmail OAuth or social-network scope.

**Architecture:** Keep the existing Next.js App Router frontend and FastAPI backend contract. Add small reusable frontend primitives for founder cards and combobox selection, then wire those into landing, feed, onboarding/profile, and email drafting. Backend changes are limited to response-schema/type alignment only if the frontend needs fields already present in the database.

**Tech Stack:** Next.js 16, React 19, TypeScript, Tailwind v4, Supabase Auth JS, FastAPI response models.

---

## Scope

This plan implements Track A only:
- shared founder/company card redesign
- landing visual overhaul with founder preview rail
- feed card/search refresh
- profile/onboarding skill combobox
- copy-to-clipboard and mailto workflow in `EmailWorkspace`

This plan does not implement:
- Supabase custom SMTP
- Gmail OAuth
- automated Gmail sent/reply tracking
- student social profiles
- deployment
- backend ranking/search overhaul

## File Structure

Modify:
- `frontend/lib/types.ts` — align frontend company types with backend founder/logo/email fields.
- `backend/schemas.py` — add card-level founder fields if missing from `CompanyCard`.
- `frontend/components/FounderCard.tsx` — convert existing feed card into the shared founder preview card.
- `frontend/components/FloatingCards.tsx` — replace tiny floating cards with a landing preview rail wrapper or remove its old responsibilities after landing migration.
- `frontend/components/SearchBar.tsx` — support larger landing/search styling without hardcoding only one presentation.
- `frontend/components/SkillPicker.tsx` — replace popular-chip-first UI with professional combobox selector.
- `frontend/components/EmailWorkspace.tsx` — add copy draft and mailto controls.
- `frontend/app/page.tsx` — landing layout, hero sizing, search copy, carousel/rail, footer.
- `frontend/app/feed/page.tsx` — use shared cards and opportunity search language.
- `frontend/app/profile/page.tsx` — consume updated `SkillPicker` with no backend changes.
- `frontend/app/onboard/page.tsx` — consume updated `SkillPicker` with onboarding copy unchanged.
- `frontend/app/founder/[id]/page.tsx` — pass `brief.founder_email` into `EmailWorkspace`.
- `frontend/app/globals.css` — add restrained animation/rail styles if Tailwind utilities are insufficient.

Verification:
- `npm run lint` from `frontend/`
- `npm run build` from `frontend/`
- manual browser check for `/`, `/feed`, `/profile`, `/onboard`, `/founder/[id]`

---

### Task 1: Align Founder And Logo Types

**Files:**
- Modify: `frontend/lib/types.ts`
- Modify: `backend/schemas.py`

- [ ] **Step 1: Update `CompanyCard` frontend type**

In `frontend/lib/types.ts`, extend `CompanyCard` with fields already used by the backend/data model:

```ts
export interface CompanyCard {
  id: number;
  name: string;
  yc_batch: string | null;
  one_liner: string | null;
  industry: string | null;
  stage_detail: string | null;
  technical_level: string | null;
  team_size: number | null;
  reachability_score: string | null;
  small_logo_url: string | null;
  founder_name: string | null;
  founder_title: string | null;
  founder_avatar_url: string | null;
  need_tags: string[];
  match_score: number;
  rank_score: number;
}
```

- [ ] **Step 2: Update `CompanyBrief` frontend type**

In `frontend/lib/types.ts`, add missing brief fields:

```ts
export interface CompanyBrief {
  id: number;
  name: string;
  yc_batch: string | null;
  description: string | null;
  summary: string | null;
  one_liner: string | null;
  website: string | null;
  industry: string | null;
  stage: string | null;
  stage_detail: string | null;
  technical_level: string | null;
  team_size: number | null;
  need_tags: string[];
  specific_projects: string[];
  reachability_score: string | null;
  reachability_probability: number | null;
  founder_name: string | null;
  founder_title: string | null;
  founder_linkedin: string | null;
  founder_twitter: string | null;
  founder_avatar_url: string | null;
  founder_email: string | null;
  small_logo_url: string | null;
  slug: string | null;
  all_locations: string | null;
  tags: string[];
  industries: string[];
  match_score: number;
  guidance: Guidance | null;
}
```

- [ ] **Step 3: Add card-level founder fields to backend schema if absent**

In `backend/schemas.py`, update `CompanyCard` so `/companies` can power the redesigned cards:

```py
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
    need_tags: list[str] = []
    match_score: int = 0
    rank_score: float = 0.0
```

- [ ] **Step 4: Verify frontend typecheck through build**

Run:

```bash
cd frontend
npm run build
```

Expected: build may still fail from later unimplemented UI references if this task is batched with others, but there should be no TypeScript error about unknown founder/logo fields after the matching component updates are complete.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/types.ts backend/schemas.py
git commit -m "feat: expose founder card fields"
```

---

### Task 2: Redesign Shared Founder Card

**Files:**
- Modify: `frontend/components/FounderCard.tsx`

- [ ] **Step 1: Replace company-initial-first card logic with founder-first display values**

Use these derived values inside `FounderCard`:

```tsx
const founderName = company.founder_name || company.name;
const founderTitle = company.founder_title || "Founder";
const founderInitials = getInitials(founderName);
const companyInitials = getInitials(company.name);
const primaryTags = [
  company.industry,
  company.team_size ? `${company.team_size} people` : null,
  company.match_score > 0
    ? `${company.match_score} skill${company.match_score === 1 ? "" : "s"} match`
    : null,
].filter(Boolean);
```

- [ ] **Step 2: Render founder avatar with fallback**

Use a fixed avatar box so images do not shift layout:

```tsx
{company.founder_avatar_url ? (
  <img
    src={company.founder_avatar_url}
    alt={founderName}
    className="h-14 w-14 rounded-full object-cover"
  />
) : (
  <div className="flex h-14 w-14 items-center justify-center rounded-full bg-accent/10 font-display text-lg text-accent">
    {founderInitials}
  </div>
)}
```

- [ ] **Step 3: Render company logo on the right with fallback**

Use a fixed logo box:

```tsx
<div className="hidden h-12 w-12 flex-shrink-0 items-center justify-center rounded-lg border border-card-border bg-background sm:flex">
  {company.small_logo_url ? (
    <img
      src={company.small_logo_url}
      alt={`${company.name} logo`}
      className="h-8 w-8 object-contain"
    />
  ) : (
    <span className="text-xs font-semibold text-tertiary">
      {companyInitials}
    </span>
  )}
</div>
```

- [ ] **Step 4: Keep link/button behavior unchanged**

The component should still:
- render a `<button>` when `onClick` exists
- render a `Link href={`/founder/${company.id}`}` otherwise
- preserve `className="block w-full text-left"` for button mode

- [ ] **Step 5: Run lint**

Run:

```bash
cd frontend
npm run lint
```

Expected: PASS. If Next lint flags raw `<img>`, either use the existing project convention if already accepted, or add `/* eslint-disable @next/next/no-img-element */` at the top of this component and keep the implementation simple.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/FounderCard.tsx
git commit -m "feat: redesign founder preview card"
```

---

### Task 3: Build Landing Founder Preview Rail

**Files:**
- Modify: `frontend/components/FloatingCards.tsx`
- Modify: `frontend/app/page.tsx`
- Modify: `frontend/app/globals.css`

- [ ] **Step 1: Change landing fetch from 6 to 20 companies**

In `frontend/app/page.tsx`, replace both landing fetch limits:

```tsx
fetchCompanies({ limit: 20 })
```

Landing preview should show enough variety to justify the horizontal rail.

- [ ] **Step 2: Keep logged-out card click gated**

Preserve this behavior:

```tsx
const handleCardClick = () => {
  router.push("/login");
};
```

Cards should preview value but not reveal full briefs to logged-out users.

- [ ] **Step 3: Replace `FloatingCards` with a horizontal preview rail**

Convert `FloatingCards` into a rail component that maps up to 20 companies and calls `onCardClick`. The component should render a full-width section, not absolute scattered cards. Use `FounderCard` directly with its `onClick` prop so the markup does not create nested interactive elements.

```tsx
export default function FloatingCards({
  companies,
  onCardClick,
}: FloatingCardsProps) {
  return (
    <section className="relative z-10 mt-12 w-full overflow-hidden">
      <div className="mx-auto flex max-w-6xl gap-4 overflow-x-auto px-6 pb-4 [scrollbar-width:none]">
        {companies.slice(0, 20).map((company) => (
          <div
            key={company.id}
            className="w-[320px] flex-shrink-0"
          >
            <FounderCard company={company} onClick={() => onCardClick?.(company)} />
          </div>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Resize landing hero**

In `frontend/app/page.tsx`, change the hero from `text-5xl md:text-6xl` to a smaller scale:

```tsx
<h1 className="max-w-2xl font-display text-4xl leading-tight text-primary md:text-5xl">
  You don&apos;t need connections. You need the right founder.
</h1>
```

- [ ] **Step 5: Elongate landing search**

Set the landing search wrapper to a wider max width:

```tsx
<div className="mt-8 w-full max-w-3xl">
  <SearchBar
    onSearch={handleSearch}
    onSubmit={handleSubmit}
    placeholder="Search AI automation, data pipelines, healthcare, React..."
  />
</div>
```

- [ ] **Step 6: Add restrained decorative shapes**

Add 3-4 non-interactive shapes inside the landing `<main>` behind content:

```tsx
<div className="pointer-events-none absolute left-10 top-24 h-16 w-28 rounded-full border border-card-border/70" />
<div className="pointer-events-none absolute right-16 top-32 h-20 w-20 rounded-full border border-accent/20" />
<div className="pointer-events-none absolute bottom-28 left-1/4 h-10 w-24 rounded-full bg-accent/5" />
```

Keep them subtle; they should not obscure cards or text.

- [ ] **Step 7: Add footer contact links**

At the bottom of landing, add a simple footer row:

```tsx
<footer className="relative z-10 mt-20 flex flex-wrap items-center justify-center gap-4 pb-10 text-sm text-tertiary">
  <a href="mailto:hello@reach.local" className="hover:text-primary">Contact</a>
  <a href="https://github.com/" target="_blank" rel="noopener noreferrer" className="hover:text-primary">GitHub</a>
  <a href="https://www.linkedin.com/" target="_blank" rel="noopener noreferrer" className="hover:text-primary">LinkedIn</a>
</footer>
```

Replace the sample social URLs with the actual project/user URLs during implementation if available in project notes.

- [ ] **Step 8: Run lint and build**

Run:

```bash
cd frontend
npm run lint
npm run build
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add frontend/app/page.tsx frontend/components/FloatingCards.tsx frontend/app/globals.css
git commit -m "feat: refresh landing founder previews"
```

---

### Task 4: Make SearchBar Presentation Flexible

**Files:**
- Modify: `frontend/components/SearchBar.tsx`

- [ ] **Step 1: Add `size` prop**

Extend props:

```tsx
interface SearchBarProps {
  onSearch: (query: string) => void;
  onSubmit?: (query: string) => void;
  placeholder?: string;
  debounceMs?: number;
  initialValue?: string;
  size?: "default" | "large";
}
```

- [ ] **Step 2: Apply size-specific classes**

Use class composition:

```tsx
const inputClass =
  size === "large"
    ? "w-full rounded-xl border border-card-border bg-card px-6 py-4 text-base text-primary shadow-card placeholder:text-tertiary focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20 md:text-lg"
    : "w-full rounded-xl border border-card-border bg-card px-4 py-3 text-sm text-primary shadow-card placeholder:text-tertiary focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20";
```

- [ ] **Step 3: Use `size="large"` on landing only**

In `frontend/app/page.tsx`:

```tsx
<SearchBar
  onSearch={handleSearch}
  onSubmit={handleSubmit}
  placeholder="Search AI automation, data pipelines, healthcare, React..."
  size="large"
/>
```

- [ ] **Step 4: Run lint**

Run:

```bash
cd frontend
npm run lint
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/SearchBar.tsx frontend/app/page.tsx
git commit -m "feat: add flexible search sizing"
```

---

### Task 5: Refresh Feed Cards And Opportunity Search

**Files:**
- Modify: `frontend/app/feed/page.tsx`
- Modify: `frontend/components/FilterBar.tsx`

- [ ] **Step 1: Change search copy**

In feed, change:

```tsx
placeholder="Search founders..."
```

to:

```tsx
placeholder="Search AI automation, data pipelines, healthcare, React..."
```

- [ ] **Step 2: Expand client-side search fields**

Replace feed filter logic with:

```tsx
const normalizedQuery = searchQuery.trim().toLowerCase();
const filtered = normalizedQuery
  ? companies.filter((c) => {
      const fields = [
        c.name,
        c.founder_name,
        c.one_liner,
        c.industry,
        c.stage_detail,
        c.technical_level,
        ...(c.need_tags ?? []),
      ];
      return fields.some((field) =>
        field?.toLowerCase().includes(normalizedQuery),
      );
    })
  : companies;
```

- [ ] **Step 3: Keep reachability and industry filters**

Do not remove `FilterBar`; it remains useful for explicit filtering. Do not rename backend `industry` query parameter.

- [ ] **Step 4: Improve empty state copy**

Use:

```tsx
No startups match that search yet. Try a skill, industry, or product area.
```

- [ ] **Step 5: Run lint and build**

Run:

```bash
cd frontend
npm run lint
npm run build
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/app/feed/page.tsx frontend/components/FilterBar.tsx
git commit -m "feat: refresh feed search and cards"
```

---

### Task 6: Replace SkillPicker With Combobox Selector

**Files:**
- Modify: `frontend/components/SkillPicker.tsx`
- Verify consumers: `frontend/app/profile/page.tsx`, `frontend/app/onboard/page.tsx`

- [ ] **Step 1: Preserve public component API**

Keep this interface so profile and onboarding keep working:

```tsx
interface SkillPickerProps {
  selected: string[];
  onChange: (skills: string[]) => void;
  max?: number;
}
```

- [ ] **Step 2: Replace popular chip wall with combobox state**

Use these states:

```tsx
const [searchQuery, setSearchQuery] = useState("");
const [open, setOpen] = useState(false);
```

Compute suggestions directly:

```tsx
const normalized = searchQuery.trim().toLowerCase();
const suggestions = (normalized ? ALL_SKILLS : POPULAR_SKILLS)
  .filter((skill) => !selected.includes(skill))
  .filter((skill) => !normalized || skill.toLowerCase().includes(normalized))
  .slice(0, 12);
```

- [ ] **Step 3: Add select and remove helpers**

```tsx
function addSkill(skill: string) {
  if (selected.includes(skill)) return;
  onChange([...selected, skill]);
  setSearchQuery("");
  setOpen(false);
}

function removeSkill(skill: string) {
  onChange(selected.filter((s) => s !== skill));
}
```

- [ ] **Step 4: Render input with dropdown button**

The top control should be one clean input row:

```tsx
<div className="relative">
  <div className="flex rounded-xl border border-card-border bg-card shadow-card focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/20">
    <input
      type="text"
      value={searchQuery}
      onFocus={() => setOpen(true)}
      onChange={(e) => {
        setSearchQuery(e.target.value);
        setOpen(true);
      }}
      placeholder="Search skills..."
      className="min-w-0 flex-1 rounded-l-xl bg-transparent px-4 py-3 text-sm text-primary placeholder:text-tertiary focus:outline-none"
    />
    <button
      type="button"
      onClick={() => setOpen((value) => !value)}
      className="border-l border-card-border px-3 text-tertiary hover:text-primary"
      aria-label="Toggle skill suggestions"
    >
     ⌄
    </button>
  </div>
</div>
```

If using the down-arrow glyph creates lint/encoding concerns, use ASCII text `v`.

- [ ] **Step 5: Render dropdown suggestions**

```tsx
{open && suggestions.length > 0 && (
  <div className="absolute z-20 mt-2 max-h-64 w-full overflow-y-auto rounded-xl border border-card-border bg-card p-1 shadow-card-hover">
    {suggestions.map((skill) => (
      <button
        key={skill}
        type="button"
        onClick={() => addSkill(skill)}
        className="block w-full rounded-lg px-3 py-2 text-left text-sm text-secondary hover:bg-background hover:text-primary"
      >
        {skill}
      </button>
    ))}
  </div>
)}
```

- [ ] **Step 6: Render selected pills below input**

```tsx
{selected.length > 0 && (
  <div className="flex flex-wrap gap-2">
    {selected.map((skill) => (
      <span
        key={skill}
        className="flex items-center gap-1.5 rounded-full bg-accent/10 px-3 py-1 text-sm text-accent"
      >
        {skill}
        <button
          type="button"
          onClick={() => removeSkill(skill)}
          className="text-accent/70 hover:text-accent"
          aria-label={`Remove ${skill}`}
        >
          x
        </button>
      </span>
    ))}
  </div>
)}
```

- [ ] **Step 7: Preserve selected-count warning**

```tsx
<p className={`text-sm ${selected.length > max ? "text-reach-med" : "text-tertiary"}`}>
  {selected.length} of {max} selected
</p>
```

- [ ] **Step 8: Run lint and build**

Run:

```bash
cd frontend
npm run lint
npm run build
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add frontend/components/SkillPicker.tsx frontend/app/profile/page.tsx frontend/app/onboard/page.tsx
git commit -m "feat: redesign skill picker combobox"
```

---

### Task 7: Add Copy And Mailto To EmailWorkspace

**Files:**
- Modify: `frontend/components/EmailWorkspace.tsx`
- Modify: `frontend/app/founder/[id]/page.tsx`

- [ ] **Step 1: Pass founder email from brief page**

In `frontend/app/founder/[id]/page.tsx`, replace:

```tsx
<EmailWorkspace
  founderEmail={null}
  companyName={brief.name}
/>
```

with:

```tsx
<EmailWorkspace
  founderEmail={brief.founder_email}
  companyName={brief.name}
/>
```

- [ ] **Step 2: Add copied state**

In `EmailWorkspace`:

```tsx
const [copied, setCopied] = useState(false);
```

- [ ] **Step 3: Add copy handler**

```tsx
async function handleCopy() {
  if (!body.trim()) return;
  try {
    await navigator.clipboard.writeText(body);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  } catch {
    setCopied(false);
  }
}
```

- [ ] **Step 4: Keep mailto simple**

Use the existing mailto behavior, but label honestly:

```tsx
const mailtoHref = founderEmail
  ? `mailto:${founderEmail}?subject=${encodeURIComponent(`Quick question - ${companyName}`)}&body=${encodeURIComponent(body)}`
  : undefined;
```

Use ASCII hyphen in the subject.

- [ ] **Step 5: Render copy and mailto controls**

Replace the current single action area with:

```tsx
<div className="flex flex-wrap items-center justify-end gap-2">
  <button
    type="button"
    onClick={handleCopy}
    disabled={!body.trim()}
    className="rounded-lg border border-card-border bg-card px-4 py-2 text-sm font-medium text-primary transition-colors hover:bg-background disabled:cursor-not-allowed disabled:opacity-40"
  >
    {copied ? "Copied" : "Copy draft"}
  </button>

  {founderEmail ? (
    <a
      href={mailtoHref}
      className="rounded-lg bg-accent px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-accent/90"
    >
      Open email
    </a>
  ) : (
    <span className="text-sm text-tertiary">
      Email not available yet
    </span>
  )}
</div>
```

- [ ] **Step 6: Run lint and build**

Run:

```bash
cd frontend
npm run lint
npm run build
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/components/EmailWorkspace.tsx 'frontend/app/founder/[id]/page.tsx'
git commit -m "feat: add email draft copy workflow"
```

---

### Task 8: Manual UX Verification

**Files:**
- No source edits unless verification finds issues.

- [ ] **Step 1: Start frontend dev server**

Run:

```bash
cd frontend
npm run dev
```

Expected: Next dev server starts on `http://localhost:3000` or another available port.

- [ ] **Step 2: Start backend if not already running**

Run from repo root:

```bash
uvicorn backend.main:app --reload
```

Expected: FastAPI starts on `http://127.0.0.1:8000`.

- [ ] **Step 3: Check landing**

Open `/` and verify:
- hero is smaller than before
- search bar is wide
- founder preview cards show founder/avatar/company data when available
- clicking a card while logged out sends the user to `/login`
- footer links are visible and not overlapping content

- [ ] **Step 4: Check feed**

Open `/feed` as an authenticated user and verify:
- cards show founder name, role/company metadata, logo/avatar fallback
- search finds need tags such as `React`, `data`, and industries such as `healthcare`
- load more remains hidden during active search and works when search is empty

- [ ] **Step 5: Check profile and onboarding skill picker**

Open `/profile` and `/onboard` as applicable and verify:
- input opens suggestions
- typing filters skills
- dropdown button opens popular suggestions
- selected skills render as removable pills
- profile auto-save still fires after changes
- onboarding continue remains disabled until 3 skills are selected

- [ ] **Step 6: Check founder brief email workspace**

Open a founder brief and verify:
- copy button is disabled for an empty draft
- copy button copies non-empty draft text
- founder email unavailable state is clear when `founder_email` is null
- if a test company has `founder_email`, mailto opens the user's email client

- [ ] **Step 7: Final verification**

Run:

```bash
cd frontend
npm run lint
npm run build
```

Expected: PASS.

- [ ] **Step 8: Commit fixes if manual verification required edits**

```bash
git add frontend
git commit -m "fix: polish frontend overhaul interactions"
```

Only commit if verification caused additional source changes.

---

## Self-Review

Spec coverage:
- Claude plan item 1, card redesign: covered by Tasks 1-2.
- Claude plan item 2, landing overhaul: covered by Tasks 3-4.
- Claude plan item 3, feed search: covered by Task 5, adjusted from industry-only to opportunity search.
- Claude plan item 4, profile skills combobox: covered by Task 6.
- Claude plan item 5, custom SMTP: intentionally excluded as Track B launch readiness.
- Claude plan item 6, copy-to-clipboard and mailto: covered by Task 7.

Ambiguity resolved:
- Full scroll hijacking is not implemented. The plan uses a horizontal preview rail that preserves normal scrolling.
- Student social profiles are not implemented.
- Gmail OAuth is not implemented.
- Search is still frontend/client-side for this pass; backend search can be a later plan.

Verification:
- Frontend verification relies on `npm run lint`, `npm run build`, and manual browser checks.
- Backend verification for `CompanyCard` schema can be covered by existing API tests in a later backend-test cleanup plan, because known auth test drift already exists in the project state.
