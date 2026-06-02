# Bounce Detection Design

**Date:** 2026-06-01
**Status:** Approved

## Problem

When a user sends an email via REACH's Gmail integration and the address is invalid, the email bounces — but REACH never tells the user. The `check_thread_for_reply` function only checks `len(messages) > 1`, which actually counts a bounce-back NDR as a "reply." The user sees "replied" status when the email was never delivered.

This is worst for low-confidence pattern-guessed emails (`first@domain.com` verified only by MX record), which are the most likely to bounce.

## Solution

Add bounce detection to the reply-checking flow. When checking a thread for replies, first check if any message in the thread is a bounce (NDR). If so, mark the email as bounced and flag the company's email globally.

## Design

### 1. New function: `check_thread_for_bounce()`

**File:** `backend/email/gmail.py`

```python
check_thread_for_bounce(service, thread_id, sender_email) -> bool
```

Fetches the thread with `format="metadata"`, requesting headers: `From`, `Subject`, `X-Failed-Recipients`.

For each message in the thread that is NOT from the sender, checks for bounce indicators (any one triggers):
- `From` contains `mailer-daemon`, `postmaster`, or `mail delivery subsystem` (case-insensitive)
- `Subject` contains `delivery status notification`, `undeliverable`, `mail delivery failed`, or `returned to sender` (case-insensitive)
- `X-Failed-Recipients` header is present

Returns `True` if any message matches.

### 2. Updated `/email/check-replies` endpoint

**File:** `backend/routers/email.py`

New flow per sent email:

1. `check_thread_for_bounce()` — if True:
   - `email_log.status` → `"bounced"`
   - `outreach_log.status` → `"bounced"`
   - `companies.founder_email_status` → `"bounced"`
   - Skip reply check, move to next email
2. `check_thread_for_reply()` — if True:
   - `email_log.status` → `"replied"` (unchanged)
   - `outreach_log.status` → `"replied"` (unchanged)

Updated response:
```json
{
  "replies_found": 1,
  "bounces_found": 2,
  "checked": 5
}
```

### 3. Send endpoint guard

**File:** `backend/routers/email.py`

The `POST /email/send` endpoint will check `companies.founder_email_status` before sending. If `"bounced"`, reject with 400: "This founder's email previously bounced. The address may be invalid."

### 4. Schema changes

**`email_log.status` constraint:**
```sql
status in ('draft', 'sent', 'replied', 'no_response', 'bounced')
```

**`outreach_log.status` constraint:**
```sql
status in ('sent', 'replied', 'meeting', 'no-response', 'bounced')
```

**`companies` table — new column:**
```sql
founder_email_status text default 'unknown'
```
Values: `'unknown'`, `'bounced'`. Flags bad emails globally so no user tries them again.

Migration ALTER statements added as a comment block in `schema.sql` for manual execution in Supabase SQL Editor.

### 5. Tests

**`tests/email/test_gmail.py`:**
- `test_check_thread_for_bounce_detects_mailer_daemon` — From header with MAILER-DAEMON
- `test_check_thread_for_bounce_detects_failed_recipients_header` — X-Failed-Recipients present
- `test_check_thread_for_bounce_ignores_real_reply` — normal human reply, returns False
- `test_check_thread_for_bounce_no_extra_messages` — single-message thread, returns False

**`tests/api/test_email_router.py`:**
- `test_check_replies_detects_bounce` — bounce detected, statuses updated, company flagged
- `test_send_rejects_bounced_email` — 400 when founder_email_status is bounced

## What this does NOT cover

- Background/automatic bounce polling (still manual via endpoint)
- Frontend UI changes to show bounce status (tracker page will need update separately)
- Re-resolving bounced emails with a different address
