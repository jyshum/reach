# Email Pipeline Phase 1: Gmail Integration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **BLOCKED:** Do not start this plan until Phase 0 validation (email-validation plan) produces a go decision.

**Goal:** Send LLM-generated cold emails from the student's Gmail account, monitor threads for replies, and collect outcome data for future ML training.

**Architecture:** Google OAuth flow stores tokens server-side. New `/email` router handles generation, sending, and monitoring. A background job polls Gmail for replies and updates outreach status. All sent emails and outcomes are logged for future ML use.

**Tech Stack:** Python/FastAPI, Google Gmail API (google-api-python-client, google-auth-oauthlib), Supabase/PostgreSQL, Claude API or Ollama for generation

---

### Task 1: Database Schema for Email Pipeline

**Files:**
- Modify: `backend/db/schema.sql`

- [ ] **Step 1: Add gmail_tokens and email_log tables**

Add to `backend/db/schema.sql`:

```sql
-- Gmail OAuth tokens (encrypted at rest via Supabase)
CREATE TABLE gmail_tokens (
  id SERIAL PRIMARY KEY,
  user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  access_token TEXT NOT NULL,
  refresh_token TEXT NOT NULL,
  token_expiry TIMESTAMPTZ NOT NULL,
  gmail_address TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Email log for ML training data
CREATE TABLE email_log (
  id SERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  company_id INT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  original_draft TEXT NOT NULL,
  sent_text TEXT NOT NULL,
  subject_line TEXT NOT NULL,
  gmail_thread_id TEXT,
  gmail_message_id TEXT,
  sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  reply_detected_at TIMESTAMPTZ,
  outcome TEXT DEFAULT 'pending',  -- pending, replied, no_response
  outcome_labeled_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_gmail_tokens_user ON gmail_tokens(user_id);
CREATE INDEX idx_email_log_user ON email_log(user_id);
CREATE INDEX idx_email_log_outcome ON email_log(outcome) WHERE outcome = 'pending';

-- RLS
ALTER TABLE gmail_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY gmail_tokens_own ON gmail_tokens
  FOR ALL USING (user_id = auth.uid());

CREATE POLICY email_log_own ON email_log
  FOR ALL USING (user_id = auth.uid());
```

- [ ] **Step 2: Run migration on Supabase**

```sql
-- Execute in Supabase SQL editor
CREATE TABLE IF NOT EXISTS gmail_tokens (
  id SERIAL PRIMARY KEY,
  user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  access_token TEXT NOT NULL,
  refresh_token TEXT NOT NULL,
  token_expiry TIMESTAMPTZ NOT NULL,
  gmail_address TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS email_log (
  id SERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  company_id INT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  original_draft TEXT NOT NULL,
  sent_text TEXT NOT NULL,
  subject_line TEXT NOT NULL,
  gmail_thread_id TEXT,
  gmail_message_id TEXT,
  sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  reply_detected_at TIMESTAMPTZ,
  outcome TEXT DEFAULT 'pending',
  outcome_labeled_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gmail_tokens_user ON gmail_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_email_log_user ON email_log(user_id);
CREATE INDEX IF NOT EXISTS idx_email_log_outcome ON email_log(outcome) WHERE outcome = 'pending';
```

- [ ] **Step 3: Commit**

```bash
git add backend/db/schema.sql
git commit -m "feat: add gmail_tokens and email_log tables"
```

---

### Task 2: Backend Schemas for Email

**Files:**
- Modify: `backend/schemas.py`

- [ ] **Step 1: Add email schemas**

Add to `backend/schemas.py`:

```python
# --- Email ---

class EmailDraftRequest(BaseModel):
    company_id: int


class EmailDraftResponse(BaseModel):
    draft: str
    subject_line: str
    company_name: str
    founder_name: str | None = None
    founder_email: str | None = None


class EmailSendRequest(BaseModel):
    company_id: int
    subject_line: str
    email_text: str
    original_draft: str


class EmailSendResponse(BaseModel):
    id: int
    gmail_thread_id: str | None = None
    status: str


class EmailLogEntry(BaseModel):
    id: int
    company_id: int
    company_name: str | None = None
    subject_line: str
    outcome: str
    sent_at: str | None = None
    reply_detected_at: str | None = None
```

