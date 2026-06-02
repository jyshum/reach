# Bounce Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect Gmail NDR bounce messages when checking for replies, mark emails as bounced, flag bad founder emails globally, and block sends to bounced addresses.

**Architecture:** Add `check_thread_for_bounce()` to `gmail.py` that inspects thread message headers for bounce indicators (MAILER-DAEMON, delivery failure subjects, X-Failed-Recipients). Update the check-replies endpoint to call bounce check before reply check. Add a send guard that rejects sends to previously-bounced addresses. Schema gets `'bounced'` status in both log tables and a new `founder_email_status` column on companies.

**Tech Stack:** Python, FastAPI, Gmail API (metadata format), Supabase PostgreSQL

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/email/gmail.py` | Modify | Add `check_thread_for_bounce()` function |
| `backend/routers/email.py` | Modify | Update check-replies flow, add send guard |
| `backend/db/schema.sql` | Modify | Add `'bounced'` to constraints, add `founder_email_status` column |
| `tests/email/test_gmail.py` | Modify | Tests for `check_thread_for_bounce()` |
| `tests/api/test_email_router.py` | Modify | Tests for bounce in check-replies, send guard |

---

### Task 1: Add `check_thread_for_bounce()` with tests

**Files:**
- Modify: `tests/email/test_gmail.py:84` (after existing tests)
- Modify: `backend/email/gmail.py:40` (after `check_thread_for_reply`)

- [ ] **Step 1: Write failing tests for bounce detection**

Add to `tests/email/test_gmail.py` after line 84 (`test_check_thread_has_reply`):

```python
def test_check_bounce_detects_mailer_daemon(mock_gmail_service):
    from backend.email.gmail import check_thread_for_bounce

    mock_gmail_service.users().threads().get().execute.return_value = {
        "messages": [
            {
                "id": "msg-1",
                "payload": {"headers": [
                    {"name": "From", "value": "student@gmail.com"},
                    {"name": "Subject", "value": "Quick question"},
                ]},
            },
            {
                "id": "msg-2",
                "payload": {"headers": [
                    {"name": "From", "value": "Mail Delivery Subsystem <mailer-daemon@googlemail.com>"},
                    {"name": "Subject", "value": "Delivery Status Notification (Failure)"},
                ]},
            },
        ]
    }

    result = check_thread_for_bounce(
        service=mock_gmail_service,
        thread_id="thread-1",
        sender_email="student@gmail.com",
    )
    assert result is True


def test_check_bounce_detects_failed_recipients_header(mock_gmail_service):
    from backend.email.gmail import check_thread_for_bounce

    mock_gmail_service.users().threads().get().execute.return_value = {
        "messages": [
            {
                "id": "msg-1",
                "payload": {"headers": [
                    {"name": "From", "value": "student@gmail.com"},
                    {"name": "Subject", "value": "Quick question"},
                ]},
            },
            {
                "id": "msg-2",
                "payload": {"headers": [
                    {"name": "From", "value": "postmaster@outlook.com"},
                    {"name": "Subject", "value": "Undeliverable: Quick question"},
                    {"name": "X-Failed-Recipients", "value": "founder@startup.com"},
                ]},
            },
        ]
    }

    result = check_thread_for_bounce(
        service=mock_gmail_service,
        thread_id="thread-1",
        sender_email="student@gmail.com",
    )
    assert result is True


def test_check_bounce_ignores_real_reply(mock_gmail_service):
    from backend.email.gmail import check_thread_for_bounce

    mock_gmail_service.users().threads().get().execute.return_value = {
        "messages": [
            {
                "id": "msg-1",
                "payload": {"headers": [
                    {"name": "From", "value": "student@gmail.com"},
                    {"name": "Subject", "value": "Quick question"},
                ]},
            },
            {
                "id": "msg-2",
                "payload": {"headers": [
                    {"name": "From", "value": "founder@startup.com"},
                    {"name": "Subject", "value": "Re: Quick question"},
                ]},
            },
        ]
    }

    result = check_thread_for_bounce(
        service=mock_gmail_service,
        thread_id="thread-1",
        sender_email="student@gmail.com",
    )
    assert result is False


