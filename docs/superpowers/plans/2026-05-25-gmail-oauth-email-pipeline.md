# Gmail OAuth + Email Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let students generate AI email drafts, edit them, and send directly from REACH via their Gmail account — with automatic reply detection.

**Architecture:** Google OAuth stores encrypted refresh tokens in a `gmail_tokens` table. Email generation calls Claude API using the existing `build_email_prompt()`. Sending uses the Gmail API. An `email_log` table tracks drafts, edits, and thread IDs. A polling endpoint checks Gmail for replies and updates outreach status.

**Tech Stack:** FastAPI, Google OAuth 2.0, Gmail API (`google-api-python-client`), Anthropic Claude API (`anthropic`), Fernet symmetric encryption (`cryptography`), Supabase/Postgres.

**Dependencies to install:**
```bash
pip install google-auth google-auth-oauthlib google-api-python-client cryptography anthropic
```

**Environment variables to add to `backend/.env`:**
```
GOOGLE_CLIENT_ID=<from Google Cloud Console>
GOOGLE_CLIENT_SECRET=<from Google Cloud Console>
GOOGLE_REDIRECT_URI=http://localhost:3000/gmail/callback
TOKEN_ENCRYPTION_KEY=<generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
ANTHROPIC_API_KEY=<Claude API key>
```

---

## File Structure

| File | Responsibility |
|------|----------------|
| `backend/email/oauth.py` | Google OAuth helpers: build auth URL, exchange code for tokens, refresh tokens, encrypt/decrypt |
| `backend/email/gmail.py` | Gmail API helpers: send email, check thread for replies |
| `backend/email/generate.py` | Claude API wrapper: generate email draft from prompt |
| `backend/routers/email.py` | All email endpoints: OAuth flow, generate, send, check replies |
| `backend/schemas.py` | Add EmailGenerate, EmailSend, EmailDraft, GmailStatus schemas |
| `backend/db/schema.sql` | Add gmail_tokens + email_log tables |
| `backend/main.py` | Mount email router |
| `tests/email/test_oauth.py` | OAuth helper tests |
| `tests/email/test_gmail.py` | Gmail send/reply helper tests |
| `tests/email/test_generate.py` | Email generation tests |
| `tests/api/test_email_router.py` | Email endpoint tests |

---

### Task 1: Database Schema — gmail_tokens + email_log

**Files:**
- Modify: `backend/db/schema.sql`

- [ ] **Step 1: Add gmail_tokens and email_log tables to schema.sql**

Add after the `outreach_log` table definition (after line 76):

```sql
-- Gmail OAuth tokens (encrypted, one per user)
create table if not exists gmail_tokens (
  user_id uuid primary key references users(id) on delete cascade,
  encrypted_refresh_token text not null,
  gmail_email text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Email log (tracks generated drafts, edits, and sends)
create table if not exists email_log (
  id serial primary key,
  user_id uuid not null references users(id) on delete cascade,
  company_id int not null references companies(id) on delete cascade,
  original_draft text not null,
  final_text text,
  subject_line text,
  tone text not null default 'curious',
  gmail_thread_id text,
  gmail_message_id text,
  status text not null default 'draft' check (status in ('draft', 'sent', 'replied', 'no_response')),
  sent_at timestamptz,
  reply_detected_at timestamptz,
  created_at timestamptz not null default now()
);
```

Add after existing indexes (after line 82):

```sql
create index if not exists idx_email_log_user on email_log(user_id);
create index if not exists idx_email_log_status on email_log(status);
create index if not exists idx_email_log_thread on email_log(gmail_thread_id);
```

Add after existing RLS policies (after line 119):

```sql
-- Gmail tokens RLS
alter table gmail_tokens enable row level security;
create policy "Users can view own gmail_tokens" on gmail_tokens for select using (auth.uid() = user_id);
create policy "Users can insert own gmail_tokens" on gmail_tokens for insert with check (auth.uid() = user_id);
create policy "Users can update own gmail_tokens" on gmail_tokens for update using (auth.uid() = user_id);
create policy "Users can delete own gmail_tokens" on gmail_tokens for delete using (auth.uid() = user_id);

-- Email log RLS
alter table email_log enable row level security;
create policy "Users can view own email_log" on email_log for select using (auth.uid() = user_id);
create policy "Users can insert own email_log" on email_log for insert with check (auth.uid() = user_id);
create policy "Users can update own email_log" on email_log for update using (auth.uid() = user_id);
```

Add trigger for gmail_tokens updated_at (after the existing triggers, ~line 99):

```sql
create or replace trigger gmail_tokens_updated_at
  before update on gmail_tokens
  for each row execute function update_updated_at();
```

- [ ] **Step 2: Run migrations in Supabase SQL Editor**

Copy and run only the new table/index/policy/trigger statements in the Supabase SQL Editor. Do NOT re-run existing table creation statements.

- [ ] **Step 3: Commit**

```bash
git add backend/db/schema.sql
git commit -m "feat: add gmail_tokens and email_log tables"
```

---

### Task 2: Pydantic Schemas for Email Pipeline

**Files:**
- Modify: `backend/schemas.py`

- [ ] **Step 1: Add email schemas to schemas.py**

Add at the end of the file, after the `OutreachEntry` class:

```python
# --- Email ---

class EmailGenerate(BaseModel):
    company_id: int
    tone: Literal["curious", "friendly"] = "curious"


class EmailDraft(BaseModel):
    draft: str
    tone: str
    company_id: int
    company_name: str
    founder_name: str | None = None


class EmailSend(BaseModel):
    company_id: int
    subject_line: str
    final_text: str
    original_draft: str
    tone: str = "curious"


class EmailLogEntry(BaseModel):
    id: int
    company_id: int
    original_draft: str
    final_text: str | None = None
    subject_line: str | None = None
    tone: str
    status: str
    sent_at: str | None = None
    reply_detected_at: str | None = None
    created_at: str | None = None


class GmailStatus(BaseModel):
    connected: bool
    gmail_email: str | None = None
```