- [ ] **Step 2: Commit**

```bash
git add backend/schemas.py
git commit -m "feat: add email pipeline schemas"
```

---

### Task 3: Google OAuth Flow

**Files:**
- Create: `backend/email/gmail_auth.py`
- Create: `backend/routers/gmail.py`

- [ ] **Step 1: Write Gmail OAuth helpers**

```python
# backend/email/gmail_auth.py
"""Google OAuth helpers for Gmail API access."""

import os
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]

# Set these in .env
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/gmail/callback")


def get_oauth_flow() -> Flow:
    """Create a Google OAuth flow for Gmail access."""
    client_config = {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [GOOGLE_REDIRECT_URI],
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = GOOGLE_REDIRECT_URI
    return flow


def get_credentials_from_tokens(token_row: dict) -> Credentials:
    """Build Credentials object from stored token data."""
    return Credentials(
        token=token_row["access_token"],
        refresh_token=token_row["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        expiry=datetime.fromisoformat(token_row["token_expiry"].replace("Z", "+00:00")),
    )


def is_token_expired(token_row: dict) -> bool:
    """Check if stored token is expired."""
    expiry = datetime.fromisoformat(token_row["token_expiry"].replace("Z", "+00:00"))
    return expiry <= datetime.now(timezone.utc)
```

- [ ] **Step 2: Write Gmail OAuth router**

```python
# backend/routers/gmail.py
"""Gmail OAuth endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from datetime import datetime, timezone

from backend.auth import get_current_user
from backend.db import get_db
from backend.email.gmail_auth import get_oauth_flow, SCOPES

router = APIRouter()


@router.get("/gmail/connect")
def gmail_connect(request: Request, user_id: str = Depends(get_current_user)):
    """Start Gmail OAuth flow. Returns the authorization URL."""
    flow = get_oauth_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=user_id,  # Pass user_id through OAuth state
    )
    return {"auth_url": auth_url}


@router.get("/gmail/callback")
def gmail_callback(request: Request, code: str, state: str):
    """Handle OAuth callback from Google."""
    user_id = state
    flow = get_oauth_flow()

    try:
        flow.fetch_token(code=code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth token exchange failed: {e}")

    credentials = flow.credentials

    db = get_db()

    # Get user's Gmail address from the ID token
    gmail_address = ""
    if hasattr(credentials, "id_token") and credentials.id_token:
        gmail_address = credentials.id_token.get("email", "")

    token_data = {
        "user_id": user_id,
        "access_token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_expiry": credentials.expiry.isoformat() if credentials.expiry else datetime.now(timezone.utc).isoformat(),
        "gmail_address": gmail_address,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Upsert (one token per user)
    db.table("gmail_tokens").upsert(token_data, on_conflict="user_id").execute()

    # Redirect to frontend
    return RedirectResponse(url="http://localhost:3000/profile?gmail=connected")


@router.get("/gmail/status")
def gmail_status(user_id: str = Depends(get_current_user)):
    """Check if user has connected Gmail."""
    db = get_db()
    result = db.table("gmail_tokens").select("gmail_address, token_expiry").eq("user_id", user_id).execute()

    if not result.data:
        return {"connected": False}

    return {
        "connected": True,
        "gmail_address": result.data[0]["gmail_address"],
    }


@router.delete("/gmail/disconnect")
def gmail_disconnect(user_id: str = Depends(get_current_user)):
    """Remove stored Gmail tokens."""
    db = get_db()
    db.table("gmail_tokens").delete().eq("user_id", user_id).execute()
    return {"disconnected": True}
```

- [ ] **Step 3: Register router in main.py**

In `backend/main.py`, add:
```python
from backend.routers.gmail import router as gmail_router
app.include_router(gmail_router)
```

- [ ] **Step 4: Add Google dependencies**

Run: `pip install google-api-python-client google-auth-oauthlib`

Add to `requirements.txt`:
```
google-api-python-client>=2.0
google-auth-oauthlib>=1.0
```

- [ ] **Step 5: Commit**

```bash
git add backend/email/gmail_auth.py backend/routers/gmail.py backend/main.py requirements.txt
git commit -m "feat: add Gmail OAuth connect/callback/status endpoints"
```

