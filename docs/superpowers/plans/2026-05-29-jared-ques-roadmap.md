# Jared's Questions — Prioritized Roadmap

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Address all remaining items from `jared_ques.txt`, ordered by impact and dependency chain.

**Architecture:** Six workstreams, some sequential (pipeline must run before email UX matters), some parallel (frontend polish is independent of data work). Tasks are grouped by priority tier.

**Tech Stack:** Python pipeline scripts, Next.js/React frontend, FastAPI backend, Supabase, Ollama (Qwen3 4B on Windows RTX 3060)

---

## Priority Map

| Tier | What | Why |
|------|------|-----|
| **P0** | Re-scrape founders + run email resolution + push to Supabase | Unlocks the entire email feature; also fixes missing avatars |
| **P1** | Frontend loading states + page transitions | Currently unusable UX — long blank screens on every navigation |
| **P2** | Reachability label text + founder image debug | Small frontend fixes, high visual impact |
| **P3** | Bio guidance + resume upload + portfolio influence on emails | Improves email personalization quality |
| **P4** | Company funding data enrichment | New data source, enriches matching but not blocking anything |
| **P5** | Full codebase cleanup audit | Cosmetic — no user impact, but keeps repo healthy |

---

## P0: Re-scrape & Email Resolution Pipeline

> **Context:** `resolve_emails.py`, `scrape_founders.py`, and `supabase_write.py` are all built and tested. They just need to be run. This is the single biggest blocker — without emails in the DB, the email feature is dead.

### Task 1: Re-scrape founder data (fixes avatars + bios)

**Files:**
- Run: `backend/pipeline/scrape_founders.py`
- Input: `data/raw_companies.json` (1,517 companies)
- Output: `data/founders.json`

**Why re-scrape:** The current `founders.json` has missing `founder_avatar_url` for some founders. A fresh scrape will pick up any YC page updates (new avatars, updated bios, corrected `has_email` flags).

- [ ] **Step 1: Back up current founders data**

```bash
cp data/founders.json data/founders_backup_20260529.json
```

- [ ] **Step 2: Delete existing founders.json to force full re-scrape**

```bash
rm data/founders.json
```

The script has resume support — if you want incremental, keep the file. For a clean re-scrape, delete it.

- [ ] **Step 3: Run the founder scraper**

```bash
cd /Users/jshum/Desktop/reach
python -m backend.pipeline.scrape_founders
```

Expected: ~25 minutes (1,517 companies x 1s delay). Logs every 50 companies. Saves progress every 50 — safe to interrupt and resume.

- [ ] **Step 4: Verify output**

```bash
python -c "
import json
with open('data/founders.json') as f:
    founders = json.load(f)
total = len(founders)
has_name = sum(1 for f in founders if f.get('founder_name'))
has_avatar = sum(1 for f in founders if f.get('founder_avatar_url'))
has_email_flag = sum(1 for f in founders if f.get('has_email'))
has_bio = sum(1 for f in founders if f.get('founder_bio'))
print(f'Total: {total}')
print(f'With name: {has_name}')
print(f'With avatar: {has_avatar}')
print(f'With has_email flag: {has_email_flag}')
print(f'With bio: {has_bio}')
"
```

Expected: ~1,500+ with name, significantly more avatars than before.

- [ ] **Step 5: Compare avatar coverage to old data**

```bash
python -c "
import json
with open('data/founders_backup_20260529.json') as f:
    old = {e['company_name']: e for e in json.load(f)}
with open('data/founders.json') as f:
    new = {e['company_name']: e for e in json.load(f)}
old_avatars = sum(1 for v in old.values() if v.get('founder_avatar_url'))
new_avatars = sum(1 for v in new.values() if v.get('founder_avatar_url'))
print(f'Old avatars: {old_avatars}')
print(f'New avatars: {new_avatars}')
print(f'Delta: +{new_avatars - old_avatars}')
"
```

---