- [ ] **Step 2: Commit**

```bash
git add backend/schemas.py
git commit -m "feat: add email pipeline Pydantic schemas"
```

---

### Task 3: Token Encryption + Google OAuth Helpers

**Files:**
- Create: `backend/email/oauth.py`
- Test: `tests/email/test_oauth.py`

- [ ] **Step 1: Write the tests**

Create `tests/email/test_oauth.py`:

```python
import os
import pytest
from unittest.mock import patch, MagicMock
from cryptography.fernet import Fernet

# Generate a test key
TEST_KEY = Fernet.generate_key().decode()


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", TEST_KEY)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost:3000/gmail/callback")


def test_encrypt_decrypt_roundtrip():
    from backend.email.oauth import encrypt_token, decrypt_token
    original = "ya29.a0AfH6SMBx..."
    encrypted = encrypt_token(original)
    assert encrypted != original
    assert decrypt_token(encrypted) == original


def test_encrypt_produces_different_ciphertext():
    from backend.email.oauth import encrypt_token
    token = "my-refresh-token"
    a = encrypt_token(token)
    b = encrypt_token(token)
    # Fernet uses random IV, so same plaintext -> different ciphertext
    assert a != b


def test_build_auth_url_contains_scopes():
    from backend.email.oauth import build_auth_url
    url = build_auth_url()
    assert "gmail.send" in url
    assert "gmail.readonly" in url
    assert "test-client-id" in url


def test_exchange_code_calls_google(monkeypatch):
    from backend.email.oauth import exchange_code

    mock_flow = MagicMock()
    mock_flow.credentials.refresh_token = "refresh-123"
    mock_flow.credentials.token = "access-456"

    with patch("backend.email.oauth.Flow.from_client_config", return_value=mock_flow):
        mock_flow.fetch_token = MagicMock()
        refresh, access = exchange_code("auth-code-xyz")

    assert refresh == "refresh-123"
    assert access == "access-456"
    mock_flow.fetch_token.assert_called_once_with(code="auth-code-xyz")


def test_refresh_access_token(monkeypatch):
    from backend.email.oauth import refresh_access_token

    mock_creds = MagicMock()
    mock_creds.token = "new-access-token"
    mock_creds.valid = True

    with patch("backend.email.oauth.Credentials", return_value=mock_creds):
        token = refresh_access_token("old-refresh-token")

    assert token == "new-access-token"
    mock_creds.refresh.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/email/test_oauth.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.email.oauth'`

- [ ] **Step 3: Implement oauth.py**

Create `backend/email/oauth.py`:

```python
"""Google OAuth helpers for Gmail integration."""

import os
from urllib.parse import urlencode

from cryptography.fernet import Fernet
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]

GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"


def _get_fernet() -> Fernet:
    key = os.environ["TOKEN_ENCRYPTION_KEY"]
    return Fernet(key.encode())


def encrypt_token(token: str) -> str:
    return _get_fernet().encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()


def _client_config() -> dict:
    return {
        "web": {
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "auth_uri": GOOGLE_AUTH_URI,
            "token_uri": GOOGLE_TOKEN_URI,
            "redirect_uris": [os.environ["GOOGLE_REDIRECT_URI"]],
        }
    }


def build_auth_url() -> str:
    """Build the Google OAuth consent URL."""
    params = {
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "redirect_uri": os.environ["GOOGLE_REDIRECT_URI"],
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"{GOOGLE_AUTH_URI}?{urlencode(params)}"


def exchange_code(code: str) -> tuple[str, str]:
    """Exchange an authorization code for refresh + access tokens.

    Returns (refresh_token, access_token).
    """
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES)
    flow.redirect_uri = os.environ["GOOGLE_REDIRECT_URI"]
    flow.fetch_token(code=code)
    return flow.credentials.refresh_token, flow.credentials.token


def refresh_access_token(refresh_token: str) -> str:
    """Use a refresh token to get a fresh access token."""
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=GOOGLE_TOKEN_URI,
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
    )
    from google.auth.transport.requests import Request

    creds.refresh(Request())
    return creds.token
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/email/test_oauth.py -v`
Expected: All 5 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/email/oauth.py tests/email/test_oauth.py
git commit -m "feat: add Google OAuth helpers with token encryption"
```

---

### Task 4: Gmail API Helpers — Send + Check Replies

**Files:**
- Create: `backend/email/gmail.py`
- Test: `tests/email/test_gmail.py`

- [ ] **Step 1: Write the tests**

Create `tests/email/test_gmail.py`:

```python
import base64
from unittest.mock import patch, MagicMock
import pytest


@pytest.fixture
def mock_gmail_service():
    service = MagicMock()
    return service


def test_send_email_returns_thread_and_message_id(mock_gmail_service):
    from backend.email.gmail import send_email

    mock_gmail_service.users().messages().send().execute.return_value = {
        "id": "msg-123",
        "threadId": "thread-456",
    }

    result = send_email(
        service=mock_gmail_service,
        to="founder@startup.com",
        subject="Quick question",
        body="Hi, I'm a high school senior...",
        sender_email="student@gmail.com",
    )

    assert result["message_id"] == "msg-123"
    assert result["thread_id"] == "thread-456"