---

### Task 4: Email Generation Endpoint

**Files:**
- Create: `backend/routers/email.py`

- [ ] **Step 1: Write the email generation and send router**

```python
# backend/routers/email.py
"""Email generation and sending endpoints."""

import base64
from email.mime.text import MIMEText
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from googleapiclient.discovery import build

from backend.auth import get_current_user
from backend.db import get_db
from backend.email.prompt import build_email_prompt
from backend.email.gmail_auth import get_credentials_from_tokens, is_token_expired
from backend.guidance.rules import generate_guidance
from backend.schemas import (
    EmailDraftRequest,
    EmailDraftResponse,
    EmailSendRequest,
    EmailSendResponse,
)
from backend.pipeline.enrich_config import OLLAMA_URL, OLLAMA_MODEL

import requests as http_requests

router = APIRouter()


def _generate_draft(prompt: str) -> str:
    """Generate email draft via Ollama."""
    response = http_requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "system": "You are a helpful writing assistant. Follow instructions exactly.",
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 256},
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["response"].strip()


def _generate_subject(company_name: str, student_capabilities: list[str]) -> str:
    """Generate a short, non-generic subject line."""
    cap_text = student_capabilities[0] if student_capabilities else "help"
    return f"Quick question about {company_name} — {cap_text}"


@router.post("/email/draft", response_model=EmailDraftResponse)
def generate_email_draft(
    body: EmailDraftRequest,
    user_id: str = Depends(get_current_user),
):
    """Generate an email draft for a company."""
    db = get_db()

    # Get company
    result = db.table("companies").select("*").eq("id", body.company_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Company not found")
    company = result.data[0]

    # Get user profile
    user_result = db.table("users").select("*").eq("id", user_id).execute()
    if not user_result.data:
        raise HTTPException(status_code=404, detail="User not found")
    user = user_result.data[0]

    # Generate guidance for the angle
    user_skills = user.get("skills", []) or []
    guidance = generate_guidance(user_skills, company)
    guidance_angle = guidance.your_angle if guidance else None

    # Build prompt and generate
    prompt = build_email_prompt(
        student_bio=user.get("bio") or "",
        student_capabilities=user_skills,
        company_name=company["name"],
        company_summary=company.get("summary") or company.get("description", ""),
        specific_projects=company.get("specific_projects") or [],
        founder_name=company.get("founder_name") or "Founder",
        guidance_angle=guidance_angle,
    )

    draft = _generate_draft(prompt)
    subject = _generate_subject(company["name"], user_skills)

    return EmailDraftResponse(
        draft=draft,
        subject_line=subject,
        company_name=company["name"],
        founder_name=company.get("founder_name"),
        founder_email=company.get("founder_email"),
    )


@router.post("/email/send", response_model=EmailSendResponse)
def send_email(
    body: EmailSendRequest,
    user_id: str = Depends(get_current_user),
):
    """Send an email via the user's connected Gmail."""
    db = get_db()

    # Check Gmail connection
    token_result = db.table("gmail_tokens").select("*").eq("user_id", user_id).execute()
    if not token_result.data:
        raise HTTPException(status_code=400, detail="Gmail not connected. Connect your Gmail first.")

    token_row = token_result.data[0]
    if is_token_expired(token_row):
        raise HTTPException(status_code=401, detail="Gmail token expired. Please reconnect.")

    # Get company for founder email
    company_result = db.table("companies").select("founder_email, name").eq("id", body.company_id).execute()
    if not company_result.data:
        raise HTTPException(status_code=404, detail="Company not found")
    company = company_result.data[0]

    founder_email = company.get("founder_email")
    if not founder_email:
        raise HTTPException(status_code=400, detail="No founder email on file for this company.")

    # Build and send via Gmail API
    credentials = get_credentials_from_tokens(token_row)
    service = build("gmail", "v1", credentials=credentials)

    message = MIMEText(body.email_text)
    message["to"] = founder_email
    message["subject"] = body.subject_line
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    try:
        sent = service.users().messages().send(
            userId="me",
            body={"raw": raw},
        ).execute()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to send via Gmail: {e}")

    thread_id = sent.get("threadId")
    message_id = sent.get("id")

    # Log the email
    log_entry = {
        "user_id": user_id,
        "company_id": body.company_id,
        "original_draft": body.original_draft,
        "sent_text": body.email_text,
        "subject_line": body.subject_line,
        "gmail_thread_id": thread_id,
        "gmail_message_id": message_id,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "outcome": "pending",
    }
    result = db.table("email_log").insert(log_entry).execute()

    # Also create outreach entry
    db.table("outreach_log").insert({
        "user_id": user_id,
        "company_id": body.company_id,
        "status": "sent",
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "notes": f"Sent via REACH",
    }).execute()

    return EmailSendResponse(
        id=result.data[0]["id"],
        gmail_thread_id=thread_id,
        status="sent",
    )
```