### Task 2: Run email resolution cascade

**Files:**
- Run: `backend/pipeline/resolve_emails.py`
- Input: `data/founders.json`, `data/raw_companies.json`
- Output: `data/resolved_emails.json`

- [ ] **Step 1: Back up any existing email data**

```bash
[ -f data/resolved_emails.json ] && cp data/resolved_emails.json data/resolved_emails_backup_20260529.json
```

- [ ] **Step 2: Run the email resolver**

```bash
cd /Users/jshum/Desktop/reach
python -m backend.pipeline.resolve_emails
```

Expected: Processes only founders with `has_email=True`. Takes ~1s per founder (website scrape + SMTP). Saves progress every 25. Safe to interrupt and resume.

- [ ] **Step 3: Verify output**

```bash
python -c "
import json
with open('data/resolved_emails.json') as f:
    emails = json.load(f)
total = len(emails)
resolved = sum(1 for e in emails if e.get('founder_email'))
website = sum(1 for e in emails if e.get('email_source') == 'website')
pattern = sum(1 for e in emails if e.get('email_source') == 'pattern')
print(f'Total processed: {total}')
print(f'Resolved: {resolved} ({100*resolved/total:.1f}%)')
print(f'  Website scrape: {website}')
print(f'  Pattern+SMTP: {pattern}')
print(f'  Failed: {total - resolved}')
"
```

---

### Task 3: Push updated data to Supabase

**Files:**
- Run: `backend/pipeline/supabase_write.py`
- Input: All 6 data JSON files
- Output: Supabase `companies` table updated

- [ ] **Step 1: Verify all input files exist**

```bash
ls -la data/enriched_companies.json data/reachability_scores.json data/raw_companies.json data/founders.json data/resolved_emails.json data/curated_tags.json
```

All 6 must exist.

- [ ] **Step 2: Run the Supabase writer**

```bash
cd /Users/jshum/Desktop/reach
python -m backend.pipeline.supabase_write
```

Expected: Upserts ~1,519 companies in batches of 500. Should complete in under a minute.

- [ ] **Step 3: Spot-check in Supabase**

Verify a few companies now have `founder_email`, `email_source`, and `email_confidence` populated. Also check that `founder_avatar_url` is updated for previously-missing entries.

---

## P1: Frontend Loading States & Page Transitions

> **Context:** Currently, navigating between pages shows blank screens for several seconds while data loads. The feed page and landing page are the worst offenders.

### Task 4: Add loading skeletons to the feed page

**Files:**
- Modify: `frontend/app/feed/page.tsx`
- Create: `frontend/components/SkeletonCard.tsx`

- [ ] **Step 1: Create a SkeletonCard component**

A pulsing placeholder card that matches FounderCard dimensions. Use Tailwind's `animate-pulse` with gray blocks for avatar, title, tags.

