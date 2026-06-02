# Profile Inputs Overhaul — Design Spec

**Date:** 2026-06-02
**Status:** Approved
**Scope:** Spec 1 of 2 for the email generation overhaul. This spec covers collecting better user data. Spec 2 (email generation overhaul) will consume these inputs.

## Problem

The email generation prompt receives weak user data. Bio is freeform and usually vague or empty (falls back to "High school student"). Projects are a single unstructured textarea that produces unreliable descriptions. Resume/portfolio URLs are just links the LLM can't read. The result: generic emails that don't represent the student.

## Solution

Replace freeform inputs with structured collection that guarantees useful content for the LLM.

---

## 1. Structured Bio Builder

### Current state
Single freeform textarea, optional, falls back to "High school student" if empty.

### New design
Three focused input fields on the profile page:

| Field | Label | Placeholder | Required |
|-------|-------|-------------|----------|
| `bio_grade` | "Grade & School" | "e.g. Junior at Lincoln High" | Yes |
| `bio_building` | "What are you building or learning?" | "e.g. Writing Python scrapers, learning React" | Yes |
| `bio_interests` | "What problems interest you?" | "e.g. How startups use NLP to process messy data" | Yes |

On save, concatenate: `"I'm a {bio_grade}. {bio_building}. I'm interested in {bio_interests}."`

Store the concatenated string in the existing `bio` column — no schema change. The three fields are frontend-only state, populated by splitting the bio on load (or showing a fallback textarea for existing users who already have a freeform bio).

### Soft validation
Yellow warning (not a blocker) if any field < 5 words. Guidance text above the section: "Founders skim — make each line specific, not generic."

Implementation: frontend-only. A small set of ~50-100 common tech terms (Python, React, ML, data, design, Figma, etc.) checked against the bio_building and bio_interests fields. If none appear, show: "Try mentioning a specific tool, language, or project." No LLM calls.

### Generation gate
If `bio` is empty (all three fields blank), the "Generate draft" button on the email workspace is disabled with tooltip: "Fill in your bio on your profile first."

---

## 2. GitHub Repo Input + Summarization

### Frontend
Up to 3 repo URL fields on the profile page. Each field has:
- Text input for the URL (placeholder: "https://github.com/username/project")
- After pasting, a "Summarize" button triggers the backend
- Shows the stored summary below the input once generated
- A remove button to clear a slot

Guidance text above the repo section: "Projects that relate to a founder's domain make your email stand out. A trading bot for a fintech founder, a scraper for a data company — that's what gets replies."

### Backend — new endpoint: `POST /me/repos`

Request body: `{ "repo_url": "https://github.com/user/project" }`

Flow:
1. Validate URL is a GitHub repo format (`github.com/{owner}/{repo}`)
2. Check user hasn't exceeded 3 stored repos
3. Check user hasn't exceeded 10 lifetime summarizations (`summarization_count` column on users table)
4. Fetch via GitHub API (no auth needed for public repos):
   - `GET /repos/{owner}/{repo}` → description, language, stars, fork status
   - `GET /repos/{owner}/{repo}/readme` → README content (base64 decoded)
5. Quality check (no LLM):
   - No README or README < 50 chars → return 400: "This repo doesn't have a README. Add one so founders know what it does."
   - Only a fork with 0 commits beyond upstream → return 400: "This looks like an unmodified fork."
   - No description on repo → soft warning in response (not a blocker)
6. Haiku call to summarize: "Summarize this GitHub project in 2-3 sentences for a cold email. Focus on what it does, the tech used, and what's impressive about it." Input: README truncated to ~2000 chars. Cost: ~$0.001 per call.
7. Increment `summarization_count`, store summary in `user_repos` table.

Response: `{ "id": int, "repo_url": str, "repo_name": str, "summary": str, "language": str, "stars": int, "warning": str | null }`

### Backend — delete endpoint: `DELETE /me/repos/{id}`

Removes a repo slot. Does NOT decrement the summarization count.

### Backend — list endpoint: `GET /me/repos`

Returns all repos for the authenticated user (max 3).

### Rate limits
- Max 3 stored repos per user (enforced in POST endpoint)
- Max 10 lifetime summarizations per user (enforced in POST endpoint, checked via `summarization_count`)
- When limit hit, return 400 with clear message: "You've used all 10 project summarizations."

---

## 3. Resume PDF Upload

### Frontend
On the profile page, a file upload area:
- Drag-and-drop zone or click-to-browse, accepts `.pdf` only
- Max file size: 2MB
- Shows current filename + "Remove" button if uploaded
- Label: "Resume (PDF)" with helper text: "Upload your resume — it'll be linked in your email signature."

### Backend — new endpoint: `POST /me/resume`

Request: multipart form data with the PDF file.

Flow:
1. Validate file is PDF (check content type + `.pdf` extension)
2. Validate size ≤ 2MB
3. Upload to Supabase Storage bucket `resumes` with path `{user_id}/resume.pdf` (overwrites previous)
4. Get public URL from Supabase Storage
5. Store URL in existing `resume_url` column on users table

Response: `{ "resume_url": str }`

### Backend — delete endpoint: `DELETE /me/resume`

Deletes file from Supabase Storage, sets `resume_url` to null on users table.

### Supabase Storage setup (manual, one-time)
- Create bucket `resumes`, set to public
- No RLS needed on storage — files are keyed by `{user_id}/resume.pdf` in the path

No schema changes — `resume_url` column already exists.

---

## 4. Schema Changes

### New table: `user_repos`

```sql
create table if not exists user_repos (
  id serial primary key,
  user_id uuid not null references users(id) on delete cascade,
  repo_url text not null,
  repo_name text,
  summary text not null,
  language text,
  stars int default 0,
  created_at timestamptz not null default now()
);

alter table user_repos enable row level security;
create policy "Users can view own repos" on user_repos for select using (auth.uid() = user_id);
create policy "Users can insert own repos" on user_repos for insert with check (auth.uid() = user_id);
create policy "Users can delete own repos" on user_repos for delete using (auth.uid() = user_id);
create index idx_user_repos_user on user_repos(user_id);
```

### Modified table: `users`

```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS summarization_count int DEFAULT 0;
```

---

## What This Does NOT Cover

- Email prompt rewrite (Spec 2)
- LLM-generated subject lines (Spec 2)
- Signature block with links (Spec 2)
- Fix EmailGenerate schema to allow all 4 tones (Spec 2)
- System prompt for email generation (Spec 2)
- "Other" tag bucket cleanup in interest picker (cosmetic, deferred)
- Background reply polling (separate feature)
- Frontend visual overhaul (separate initiative)