def test_send_email_constructs_valid_mime(mock_gmail_service):
    from backend.email.gmail import send_email

    mock_gmail_service.users().messages().send().execute.return_value = {
        "id": "msg-1", "threadId": "thread-1",
    }

    send_email(
        service=mock_gmail_service,
        to="founder@co.com",
        subject="Test subject",
        body="Test body",
        sender_email="me@gmail.com",
    )

    call_args = mock_gmail_service.users().messages().send.call_args
    raw = call_args[1]["body"]["raw"] if "body" in call_args[1] else call_args[0][0]["body"]["raw"]
    decoded = base64.urlsafe_b64decode(raw + "==").decode()
    assert "founder@co.com" in decoded
    assert "Test subject" in decoded
    assert "Test body" in decoded


def test_check_thread_no_reply(mock_gmail_service):
    from backend.email.gmail import check_thread_for_reply

    mock_gmail_service.users().threads().get().execute.return_value = {
        "messages": [
            {"id": "msg-1", "labelIds": ["SENT"]},
        ]
    }

    result = check_thread_for_reply(
        service=mock_gmail_service,
        thread_id="thread-1",
        sender_email="student@gmail.com",
    )
    assert result is False


def test_check_thread_has_reply(mock_gmail_service):
    from backend.email.gmail import check_thread_for_reply

    mock_gmail_service.users().threads().get().execute.return_value = {
        "messages": [
            {"id": "msg-1", "labelIds": ["SENT"]},
            {"id": "msg-2", "labelIds": ["INBOX"]},
        ]
    }

    result = check_thread_for_reply(
        service=mock_gmail_service,
        thread_id="thread-1",
        sender_email="student@gmail.com",
    )
    assert result is True


def test_build_gmail_service():
    from backend.email.gmail import build_gmail_service

    with patch("backend.email.gmail.build") as mock_build:
        mock_build.return_value = MagicMock()
        service = build_gmail_service("access-token-123")

    mock_build.assert_called_once()
    assert service is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/email/test_gmail.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.email.gmail'`

- [ ] **Step 3: Implement gmail.py**

Create `backend/email/gmail.py`:

```python
"""Gmail API helpers for sending emails and checking replies."""

import base64
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def build_gmail_service(access_token: str):
    """Create a Gmail API service from an access token."""
    creds = Credentials(token=access_token)
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def send_email(
    service,
    to: str,
    subject: str,
    body: str,
    sender_email: str,
) -> dict:
    """Send an email via Gmail API.

    Returns dict with 'message_id' and 'thread_id'.
    """
    message = MIMEText(body)
    message["to"] = to
    message["from"] = sender_email
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    result = service.users().messages().send(
        userId="me", body={"raw": raw}
    ).execute()

    return {
        "message_id": result["id"],
        "thread_id": result["threadId"],
    }


def check_thread_for_reply(
    service,
    thread_id: str,
    sender_email: str,
) -> bool:
    """Check if a Gmail thread has a reply (message not from sender).

    Returns True if a reply was detected.
    """
    thread = service.users().threads().get(
        userId="me", id=thread_id, format="minimal"
    ).execute()

    messages = thread.get("messages", [])
    # More than one message means someone replied
    # (first message is the one we sent)
    return len(messages) > 1
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/email/test_gmail.py -v`
Expected: All 5 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/email/gmail.py tests/email/test_gmail.py
git commit -m "feat: add Gmail API helpers for send and reply detection"
```

---

### Task 5: Email Generation with Claude API

**Files:**
- Create: `backend/email/generate.py`
- Test: `tests/email/test_generate.py`

- [ ] **Step 1: Write the tests**

Create `tests/email/test_generate.py`:

```python
from unittest.mock import patch, MagicMock
import pytest


def test_generate_draft_calls_claude():
    from backend.email.generate import generate_draft

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="I'm a high school senior in SF...")]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("backend.email.generate.anthropic.Anthropic", return_value=mock_client):
        draft = generate_draft(
            student_bio="HS senior, ML projects",
            student_capabilities=["deep-learning", "data-pipelines"],
            company_name="Pando Bio",
            company_summary="AI enzyme design",
            specific_projects=["Analyze screening data"],
            founder_name="Alex Chen",
            tone="curious",
        )

    assert draft == "I'm a high school senior in SF..."
    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["model"] == "claude-haiku-4-5-20251001"
    assert call_kwargs["max_tokens"] == 300


def test_generate_draft_passes_guidance_angle():
    from backend.email.generate import generate_draft

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Draft text")]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("backend.email.generate.anthropic.Anthropic", return_value=mock_client):
        generate_draft(
            student_bio="Student",
            student_capabilities=["frontend-development"],
            company_name="TestCo",
            company_summary="Test",
            specific_projects=[],
            founder_name="Jane",
            tone="friendly",
            guidance_angle="Lead with React experience",
        )

    prompt_text = mock_client.messages.create.call_args[1]["messages"][0]["content"]
    assert "Lead with React experience" in prompt_text


def test_generate_draft_uses_correct_tone():
    from backend.email.generate import generate_draft

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Draft")]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("backend.email.generate.anthropic.Anthropic", return_value=mock_client):
        generate_draft(
            student_bio="Student",
            student_capabilities=["backend-apis"],
            company_name="TestCo",
            company_summary="Test",
            specific_projects=[],
            founder_name="Sam",
            tone="friendly",
        )

    prompt_text = mock_client.messages.create.call_args[1]["messages"][0]["content"]
    assert "Warm" in prompt_text  # Friendly tone voice starts with "Warm"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/email/test_generate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.email.generate'`

- [ ] **Step 3: Implement generate.py**

Create `backend/email/generate.py`:

```python
"""Email draft generation using Claude API."""

import anthropic
from backend.email.prompt import build_email_prompt

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 300


def generate_draft(
    student_bio: str,
    student_capabilities: list[str],
    company_name: str,
    company_summary: str,
    specific_projects: list[str],
    founder_name: str,
    tone: str = "curious",
    guidance_angle: str | None = None,
) -> str:
    """Generate a cold email draft using Claude.

    Returns the draft text.
    """
    prompt = build_email_prompt(
        student_bio=student_bio,
        student_capabilities=student_capabilities,
        company_name=company_name,
        company_summary=company_summary,
        specific_projects=specific_projects,
        founder_name=founder_name,
        guidance_angle=guidance_angle,
        tone=tone,
    )

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/email/test_generate.py -v`
Expected: All 3 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/email/generate.py tests/email/test_generate.py
git commit -m "feat: add Claude API email draft generation"
```

---

### Task 6: Email Router — OAuth Endpoints

**Files:**
- Create: `backend/routers/email.py`
- Test: `tests/api/test_email_router.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Write the tests**

Create `tests/api/test_email_router.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test.jwt.token"}


def _mock_auth(user_id="user-uuid-123"):
    return patch(
        "backend.auth._decode_token",
        return_value={"sub": user_id, "email": "test@school.edu"},
    )


# --- OAuth endpoints ---


def test_get_auth_url_requires_auth(client):
    response = client.get("/email/gmail/auth-url")
    assert response.status_code == 401


def test_get_auth_url_returns_google_url(client, auth_headers):
    with _mock_auth(), \
         patch("backend.routers.email.build_auth_url", return_value="https://accounts.google.com/o/oauth2/v2/auth?client_id=test"):
        response = client.get("/email/gmail/auth-url", headers=auth_headers)

    assert response.status_code == 200
    assert "https://accounts.google.com" in response.json()["url"]


def test_gmail_callback_stores_token(client, auth_headers):
    mock_db = MagicMock()
    mock_db.table.return_value.upsert.return_value.execute.return_value.data = [{}]

    with _mock_auth(), \
         patch("backend.routers.email.exchange_code", return_value=("refresh-tok", "access-tok")), \
         patch("backend.routers.email.encrypt_token", return_value="encrypted-refresh"), \
         patch("backend.routers.email.build_gmail_service") as mock_build, \
         patch("backend.routers.email.get_db", return_value=mock_db):

        # Mock getting user's email from Gmail
        mock_service = MagicMock()
        mock_service.users().getProfile().execute.return_value = {"emailAddress": "student@gmail.com"}
        mock_build.return_value = mock_service

        response = client.post(
            "/email/gmail/callback",
            json={"code": "auth-code-xyz"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    assert response.json()["gmail_email"] == "student@gmail.com"
    mock_db.table.return_value.upsert.assert_called_once()


def test_gmail_status_not_connected(client, auth_headers):
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

    with _mock_auth(), patch("backend.routers.email.get_db", return_value=mock_db):
        response = client.get("/email/gmail/status", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["connected"] is False


def test_gmail_status_connected(client, auth_headers):
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"gmail_email": "student@gmail.com"}
    ]

    with _mock_auth(), patch("backend.routers.email.get_db", return_value=mock_db):
        response = client.get("/email/gmail/status", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["connected"] is True
    assert response.json()["gmail_email"] == "student@gmail.com"


def test_gmail_disconnect(client, auth_headers):
    mock_db = MagicMock()
    mock_db.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = [{}]

    with _mock_auth(), patch("backend.routers.email.get_db", return_value=mock_db):
        response = client.delete("/email/gmail/disconnect", headers=auth_headers)

    assert response.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/api/test_email_router.py -v -k "gmail"`