```tsx
// frontend/components/SkeletonCard.tsx
export default function SkeletonCard() {
  return (
    <div className="rounded-xl border border-white/5 bg-white/[0.02] p-5 space-y-4 animate-pulse">
      <div className="flex items-center gap-3">
        <div className="w-11 h-11 rounded-full bg-white/10" />
        <div className="space-y-2 flex-1">
          <div className="h-4 bg-white/10 rounded w-2/3" />
          <div className="h-3 bg-white/10 rounded w-1/3" />
        </div>
      </div>
      <div className="space-y-2">
        <div className="h-3 bg-white/10 rounded w-full" />
        <div className="h-3 bg-white/10 rounded w-4/5" />
      </div>
      <div className="flex gap-2">
        <div className="h-6 bg-white/10 rounded-full w-16" />
        <div className="h-6 bg-white/10 rounded-full w-20" />
        <div className="h-6 bg-white/10 rounded-full w-14" />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Show skeleton grid while feed is loading**

In `feed/page.tsx`, replace the empty loading state with a grid of 8 SkeletonCards:

```tsx
{loading && companies.length === 0 && (
  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
    {Array.from({ length: 8 }).map((_, i) => (
      <SkeletonCard key={i} />
    ))}
  </div>
)}
```

- [ ] **Step 3: Add skeleton to the landing page preview cards**

In `page.tsx`, show skeleton cards while the initial preview companies load.

- [ ] **Step 4: Test both pages — verify skeletons appear during load, then swap to real cards**

- [ ] **Step 5: Commit**

```bash
git add frontend/components/SkeletonCard.tsx frontend/app/feed/page.tsx frontend/app/page.tsx
git commit -m "feat: add skeleton loading states to feed and landing pages"
```

---

### Task 5: Smooth page transitions

**Files:**
- Modify: `frontend/app/globals.css`
- Modify: `frontend/app/layout.tsx` (if needed)

- [ ] **Step 1: Add a fade-in transition to page content**

In `globals.css`, add a subtle fade-in animation:

```css
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.page-enter {
  animation: fadeIn 0.2s ease-out;
}
```

- [ ] **Step 2: Apply the animation class to main content wrappers**

Wrap the main content in feed, brief, profile, and tracker pages with the `page-enter` class.

- [ ] **Step 3: Test navigation between pages — transitions should feel smooth, not jarring**

- [ ] **Step 4: Commit**

```bash
git add frontend/app/globals.css frontend/app/feed/page.tsx frontend/app/page.tsx
git commit -m "feat: add smooth page transition animations"
```

---

## P2: Small Visual Fixes

### Task 6: Change reachability label to full text

**Files:**
- Modify: `frontend/components/FounderCard.tsx`
- Modify: `frontend/components/FounderBrief.tsx`

- [ ] **Step 1: In FounderCard.tsx, change the reachability badge text**

Find where the badge displays "high", "medium", or "low" and change to:

```
"high"   → "High Reachability"
"medium" → "Medium Reachability"
"low"    → "Low Reachability"
```

- [ ] **Step 2: Do the same in FounderBrief.tsx**

- [ ] **Step 3: Verify the badge still fits — may need to adjust padding or font size**

- [ ] **Step 4: Commit**

```bash
git add frontend/components/FounderCard.tsx frontend/components/FounderBrief.tsx
git commit -m "feat: show full reachability label text on founder cards"
```

---

### Task 7: Debug missing founder profile pictures

**Files:**
- Modify: `frontend/components/FounderCard.tsx` (if needed)

- [ ] **Step 1: After re-scrape (Task 1), check how many founders still lack avatars**

```bash
python -c "
import json
with open('data/founders.json') as f:
    founders = json.load(f)
missing = [f['company_name'] for f in founders if f.get('founder_name') and not f.get('founder_avatar_url')]
print(f'{len(missing)} founders with name but no avatar')
for name in missing[:10]:
    print(f'  - {name}')
"
```

- [ ] **Step 2: For remaining missing avatars, check if the YC pages actually have images**

Manually spot-check 3-5 of the missing companies at `ycombinator.com/companies/{slug}` to determine if this is a scraper issue or genuinely missing data.

- [ ] **Step 3: If scraper is missing available avatars, fix `parse_founders_from_html`**

Possible issues:
- Avatar URL field name changed on YC's end
- `avatar_thumb_url` is empty but `avatar_url` exists
- S3 signature stripping breaks the URL

- [ ] **Step 4: If avatars are genuinely missing, the initials fallback is already in place — no further action needed**

- [ ] **Step 5: Commit any scraper fixes**

```bash
git add backend/pipeline/scrape_founders.py
git commit -m "fix: improve avatar URL extraction from YC pages"
```

---

## P3: Email Personalization Improvements

### Task 8: Add bio writing guidance to profile page

**Files:**
- Modify: `frontend/app/profile/page.tsx`

- [ ] **Step 1: Add helper text below the bio textarea**

Add a collapsible "Tips for a strong bio" section with concrete guidance:

```tsx
<details className="text-xs text-white/40 mt-2">
  <summary className="cursor-pointer hover:text-white/60">Tips for a strong bio</summary>
  <ul className="mt-2 space-y-1 pl-4 list-disc">
    <li>Mention what you're building or learning right now</li>
    <li>Include a specific technical skill (e.g. "I've been writing Python for 2 years")</li>
    <li>Say what kind of problems excite you, not just what you're good at</li>
    <li>Keep it under 3 sentences — founders skim</li>
  </ul>