def test_check_bounce_no_extra_messages(mock_gmail_service):
    from backend.email.gmail import check_thread_for_bounce

    mock_gmail_service.users().threads().get().execute.return_value = {
        "messages": [
            {
                "id": "msg-1",
                "payload": {"headers": [
                    {"name": "From", "value": "student@gmail.com"},
                    {"name": "Subject", "value": "Quick question"},
                ]},
            },
        ]
    }

    result = check_thread_for_bounce(
        service=mock_gmail_service,
        thread_id="thread-1",
        sender_email="student@gmail.com",
    )
    assert result is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/email/test_gmail.py -v -k "bounce"`
Expected: FAIL — `ImportError: cannot import name 'check_thread_for_bounce'`

- [ ] **Step 3: Implement `check_thread_for_bounce()`**

Add to `backend/email/gmail.py` after the `check_thread_for_reply` function (after line 51):

```python
BOUNCE_SENDERS = {"mailer-daemon", "postmaster", "mail delivery subsystem"}

BOUNCE_SUBJECTS = {
    "delivery status notification",
    "undeliverable",
    "mail delivery failed",
    "returned to sender",
}


def check_thread_for_bounce(
    service,
    thread_id: str,
    sender_email: str,
) -> bool:
    """Check if a Gmail thread contains a bounce (NDR) message."""
    thread = service.users().threads().get(
        userId="me", id=thread_id, format="metadata",
        metadataHeaders=["From", "Subject", "X-Failed-Recipients"],
    ).execute()

    messages = thread.get("messages", [])
    sender_lower = sender_email.lower()

    for msg in messages:
        headers = {
            h["name"].lower(): h["value"]
            for h in msg.get("payload", {}).get("headers", [])
        }

        from_addr = headers.get("from", "").lower()
        if sender_lower in from_addr:
            continue

        # Check X-Failed-Recipients header
        if "x-failed-recipients" in headers:
            return True

        # Check From for bounce senders
        if any(sender in from_addr for sender in BOUNCE_SENDERS):
            return True

        # Check Subject for bounce patterns
        subject = headers.get("subject", "").lower()
        if any(pattern in subject for pattern in BOUNCE_SUBJECTS):
            return True

    return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/email/test_gmail.py -v -k "bounce"`
Expected: 4 passed

- [ ] **Step 5: Run all existing gmail tests to check for regressions**

Run: `pytest tests/email/test_gmail.py -v`
Expected: 9 passed (5 existing + 4 new)

- [ ] **Step 6: Commit**

```bash
git add backend/email/gmail.py tests/email/test_gmail.py
git commit -m "feat: add check_thread_for_bounce() to detect Gmail NDR messages"
```

---

### Task 2: Update schema for bounced status

**Files:**
- Modify: `backend/db/schema.sql:88` (email_log status constraint)
- Modify: `backend/db/schema.sql:68` (outreach_log status constraint)
- Modify: `backend/db/schema.sql:22` (companies table — add column)

- [ ] **Step 1: Add `'bounced'` to `email_log` status constraint**

In `backend/db/schema.sql`, change line 98:

```sql
-- OLD:
  status text not null default 'draft' check (status in ('draft', 'sent', 'replied', 'no_response')),
-- NEW:
  status text not null default 'draft' check (status in ('draft', 'sent', 'replied', 'no_response', 'bounced')),
```

- [ ] **Step 2: Add `'bounced'` to `outreach_log` status constraint**

In `backend/db/schema.sql`, change line 70:

```sql
-- OLD:
  status text not null check (status in ('sent', 'replied', 'meeting', 'no-response')),
-- NEW:
  status text not null check (status in ('sent', 'replied', 'meeting', 'no-response', 'bounced')),
```

- [ ] **Step 3: Add `founder_email_status` column to companies table**

In `backend/db/schema.sql`, add after `founder_email text,` (after line 48):

```sql
  founder_email_status text default 'unknown',