- [ ] **Step 2: Register router**

In `backend/main.py`, add:
```python
from backend.routers.email import router as email_router
app.include_router(email_router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/routers/email.py backend/main.py
git commit -m "feat: add email draft generation and Gmail send endpoints"
```

---

### Task 5: Thread Monitoring Background Job

**Files:**
- Create: `backend/email/monitor.py`

- [ ] **Step 1: Write the reply monitoring script**

```python
# backend/email/monitor.py
"""Poll Gmail for replies to sent emails. Run on a schedule (e.g. cron every 4 hours)."""

from datetime import datetime, timezone, timedelta

from googleapiclient.discovery import build

from backend.db import get_db
from backend.email.gmail_auth import get_credentials_from_tokens, is_token_expired

REPLY_TIMEOUT_DAYS = 7


def check_for_replies():
    """Check all pending emails for replies."""
    db = get_db()
    now = datetime.now(timezone.utc)
    timeout_cutoff = now - timedelta(days=REPLY_TIMEOUT_DAYS)

    # Get all pending emails
    pending = db.table("email_log").select(
        "id, user_id, gmail_thread_id, sent_at"
    ).eq("outcome", "pending").execute()

    if not pending.data:
        print("No pending emails to check.")
        return

    # Group by user to minimize token lookups
    by_user: dict[str, list[dict]] = {}
    for entry in pending.data:
        uid = entry["user_id"]
        by_user.setdefault(uid, []).append(entry)

    replied_count = 0
    timeout_count = 0

    for user_id, entries in by_user.items():
        # Get user's Gmail tokens
        token_result = db.table("gmail_tokens").select("*").eq("user_id", user_id).execute()
        if not token_result.data:
            continue

        token_row = token_result.data[0]
        if is_token_expired(token_row):
            print(f"  Skipping user {user_id}: token expired")
            continue

        credentials = get_credentials_from_tokens(token_row)
        service = build("gmail", "v1", credentials=credentials)

        for entry in entries:
            thread_id = entry.get("gmail_thread_id")
            sent_at_str = entry.get("sent_at", "")

            # Check timeout
            try:
                sent_at = datetime.fromisoformat(sent_at_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                sent_at = now

            if sent_at < timeout_cutoff:
                db.table("email_log").update({
                    "outcome": "no_response",
                    "outcome_labeled_at": now.isoformat(),
                }).eq("id", entry["id"]).execute()
                timeout_count += 1
                continue

            if not thread_id:
                continue

            # Check thread for replies
            try:
                thread = service.users().threads().get(
                    userId="me", id=thread_id, format="minimal"
                ).execute()
                messages = thread.get("messages", [])

                if len(messages) > 1:
                    # Reply detected (more than just our sent message)
                    db.table("email_log").update({
                        "outcome": "replied",
                        "reply_detected_at": now.isoformat(),
                        "outcome_labeled_at": now.isoformat(),
                    }).eq("id", entry["id"]).execute()

                    # Also update outreach log
                    db.table("outreach_log").update({
                        "status": "replied",
                    }).eq("user_id", user_id).eq(
                        "company_id", entry.get("company_id")
                    ).eq("status", "sent").execute()

                    replied_count += 1

            except Exception as e:
                print(f"  Error checking thread {thread_id}: {e}")

    print(f"Done. Replied: {replied_count}, Timed out: {timeout_count}, Still pending: {len(pending.data) - replied_count - timeout_count}")


if __name__ == "__main__":
    check_for_replies()
```