</details>
```

- [ ] **Step 2: Add similar guidance for the projects field**

```tsx
<details className="text-xs text-white/40 mt-2">
  <summary className="cursor-pointer hover:text-white/60">What makes a good project description?</summary>
  <ul className="mt-2 space-y-1 pl-4 list-disc">
    <li>Name a specific project, not just "I've done some projects"</li>
    <li>Mention the tech stack or approach</li>
    <li>Include a link if it's deployed or on GitHub</li>
    <li>Focus on 1-2 best projects, not a long list</li>
  </ul>
</details>
```

- [ ] **Step 3: Verify tips render correctly and collapse/expand works**

- [ ] **Step 4: Commit**

```bash
git add frontend/app/profile/page.tsx
git commit -m "feat: add bio and project writing guidance to profile page"
```

---

### Task 9: Verify resume_url and portfolio_url feed into email generation

**Files:**
- Read: `backend/email/prompt.py`
- Read: `backend/email/generate.py`
- Read: `frontend/components/EmailWorkspace.tsx`

**Status from code review:** `generate.py` already accepts `portfolio_url`, `github_url`, and `resume_url` as parameters and passes them into the prompt template. The prompt template includes them in the student context section. `EmailWorkspace.tsx` passes the user's profile data to the generate endpoint.

- [ ] **Step 1: Verify the frontend sends these fields**

Read `EmailWorkspace.tsx` and trace the API call to `/email/generate`. Confirm `portfolio_url`, `github_url`, and `resume_url` are included in the request body.

- [ ] **Step 2: Verify the prompt actually uses them**

Read `prompt.py` and confirm the template includes lines like:
- "Portfolio: {portfolio_url}" (when present)
- "GitHub: {github_url}" (when present)
- "Resume: {resume_url}" (when present)

- [ ] **Step 3: If any field is missing from the chain, add it**

Trace the full path: profile page → API call → router → generate function → prompt template. Fix any gaps.

- [ ] **Step 4: Test with a real profile that has all fields populated — generate a draft and verify the email references the links**

- [ ] **Step 5: Commit if changes were needed**

```bash
git add -A
git commit -m "fix: ensure all profile links feed into email generation"
```

---

### Task 10: Add resume file upload (stretch)

**Files:**
- Modify: `frontend/app/profile/page.tsx`
- Create: `backend/routers/upload.py` (new endpoint)
- Modify: `backend/main.py` (register router)

> **Note:** This is a stretch goal. The current `resume_url` field (paste a link) works fine for MVP. File upload adds complexity (storage backend, file size limits, parsing). Consider deferring until after launch unless Jared specifically wants it.

- [ ] **Step 1: Decide on storage backend**

Options:
- **Supabase Storage** (simplest — already using Supabase)
- **S3 bucket** (more control)
- **Just keep the URL field** (users paste Google Drive / Dropbox links)

- [ ] **Step 2: If proceeding with Supabase Storage, create a `resumes` bucket**

- [ ] **Step 3: Add upload endpoint**

```python
# backend/routers/upload.py
@router.post("/upload/resume")
async def upload_resume(file: UploadFile, user=Depends(get_current_user)):
    # Validate: PDF only, max 5MB
    # Upload to Supabase Storage
    # Update user's resume_url
    # Return URL
