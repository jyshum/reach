# Email Generation Overhaul — Design Spec

**Date:** 2026-06-02
**Status:** Approved
**Scope:** Spec 2 of 2 for the email generation overhaul. This spec rewires the email generation pipeline to consume the new structured profile inputs from Spec 1 (bio builder, GitHub repo summaries, PDF resume upload).

## Problem

The email generation prompt is wired to the old profile data. It passes a freeform `projects` text that no longer gets filled (replaced by repo summaries in Spec 1). Raw URLs (portfolio, GitHub, resume) are dumped into the prompt body with "include naturally if relevant" — the LLM can't read them, so it either ignores them or awkwardly pastes them mid-sentence. Subject lines are hardcoded (`"Quick question - {companyName}"`). The `EmailGenerate` schema only allows 2 of 4 tones, silently blocking scrappy and earnest. There's no system prompt — persona, rules, and context are all crammed into one user message.

## Solution

Rewrite the prompt with a system/user split, wire in repo summaries, move links to a signature block, generate subject lines, and fix the schema.

---

## 1. Fix EmailGenerate Schema

### Current state
```python
class EmailGenerate(BaseModel):
    company_id: int
    tone: Literal["curious", "friendly"] = "curious"
```

The frontend sends all 4 tones. Scrappy and earnest requests return 422.

### Change
```python
class EmailGenerate(BaseModel):
    company_id: int
    tone: Literal["curious", "friendly", "scrappy", "earnest"] = "curious"
```

### Update EmailDraft response
Add `subject_line` field so the frontend receives a generated subject:
```python
class EmailDraft(BaseModel):
    draft: str
    subject_line: str
    tone: str
    company_id: int
    company_name: str
    founder_name: str | None = None
```

---

## 2. Prompt Rewrite — System + User Split

### System prompt (stable across all calls)

```
You write cold emails from high school students to startup founders.

RULES:
- Open by establishing you're a high school student. This is your biggest pattern interrupt — founders don't get emails from high schoolers.
- Maximum 4-5 sentences. Shorter is better.
- Sound like a real student, not a professional.
- NO filler enthusiasm ("I'm really excited", "I'd love to", "I'm passionate about")
- NO compliments about the company ("I admire your work", "Your company is amazing")
- Show genuine interest in the founder's DOMAIN — you care about the same problems they're solving.
- If the student has projects, reference at most one — pick the one most relevant to the founder's domain. Don't just name-drop it; connect it to what the founder is building.
- Include ONE specific hook showing you actually understand what they build.
- Do NOT use a formal sign-off. Just the student's first name.
- After the name, add a signature line with the provided links (only include links that are provided). Format: "GitHub: url | Resume: url" on its own line. Do not put links anywhere in the email body.

OUTPUT FORMAT:
- First line: SUBJECT: <subject line, under 8 words, specific to this founder>
- Then a blank line
- Then the email body (including first name sign-off and signature line)
```

### User message (changes per call)

```
TONE: {voice description}
ASK: {ask instruction}

STUDENT:
Bio: {bio}
{repo_summaries section, if any}
Domain interests: {interests}

SIGNATURE LINKS (for the sign-off line, NOT the email body):
{resume_url if present}
{github_url if present}
{portfolio_url if present}

COMPANY:
Company: {company_name}
Founder: {founder_name}
{founder_bio if present}
What they do: {company_summary}
{specific_projects if present}

Write the email.
```

### Repo summaries format in the prompt

If the user has repos, include:
```
Projects:
- trading-bot (Python, 12 stars): A Python bot that executes crypto trades using Binance API. Uses websockets for real-time data.
- scraper-tool (JavaScript): A web scraper that collects pricing data from e-commerce sites.
```

If no repos, omit the section entirely.

---

## 3. Generate Endpoint Changes

### Fetch user_repos

The `/email/generate` endpoint currently fetches:
```python
db.table("users").select("interests, projects, bio, portfolio_url, github_url, resume_url")
```

Change to:
```python
db.table("users").select("interests, bio, portfolio_url, github_url, resume_url")
```

And add a separate query:
```python
db.table("user_repos").select("repo_name, summary, language, stars").eq("user_id", user_id)
```

Pass the repo data as a list of dicts to the prompt builder.

### Drop `student_projects` parameter

Remove `student_projects` from `generate_draft()` and `build_email_prompt()`. Replace with `repo_summaries: list[dict]`.

### Signature links

Remove `portfolio_url`, `github_url`, `resume_url` as separate prompt parameters that get injected into the email body. Instead, pass them as `signature_links: dict` — the prompt puts them in the sign-off line only.

### Parse response

The LLM returns:
```
SUBJECT: How you handle X at CompanyName

Hey — I'm a junior at Lincoln High...

— Alex
GitHub: github.com/alex | Resume: link
```

In `generate.py`, parse the response:
1. If the first line starts with `SUBJECT:`, extract it as the subject line and strip it from the body.
2. If no `SUBJECT:` prefix found, fall back to `"Quick question - {company_name}"`.
3. Strip leading/trailing whitespace from both.

Return both `subject_line` and `draft` from `generate_draft()`.

### Updated function signature

```python
def generate_draft(
    student_bio: str,
    repo_summaries: list[dict],
    student_interests: list[str],
    signature_links: dict,
    company_name: str,
    company_summary: str,
    specific_projects: list[str],
    founder_name: str,
    founder_bio: str | None = None,
    tone: str = "curious",
) -> tuple[str, str]:  # (subject_line, draft)
```

### Updated endpoint response

```python
return {
    "draft": draft,
    "subject_line": subject_line,
    "tone": body.tone,
    "company_id": body.company_id,
    "company_name": company.get("name", ""),
    "founder_name": company.get("founder_name"),
}
```

---

## 4. Frontend Changes

### EmailWorkspace: use generated subject

Currently in `handleGenerate()`:
```typescript
if (!subjectLine) {
    setSubjectLine(`Quick question - ${companyName}`);
}
```

Change to use the returned subject line:
```typescript
setSubjectLine(result.subject_line || `Quick question - ${companyName}`);
```

Always overwrite with the generated subject (not just when empty), since each generation may produce a different subject. User can still edit it manually after.

### EmailDraft type

Add `subject_line` to the `EmailDraft` interface in `frontend/lib/types.ts`:
```typescript
export interface EmailDraft {
  draft: string;
  subject_line: string;
  tone: string;
  company_id: number;
  company_name: string;
  founder_name: string | null;
}
```

### Clean up projects from updateProfile

In `frontend/lib/api.ts`, the `updateProfile` function's type includes `projects` in the `Partial<Pick<...>>`. Remove it since the projects textarea no longer exists.

---

## What This Does NOT Cover

- Background reply polling (separate feature)
- Frontend visual overhaul (separate initiative, on hold)
- "Other" tag bucket cleanup (cosmetic, deferred)
- Changing the LLM model (staying on Haiku)
- Email templates or follow-up emails