- [ ] **Step 2: Commit**

```bash
git add backend/email/monitor.py
git commit -m "feat: add Gmail thread reply monitoring script"
```

---

### Task 6: Frontend Email Integration

**Files:**
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/lib/types.ts`
- Modify: `frontend/components/EmailWorkspace.tsx`

- [ ] **Step 1: Add email API functions**

Add to `frontend/lib/api.ts`:

```typescript
export async function getGmailStatus(): Promise<{ connected: boolean; gmail_address?: string }> {
  return apiFetch("/gmail/status");
}

export async function generateEmailDraft(companyId: number): Promise<{
  draft: string;
  subject_line: string;
  company_name: string;
  founder_name: string | null;
  founder_email: string | null;
}> {
  return apiFetch("/email/draft", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ company_id: companyId }),
  });
}

export async function sendEmail(data: {
  company_id: number;
  subject_line: string;
  email_text: string;
  original_draft: string;
}): Promise<{ id: number; gmail_thread_id: string | null; status: string }> {
  return apiFetch("/email/send", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}
```

- [ ] **Step 2: Read current EmailWorkspace to understand its interface**

Run: `cat frontend/components/EmailWorkspace.tsx` to see current implementation. Then update it to integrate with the new generation and send APIs. The component should:

1. Show a "Generate draft" button that calls `generateEmailDraft(companyId)`
2. Display the draft in an editable textarea
3. Show a "Send via Gmail" button (disabled if Gmail not connected, with a "Connect Gmail" link)
4. On send, call `sendEmail()` with the edited text and original draft
5. Show success/error states

The exact implementation depends on the current EmailWorkspace structure — read it first, then modify in place.

- [ ] **Step 3: Verify build**

Run: `cd frontend && npx next build 2>&1 | tail -5`
Expected: Build succeeds

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/api.ts frontend/components/EmailWorkspace.tsx
git commit -m "feat: integrate email generation and Gmail send in frontend"
```

---

### Task 7: Google Cloud Setup (Manual)

This task is manual configuration, no code.

- [ ] **Step 1: Create Google Cloud project**

Go to https://console.cloud.google.com, create a new project called "REACH".

- [ ] **Step 2: Enable Gmail API**

In the project, go to APIs & Services > Enable APIs > search "Gmail API" > Enable.

- [ ] **Step 3: Configure OAuth consent screen**

- User type: External
- App name: REACH
- Support email: your email
- Scopes: gmail.send, gmail.readonly
- Test users: add your own Gmail

- [ ] **Step 4: Create OAuth credentials**

- Type: Web application
- Authorized redirect URI: `http://localhost:8000/gmail/callback`
- Save Client ID and Client Secret

- [ ] **Step 5: Add to .env**

```bash
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/gmail/callback
```

- [ ] **Step 6: Submit for Google verification**

Go to OAuth consent screen > Publish app. This starts the verification process (2-6 weeks). While waiting, the app works for up to 100 manually-added test users.

---

### Task 8: End-to-End Test

- [ ] **Step 1: Start backend and frontend**

```bash
# Terminal 1
cd backend && uvicorn backend.main:app --reload

# Terminal 2
cd frontend && npm run dev
```

- [ ] **Step 2: Test Gmail connect flow**

1. Log in to REACH
2. Go to profile page
3. Click "Connect Gmail"
4. Complete Google OAuth
5. Verify redirect back to profile with "Gmail connected" status

- [ ] **Step 3: Test email generation**

1. Navigate to a founder brief
2. Click "Generate draft"
3. Verify a draft appears in the EmailWorkspace
4. Edit the draft

- [ ] **Step 4: Test email send**

1. Click "Send via Gmail"
2. Verify success message
3. Check outreach tracker — should show new "sent" entry
4. Check your Gmail sent folder — email should be there

- [ ] **Step 5: Test reply monitoring**

```bash
python -m backend.email.monitor
```
Verify it runs without errors (no pending emails to check initially, that's fine).

- [ ] **Step 6: Commit any fixes**

```bash
git add -A
git commit -m "chore: fix issues from end-to-end email pipeline testing"
```