```

- [ ] **Step 4: Add upload UI to profile page**

Replace the text input with a file drop zone + the existing URL input as fallback.

- [ ] **Step 5: Test upload + verify URL is stored and used in email generation**

- [ ] **Step 6: Commit**

---

## P4: Company Funding Data Enrichment

### Task 11: Research funding data sources

**Files:** None (research task)

> **Note:** This requires a new data source. YC's Algolia API does not include funding amounts. Options to investigate:

- [ ] **Step 1: Check if YC company pages include funding info**

Manually check 5 YC company pages for funding data in the HTML/JSON. The scraper already parses the page — funding might be there but not extracted.

- [ ] **Step 2: Evaluate external APIs**

Options:
- **Crunchbase API** — most comprehensive, but paid ($)
- **PitchBook** — institutional, expensive
- **OpenAI web search** — could extract from news articles, unreliable
- **Manual enrichment via LLM** — use the existing Ollama pipeline to extract funding from company descriptions (some mention "raised $X")

- [ ] **Step 3: If funding is available from YC pages, add extraction to `scrape_founders.py`**

- [ ] **Step 4: If external API needed, evaluate cost vs value and report back to Jared before proceeding**

- [ ] **Step 5: If proceeding, add `funding_amount` and `funding_stage` fields to the pipeline**

Modify: `backend/pipeline/supabase_write.py` (add columns), `backend/pipeline/enrich.py` (extract from descriptions), database schema.

---

## P5: Codebase Cleanup Audit

### Task 12: Audit and report unused/dirty files

**Files:** Entire repo

> **Important:** Do NOT delete anything without reporting to Jared first. This is an audit, not a cleanup.

- [ ] **Step 1: Identify unused backend files**

Check for:
- Files in `backend/` not imported by any router or pipeline script
- Old test files testing removed functionality
- Duplicate or superseded pipeline scripts
- `backend/ml/` remnants (XGBoost model files, training scripts — replaced by rule-based scoring)

- [ ] **Step 2: Identify unused frontend files**

Check for:
- Components not imported by any page
- Unused API function exports in `frontend/lib/`
- Old page routes that are dead ends
- Unused assets in `frontend/public/`

- [ ] **Step 3: Identify config/data bloat**

Check for:
- Backup JSON files in `data/`
- Old plan documents that are fully completed
- Unused environment variables
- Duplicate dependencies in `requirements.txt`

- [ ] **Step 4: Compile report and present to Jared**

Format:
```
SAFE TO DELETE (no references found):
  - path/to/file.py — reason

PROBABLY UNUSED (verify before deleting):
  - path/to/file.py — reason

KEEP (referenced but may look unused):
  - path/to/file.py — reason
```

- [ ] **Step 5: After Jared approves, delete approved files and commit**

```bash
git add -A
git commit -m "chore: remove unused files per cleanup audit"
```

---

## Execution Order

```
Week 1 (immediate):
  Task 1  → Task 2  → Task 3     (pipeline: scrape → resolve → push)
  Task 4  + Task 5                (frontend loading, can run in parallel with pipeline)
  Task 6                          (reachability labels, quick fix)

Week 1 (after pipeline completes):
  Task 7                          (debug remaining missing avatars)
  Task 9                          (verify email field chain)

Week 2:
  Task 8                          (bio guidance)
  Task 11                         (funding research)
  Task 12                         (cleanup audit)

Deferred:
  Task 10                         (resume upload — decide after MVP feedback)
```

---

## Dependencies

```
Task 1 (scrape) ──→ Task 2 (emails) ──→ Task 3 (push to Supabase)
                                              │
Task 7 (avatar debug) ←──────────────────────┘
Task 9 (verify email fields) ←───────────────┘

Task 4 (skeletons)    ── independent, do anytime
Task 5 (transitions)  ── independent, do anytime
Task 6 (labels)       ── independent, do anytime
Task 8 (bio guidance) ── independent, do anytime
Task 11 (funding)     ── independent, needs research first
Task 12 (cleanup)     ── independent, do anytime
```