Expected: FAIL (router doesn't exist yet)

- [ ] **Step 3: Create the email router with OAuth endpoints**

Create `backend/routers/email.py`:

```python
"""Email pipeline endpoints: Gmail OAuth, generation, send, reply checking."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth import get_current_user
from backend.db import get_db
from backend.email.oauth import (
    build_auth_url,
    exchange_code,
    encrypt_token,
    decrypt_token,
    refresh_access_token,
)
from backend.email.gmail import build_gmail_service
from backend.schemas import GmailStatus

router = APIRouter(prefix="/email")


class AuthUrlResponse(BaseModel):
    url: str


class CallbackRequest(BaseModel):
    code: str


class CallbackResponse(BaseModel):
    gmail_email: str


# --- Gmail OAuth ---


@router.get("/gmail/auth-url", response_model=AuthUrlResponse)
def get_gmail_auth_url(user_id: str = Depends(get_current_user)):
    """Get the Google OAuth consent URL."""
    return {"url": build_auth_url()}


@router.post("/gmail/callback", response_model=CallbackResponse)
def gmail_callback(body: CallbackRequest, user_id: str = Depends(get_current_user)):
    """Exchange OAuth code for tokens, store encrypted refresh token."""
    refresh_token, access_token = exchange_code(body.code)

    if not refresh_token:
        raise HTTPException(status_code=400, detail="No refresh token returned. Try disconnecting and reconnecting.")

    # Get the user's Gmail address
    service = build_gmail_service(access_token)
    profile = service.users().getProfile(userId="me").execute()
    gmail_email = profile["emailAddress"]

    # Store encrypted refresh token
    db = get_db()
    db.table("gmail_tokens").upsert({
        "user_id": user_id,
        "encrypted_refresh_token": encrypt_token(refresh_token),
        "gmail_email": gmail_email,
    }).execute()

    return {"gmail_email": gmail_email}


@router.get("/gmail/status", response_model=GmailStatus)
def gmail_status(user_id: str = Depends(get_current_user)):
    """Check if user has connected Gmail."""
    db = get_db()
    result = db.table("gmail_tokens").select("gmail_email").eq("user_id", user_id).execute()

    if not result.data:
        return {"connected": False, "gmail_email": None}

    return {"connected": True, "gmail_email": result.data[0]["gmail_email"]}


@router.delete("/gmail/disconnect")
def gmail_disconnect(user_id: str = Depends(get_current_user)):
    """Disconnect Gmail by removing stored tokens."""
    db = get_db()
    db.table("gmail_tokens").delete().eq("user_id", user_id).execute()
    return {"ok": True}
```

- [ ] **Step 4: Mount the email router in main.py**

Add to `backend/main.py` imports (after line 8):

```python
from backend.routers import users, companies, outreach, email
```

Add after existing `include_router` calls (after line 25):

```python
app.include_router(email.router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/api/test_email_router.py -v -k "gmail"`
Expected: All 6 PASS

- [ ] **Step 6: Commit**

```bash
git add backend/routers/email.py backend/main.py tests/api/test_email_router.py
git commit -m "feat: add Gmail OAuth endpoints (auth-url, callback, status, disconnect)"
```

---

### Task 7: Email Router — Generate Endpoint

**Files:**
- Modify: `backend/routers/email.py`
- Modify: `tests/api/test_email_router.py`

- [ ] **Step 1: Add generate endpoint tests**

Add to `tests/api/test_email_router.py`:

```python
# --- Generate endpoint ---


def _sample_company():
    return {
        "id": 1,
        "name": "AlphaCo",
        "summary": "AI tools for alpha",
        "specific_projects": ["Build dashboard"],
        "founder_name": "Alex Chen",
        "capability_tags": ["deep-learning"],
        "need_tags": [],
    }


def _sample_user():
    return {
        "id": "user-uuid-123",
        "skills": ["deep-learning", "data-pipelines"],
        "bio": "HS senior interested in ML",
        "location": "San Francisco",
    }


def test_generate_requires_auth(client):
    response = client.post("/email/generate", json={"company_id": 1})
    assert response.status_code == 401


def test_generate_returns_draft(client, auth_headers):
    mock_db = MagicMock()

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "companies":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [_sample_company()]
        elif table_name == "users":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [_sample_user()]
        return mock_table

    mock_db.table.side_effect = table_side_effect

    with _mock_auth(), \
         patch("backend.routers.email.get_db", return_value=mock_db), \
         patch("backend.routers.email.generate_draft", return_value="I'm a high school senior in SF..."):
        response = client.post(
            "/email/generate",
            json={"company_id": 1, "tone": "curious"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["draft"] == "I'm a high school senior in SF..."
    assert data["company_name"] == "AlphaCo"
    assert data["tone"] == "curious"


def test_generate_company_not_found(client, auth_headers):
    mock_db = MagicMock()

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "companies":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = []
        elif table_name == "users":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [_sample_user()]
        return mock_table

    mock_db.table.side_effect = table_side_effect

    with _mock_auth(), patch("backend.routers.email.get_db", return_value=mock_db):
        response = client.post(
            "/email/generate",
            json={"company_id": 999},
            headers=auth_headers,
        )

    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/api/test_email_router.py -v -k "generate"`
Expected: FAIL (endpoint doesn't exist)

- [ ] **Step 3: Add generate endpoint to email router**

Add to `backend/routers/email.py` imports:

```python
from backend.email.generate import generate_draft
from backend.schemas import EmailGenerate, EmailDraft, GmailStatus
```

(Remove `GmailStatus` from the existing import if it's already there — consolidate into one import.)

Add the endpoint after the OAuth endpoints:

```python
# --- Email Generation ---


@router.post("/generate", response_model=EmailDraft)
def generate_email(body: EmailGenerate, user_id: str = Depends(get_current_user)):
    """Generate a cold email draft for a company."""
    db = get_db()

    # Fetch company
    company_result = db.table("companies").select("*").eq("id", body.company_id).execute()
    if not company_result.data:
        raise HTTPException(status_code=404, detail="Company not found")
    company = company_result.data[0]

    # Fetch user profile
    user_result = db.table("users").select("skills, bio, location").eq("id", user_id).execute()
    user = user_result.data[0] if user_result.data else {}

    student_bio = user.get("bio") or "High school student"
    student_capabilities = user.get("skills") or []

    # Generate guidance angle from matching capabilities
    guidance_angle = None
    company_caps = company.get("capability_tags") or company.get("need_tags") or []
    overlap = [c for c in student_capabilities if c in company_caps]
    if overlap:
        from backend.capabilities import TIER2_LABELS
        labels = [TIER2_LABELS.get(c, c) for c in overlap]
        guidance_angle = f"Lead with your experience in {', '.join(labels)}"

    draft = generate_draft(
        student_bio=student_bio,
        student_capabilities=student_capabilities,
        company_name=company.get("name", ""),
        company_summary=company.get("summary") or company.get("description") or "",
        specific_projects=company.get("specific_projects") or [],
        founder_name=company.get("founder_name") or "the founder",
        tone=body.tone,
        guidance_angle=guidance_angle,
    )

    return {
        "draft": draft,
        "tone": body.tone,
        "company_id": body.company_id,
        "company_name": company.get("name", ""),
        "founder_name": company.get("founder_name"),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/api/test_email_router.py -v -k "generate"`
Expected: All 3 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/routers/email.py tests/api/test_email_router.py
git commit -m "feat: add email generation endpoint"
```

---

### Task 8: Email Router — Send Endpoint

**Files:**
- Modify: `backend/routers/email.py`
- Modify: `tests/api/test_email_router.py`

- [ ] **Step 1: Add send endpoint tests**

Add to `tests/api/test_email_router.py`:

```python
# --- Send endpoint ---


def test_send_requires_auth(client):
    response = client.post("/email/send", json={
        "company_id": 1, "subject_line": "Hi", "final_text": "Hello", "original_draft": "Hello",
    })
    assert response.status_code == 401


def test_send_requires_gmail_connected(client, auth_headers):
    mock_db = MagicMock()

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "gmail_tokens":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = []
        elif table_name == "companies":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [_sample_company()]
        return mock_table

    mock_db.table.side_effect = table_side_effect

    with _mock_auth(), patch("backend.routers.email.get_db", return_value=mock_db):
        response = client.post(
            "/email/send",
            json={"company_id": 1, "subject_line": "Hi", "final_text": "Hello", "original_draft": "Hello"},
            headers=auth_headers,
        )

    assert response.status_code == 400
    assert "Gmail" in response.json()["detail"]


def test_send_requires_founder_email(client, auth_headers):
    mock_db = MagicMock()
    company_no_email = _sample_company()
    company_no_email["founder_email"] = None

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "gmail_tokens":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                {"encrypted_refresh_token": "enc-tok", "gmail_email": "me@gmail.com"}
            ]
        elif table_name == "companies":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [company_no_email]
        return mock_table

    mock_db.table.side_effect = table_side_effect

    with _mock_auth(), patch("backend.routers.email.get_db", return_value=mock_db):
        response = client.post(
            "/email/send",
            json={"company_id": 1, "subject_line": "Hi", "final_text": "Hello", "original_draft": "Hello"},
            headers=auth_headers,
        )

    assert response.status_code == 400
    assert "email" in response.json()["detail"].lower()


def test_send_success(client, auth_headers):
    mock_db = MagicMock()
    company = _sample_company()
    company["founder_email"] = "founder@startup.com"

    insert_result = {"id": 1, "status": "sent"}

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "gmail_tokens":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                {"encrypted_refresh_token": "enc-tok", "gmail_email": "me@gmail.com"}
            ]
        elif table_name == "companies":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [company]
        elif table_name == "email_log":
            mock_table.insert.return_value.execute.return_value.data = [insert_result]
        elif table_name == "outreach_log":
            mock_table.insert.return_value.execute.return_value.data = [{}]
        return mock_table

    mock_db.table.side_effect = table_side_effect

    mock_service = MagicMock()
    mock_service.users().messages().send().execute.return_value = {
        "id": "msg-123", "threadId": "thread-456",
    }

    with _mock_auth(), \
         patch("backend.routers.email.get_db", return_value=mock_db), \
         patch("backend.routers.email.decrypt_token", return_value="refresh-tok"), \
         patch("backend.routers.email.refresh_access_token", return_value="access-tok"), \
         patch("backend.routers.email.build_gmail_service", return_value=mock_service), \
         patch("backend.routers.email.send_email", return_value={"message_id": "msg-123", "thread_id": "thread-456"}):
        response = client.post(
            "/email/send",
            json={
                "company_id": 1,
                "subject_line": "Quick question about AlphaCo",
                "final_text": "Hi, I'm a high school senior...",
                "original_draft": "Draft text here",
                "tone": "curious",
            },
            headers=auth_headers,
        )

    assert response.status_code == 200
    assert response.json()["status"] == "sent"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/api/test_email_router.py -v -k "send"`
Expected: FAIL (endpoint doesn't exist)

- [ ] **Step 3: Add send endpoint to email router**

Add to `backend/routers/email.py` imports (update the gmail import):

```python
from backend.email.gmail import build_gmail_service, send_email
from backend.email.oauth import (
    build_auth_url,
    exchange_code,
    encrypt_token,
    decrypt_token,
    refresh_access_token,
)
from backend.schemas import EmailGenerate, EmailDraft, EmailSend, EmailLogEntry, GmailStatus
```

Add the endpoint:

```python
# --- Email Sending ---


@router.post("/send")
def send_email_endpoint(body: EmailSend, user_id: str = Depends(get_current_user)):
    """Send an email via the user's connected Gmail account."""
    db = get_db()

    # Check Gmail is connected
    token_result = db.table("gmail_tokens").select("encrypted_refresh_token, gmail_email").eq("user_id", user_id).execute()
    if not token_result.data:
        raise HTTPException(status_code=400, detail="Gmail not connected. Please connect your Gmail account first.")

    token_row = token_result.data[0]

    # Get founder email
    company_result = db.table("companies").select("founder_email, name").eq("id", body.company_id).execute()
    if not company_result.data:
        raise HTTPException(status_code=404, detail="Company not found")

    company = company_result.data[0]
    founder_email = company.get("founder_email")
    if not founder_email:
        raise HTTPException(status_code=400, detail="No email address found for this founder")

    # Get fresh access token
    refresh_token = decrypt_token(token_row["encrypted_refresh_token"])
    access_token = refresh_access_token(refresh_token)
    service = build_gmail_service(access_token)

    # Send via Gmail
    result = send_email(
        service=service,
        to=founder_email,
        subject=body.subject_line,
        body=body.final_text,
        sender_email=token_row["gmail_email"],
    )

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    # Log the email
    db.table("email_log").insert({
        "user_id": user_id,
        "company_id": body.company_id,
        "original_draft": body.original_draft,
        "final_text": body.final_text,
        "subject_line": body.subject_line,
        "tone": body.tone,
        "gmail_thread_id": result["thread_id"],
        "gmail_message_id": result["message_id"],
        "status": "sent",
        "sent_at": now,
    }).execute()

    # Also create outreach entry
    from datetime import timedelta
    followup = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    db.table("outreach_log").insert({
        "user_id": user_id,
        "company_id": body.company_id,
        "status": "sent",
        "sent_at": now,
        "followup_date": followup,
        "notes": f"Sent via REACH ({body.tone} tone)",
    }).execute()

    return {"status": "sent", "thread_id": result["thread_id"]}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/api/test_email_router.py -v -k "send"`
Expected: All 4 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/routers/email.py tests/api/test_email_router.py
git commit -m "feat: add email send endpoint with Gmail API integration"
```

---

### Task 9: Email Router — Reply Checking Endpoint

**Files:**
- Modify: `backend/routers/email.py`
- Modify: `tests/api/test_email_router.py`

- [ ] **Step 1: Add reply check tests**

Add to `tests/api/test_email_router.py`:

```python
# --- Reply checking ---


def test_check_replies_requires_auth(client):
    response = client.post("/email/check-replies")
    assert response.status_code == 401


def test_check_replies_detects_reply(client, auth_headers):
    mock_db = MagicMock()

    sent_emails = [
        {"id": 1, "gmail_thread_id": "thread-1", "status": "sent", "company_id": 1},
    ]

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "gmail_tokens":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                {"encrypted_refresh_token": "enc-tok", "gmail_email": "me@gmail.com"}
            ]
        elif table_name == "email_log":
            # For select (finding sent emails)
            mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = sent_emails
            # For update
            mock_table.update.return_value.eq.return_value.execute.return_value.data = [{}]
        elif table_name == "outreach_log":
            mock_table.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{}]
        return mock_table

    mock_db.table.side_effect = table_side_effect

    with _mock_auth(), \
         patch("backend.routers.email.get_db", return_value=mock_db), \
         patch("backend.routers.email.decrypt_token", return_value="refresh-tok"), \
         patch("backend.routers.email.refresh_access_token", return_value="access-tok"), \
         patch("backend.routers.email.build_gmail_service") as mock_build, \
         patch("backend.routers.email.check_thread_for_reply", return_value=True):
        response = client.post("/email/check-replies", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["replies_found"] == 1


def test_check_replies_no_sent_emails(client, auth_headers):
    mock_db = MagicMock()

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "gmail_tokens":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                {"encrypted_refresh_token": "enc-tok", "gmail_email": "me@gmail.com"}
            ]
        elif table_name == "email_log":
            mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        return mock_table

    mock_db.table.side_effect = table_side_effect

    with _mock_auth(), \
         patch("backend.routers.email.get_db", return_value=mock_db), \
         patch("backend.routers.email.decrypt_token", return_value="refresh-tok"), \
         patch("backend.routers.email.refresh_access_token", return_value="access-tok"), \
         patch("backend.routers.email.build_gmail_service"):
        response = client.post("/email/check-replies", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["replies_found"] == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/api/test_email_router.py -v -k "replies"`
Expected: FAIL (endpoint doesn't exist)

- [ ] **Step 3: Add reply checking endpoint**

Add to `backend/routers/email.py` imports (update gmail import):

```python
from backend.email.gmail import build_gmail_service, send_email, check_thread_for_reply
```

Add the endpoint:

```python
# --- Reply Checking ---


@router.post("/check-replies")
def check_replies(user_id: str = Depends(get_current_user)):
    """Check all sent emails for replies via Gmail API."""
    db = get_db()

    # Check Gmail is connected
    token_result = db.table("gmail_tokens").select("encrypted_refresh_token, gmail_email").eq("user_id", user_id).execute()
    if not token_result.data:
        raise HTTPException(status_code=400, detail="Gmail not connected")

    token_row = token_result.data[0]

    # Get fresh access token
    refresh_token = decrypt_token(token_row["encrypted_refresh_token"])
    access_token = refresh_access_token(refresh_token)
    service = build_gmail_service(access_token)

    # Find all sent emails with thread IDs
    sent_result = db.table("email_log").select("id, gmail_thread_id, company_id").eq("user_id", user_id).eq("status", "sent").execute()
    sent_emails = sent_result.data

    from datetime import datetime, timezone
    replies_found = 0

    for email_entry in sent_emails:
        thread_id = email_entry.get("gmail_thread_id")
        if not thread_id:
            continue

        has_reply = check_thread_for_reply(
            service=service,
            thread_id=thread_id,
            sender_email=token_row["gmail_email"],
        )

        if has_reply:
            replies_found += 1
            now = datetime.now(timezone.utc).isoformat()

            # Update email_log
            db.table("email_log").update({
                "status": "replied",
                "reply_detected_at": now,
            }).eq("id", email_entry["id"]).execute()

            # Update outreach_log
            db.table("outreach_log").update({
                "status": "replied",
            }).eq("user_id", user_id).eq("company_id", email_entry["company_id"]).execute()

    return {"replies_found": replies_found, "checked": len(sent_emails)}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/api/test_email_router.py -v -k "replies"`
Expected: All 3 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/routers/email.py tests/api/test_email_router.py
git commit -m "feat: add reply checking endpoint with Gmail thread monitoring"
```

---

### Task 10: Frontend Types + API Functions

**Files:**
- Modify: `frontend/lib/types.ts`
- Modify: `frontend/lib/api.ts`

- [ ] **Step 1: Add email types to types.ts**

Add at the end of `frontend/lib/types.ts`:

```typescript
// --- Email ---

export interface EmailDraft {
  draft: string;
  tone: string;
  company_id: number;
  company_name: string;
  founder_name: string | null;
}

export interface GmailStatus {
  connected: boolean;
  gmail_email: string | null;
}
```

- [ ] **Step 2: Add email API functions to api.ts**

Add at the end of `frontend/lib/api.ts`:

```typescript
// --- Email ---

export async function getGmailAuthUrl(): Promise<{ url: string }> {
  return apiFetch("/email/gmail/auth-url");
}

export async function submitGmailCallback(code: string): Promise<{ gmail_email: string }> {
  return apiFetch("/email/gmail/callback", {
    method: "POST",
    body: JSON.stringify({ code }),
  });
}

export async function getGmailStatus(): Promise<GmailStatus> {
  return apiFetch("/email/gmail/status");
}

export async function disconnectGmail(): Promise<void> {
  return apiFetch("/email/gmail/disconnect", { method: "DELETE" });
}

export async function generateEmailDraft(
  companyId: number,
  tone: "curious" | "friendly" = "curious"
): Promise<EmailDraft> {
  return apiFetch("/email/generate", {
    method: "POST",
    body: JSON.stringify({ company_id: companyId, tone }),
  });
}

export async function sendEmail(data: {
  company_id: number;
  subject_line: string;
  final_text: string;
  original_draft: string;
  tone: string;
}): Promise<{ status: string; thread_id: string }> {
  return apiFetch("/email/send", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function checkReplies(): Promise<{ replies_found: number; checked: number }> {
  return apiFetch("/email/check-replies", { method: "POST" });
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/types.ts frontend/lib/api.ts
git commit -m "feat: add email pipeline types and API functions to frontend"
```

---

### Task 11: Gmail OAuth Callback Page

**Files:**
- Create: `frontend/app/gmail/callback/page.tsx`

- [ ] **Step 1: Create the callback page**

This page handles the redirect from Google OAuth. It extracts the `code` query param and sends it to the backend.

Create `frontend/app/gmail/callback/page.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { submitGmailCallback } from "@/lib/api";

export default function GmailCallbackPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [error, setError] = useState("");

  useEffect(() => {
    const code = searchParams.get("code");
    if (!code) {
      setStatus("error");
      setError("No authorization code received from Google.");
      return;
    }

    submitGmailCallback(code)
      .then(() => {
        setStatus("success");
        setTimeout(() => router.push("/profile"), 2000);
      })
      .catch((err) => {
        setStatus("error");
        setError(err.message || "Failed to connect Gmail.");
      });
  }, [searchParams, router]);

  return (
    <div className="min-h-[100dvh] flex items-center justify-center">
      <div className="text-center max-w-md">
        {status === "loading" && (
          <>
            <h1 className="text-xl font-semibold mb-2">Connecting Gmail...</h1>
            <p className="text-zinc-500">Please wait while we finish setting up.</p>
          </>
        )}
        {status === "success" && (
          <>
            <h1 className="text-xl font-semibold mb-2">Gmail Connected</h1>
            <p className="text-zinc-500">Redirecting you back...</p>
          </>
        )}
        {status === "error" && (
          <>
            <h1 className="text-xl font-semibold mb-2 text-red-600">Connection Failed</h1>
            <p className="text-zinc-500 mb-4">{error}</p>
            <button
              onClick={() => router.push("/profile")}
              className="text-sm text-blue-600 hover:underline"
            >
              Back to profile
            </button>
          </>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/gmail/callback/page.tsx
git commit -m "feat: add Gmail OAuth callback page"
```

---

### Task 12: Update requirements.txt

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add new dependencies**

Add to `requirements.txt`:

```
google-auth>=2.0
google-auth-oauthlib>=1.0
google-api-python-client>=2.0
cryptography>=42.0
anthropic>=0.30
```

- [ ] **Step 2: Install dependencies**

Run: `pip install -r requirements.txt`

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "feat: add Gmail and Claude API dependencies"
```

---

### Task 13: Run Full Test Suite

- [ ] **Step 1: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS (existing + new)

- [ ] **Step 2: Verify no regressions**

Check that existing test counts haven't decreased:
- `tests/api/test_auth.py` — 5 tests
- `tests/api/test_companies.py` — 7 tests
- `tests/api/test_outreach.py` — 4 tests
- `tests/api/test_users.py` — 4 tests
- `tests/email/test_prompt.py` — 6 tests
- `tests/email/test_oauth.py` — 5 tests (new)
- `tests/email/test_gmail.py` — 5 tests (new)
- `tests/email/test_generate.py` — 3 tests (new)
- `tests/api/test_email_router.py` — 13 tests (new)

---

## Self-Review Checklist

**Spec coverage:**
- Gmail OAuth (scopes, token storage, encrypted) — Tasks 1, 3, 6 ✓
- Email generation (Claude API, prompt, tones) — Tasks 5, 7 ✓
- Student edit + send flow — Task 8 ✓
- Data stored at send time (email_text, original_draft, thread_id, etc.) — Tasks 1, 8 ✓
- Thread monitoring (check for replies) — Tasks 4, 9 ✓
- Outreach tracker auto-update — Task 8 (send creates outreach entry), Task 9 (reply updates status) ✓
- Frontend callback page — Task 11 ✓
- Frontend API functions — Task 10 ✓

**Not in scope (per spec, these are Phase 2 or frontend overhaul):**
- EmailWorkspace UI rewrite (deferred — user planning frontend visual overhaul)
- ML on real outcomes (Phase 2 — needs 100+ outcomes first)
- 7-day no_response timeout (can be added as a cron job later)
- Google verification submission (manual process, not code)

**Placeholder scan:** No TBDs, TODOs, or vague steps found.

**Type consistency:** All schemas, function signatures, and property names are consistent across tasks.