```

- [ ] **Step 4: Add migration comment block**

Add at the end of `backend/db/schema.sql`:

```sql
-- ============================================================
-- MIGRATION: Bounce detection (2026-06-01)
-- Run these in Supabase SQL Editor on existing database:
--
-- ALTER TABLE email_log DROP CONSTRAINT email_log_status_check;
-- ALTER TABLE email_log ADD CONSTRAINT email_log_status_check
--   CHECK (status IN ('draft', 'sent', 'replied', 'no_response', 'bounced'));
--
-- ALTER TABLE outreach_log DROP CONSTRAINT outreach_log_status_check;
-- ALTER TABLE outreach_log ADD CONSTRAINT outreach_log_status_check
--   CHECK (status IN ('sent', 'replied', 'meeting', 'no-response', 'bounced'));
--
-- ALTER TABLE companies ADD COLUMN IF NOT EXISTS
--   founder_email_status text DEFAULT 'unknown';
-- ============================================================
```

- [ ] **Step 5: Commit**

```bash
git add backend/db/schema.sql
git commit -m "schema: add bounced status to email_log/outreach_log, add founder_email_status column"
```

---

### Task 3: Update check-replies endpoint with bounce detection

**Files:**
- Modify: `tests/api/test_email_router.py:355` (after existing tests)
- Modify: `backend/routers/email.py:17` (import)
- Modify: `backend/routers/email.py:195-239` (check-replies endpoint)

- [ ] **Step 1: Write failing test for bounce detection in check-replies**

Add to `tests/api/test_email_router.py` at the end of the file:

```python
def test_check_replies_detects_bounce(client, auth_headers):
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
            mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = sent_emails
            mock_table.update.return_value.eq.return_value.execute.return_value.data = [{}]
        elif table_name == "outreach_log":
            mock_table.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{}]
        elif table_name == "companies":
            mock_table.update.return_value.eq.return_value.execute.return_value.data = [{}]
        return mock_table

    mock_db.table.side_effect = table_side_effect

    with _mock_auth(), \
         patch("backend.routers.email.get_db", return_value=mock_db), \
         patch("backend.routers.email.decrypt_token", return_value="refresh-tok"), \
         patch("backend.routers.email.refresh_access_token", return_value="access-tok"), \
         patch("backend.routers.email.build_gmail_service"), \
         patch("backend.routers.email.check_thread_for_bounce", return_value=True):
        response = client.post("/email/check-replies", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["bounces_found"] == 1
    assert response.json()["replies_found"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/api/test_email_router.py::test_check_replies_detects_bounce -v`
Expected: FAIL — `ImportError` (check_thread_for_bounce not imported in router) or KeyError on `bounces_found`

- [ ] **Step 3: Update the check-replies endpoint**

In `backend/routers/email.py`, update the import on line 17:

```python
from backend.email.gmail import build_gmail_service, send_email, check_thread_for_reply, check_thread_for_bounce
```

Replace the `check_replies` function (lines 196-239) with:

```python
@router.post("/check-replies")
def check_replies(user_id: str = Depends(get_current_user)):
    """Check all sent emails for bounces and replies via Gmail API."""
    db = get_db()

    token_result = db.table("gmail_tokens").select("encrypted_refresh_token, gmail_email").eq("user_id", user_id).execute()
    if not token_result.data:
        raise HTTPException(status_code=400, detail="Gmail not connected")

    token_row = token_result.data[0]

    refresh_token = decrypt_token(token_row["encrypted_refresh_token"])
    access_token = refresh_access_token(refresh_token)
    service = build_gmail_service(access_token)

    sent_result = db.table("email_log").select("id, gmail_thread_id, company_id").eq("user_id", user_id).eq("status", "sent").execute()
    sent_emails = sent_result.data

    replies_found = 0
    bounces_found = 0

    for email_entry in sent_emails:
        thread_id = email_entry.get("gmail_thread_id")
        if not thread_id:
            continue

        # Check for bounce first
        is_bounce = check_thread_for_bounce(
            service=service,
            thread_id=thread_id,
            sender_email=token_row["gmail_email"],
        )

        if is_bounce:
            bounces_found += 1
            now = datetime.now(timezone.utc).isoformat()

            db.table("email_log").update({
                "status": "bounced",
            }).eq("id", email_entry["id"]).execute()

            db.table("outreach_log").update({
                "status": "bounced",
            }).eq("user_id", user_id).eq("company_id", email_entry["company_id"]).execute()

            db.table("companies").update({
                "founder_email_status": "bounced",
            }).eq("id", email_entry["company_id"]).execute()

            continue

        # Check for reply
        has_reply = check_thread_for_reply(
            service=service,
            thread_id=thread_id,
            sender_email=token_row["gmail_email"],
        )

        if has_reply:
            replies_found += 1
            now = datetime.now(timezone.utc).isoformat()

            db.table("email_log").update({
                "status": "replied",
                "reply_detected_at": now,
            }).eq("id", email_entry["id"]).execute()

            db.table("outreach_log").update({
                "status": "replied",
            }).eq("user_id", user_id).eq("company_id", email_entry["company_id"]).execute()

    return {"replies_found": replies_found, "bounces_found": bounces_found, "checked": len(sent_emails)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/api/test_email_router.py::test_check_replies_detects_bounce -v`
Expected: PASS

- [ ] **Step 5: Run existing check-replies tests for regressions**

Run: `pytest tests/api/test_email_router.py -v -k "check_replies"`
Expected: 3 passed (2 existing + 1 new)

- [ ] **Step 6: Commit**

```bash
git add backend/routers/email.py tests/api/test_email_router.py
git commit -m "feat: detect bounces in check-replies endpoint, flag bounced company emails"
```

---

### Task 4: Add send guard for bounced emails

**Files:**
- Modify: `tests/api/test_email_router.py` (after bounce test)
- Modify: `backend/routers/email.py:132-189` (send endpoint)

- [ ] **Step 1: Write failing test for send guard**

Add to `tests/api/test_email_router.py` after the bounce test:

```python
def test_send_rejects_bounced_email(client, auth_headers):
    mock_db = MagicMock()
    company = _sample_company()
    company["founder_email"] = "founder@startup.com"
    company["founder_email_status"] = "bounced"

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "gmail_tokens":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                {"encrypted_refresh_token": "enc-tok", "gmail_email": "me@gmail.com"}
            ]
        elif table_name == "companies":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [company]
        return mock_table

    mock_db.table.side_effect = table_side_effect

    with _mock_auth(), patch("backend.routers.email.get_db", return_value=mock_db):
        response = client.post(
            "/email/send",
            json={"company_id": 1, "subject_line": "Hi", "final_text": "Hello", "original_draft": "Hello"},
            headers=auth_headers,
        )

    assert response.status_code == 400
    assert "bounced" in response.json()["detail"].lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/api/test_email_router.py::test_send_rejects_bounced_email -v`
Expected: FAIL — response is 200 or different error (no bounce guard yet)

- [ ] **Step 3: Add bounce guard to send endpoint**

In `backend/routers/email.py`, in the `send_email_endpoint` function, add after the `if not founder_email:` check (after line 151):

```python
    if company.get("founder_email_status") == "bounced":
        raise HTTPException(
            status_code=400,
            detail="This founder's email previously bounced. The address may be invalid.",
        )
```

Also update the companies select to include the new column. Change line 143:

```python
    company_result = db.table("companies").select("founder_email, founder_email_status, name").eq("id", body.company_id).execute()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/api/test_email_router.py::test_send_rejects_bounced_email -v`
Expected: PASS

- [ ] **Step 5: Run all email router tests for regressions**

Run: `pytest tests/api/test_email_router.py -v`
Expected: All tests pass (existing + 2 new)

- [ ] **Step 6: Commit**

```bash
git add backend/routers/email.py tests/api/test_email_router.py
git commit -m "feat: block sends to previously-bounced email addresses"
```

---

### Task 5: Final integration test run

**Files:** None (verification only)

- [ ] **Step 1: Run full email test suite**

Run: `pytest tests/email/ -v`
Expected: 9 passed (5 existing + 4 new bounce tests)

- [ ] **Step 2: Run full API router test suite**

Run: `pytest tests/api/test_email_router.py -v`
Expected: All pass (existing + 2 new)

- [ ] **Step 3: Run all tests to check for regressions**

Run: `pytest tests/ -v --timeout=30`
Expected: No new failures beyond any pre-existing collection errors
