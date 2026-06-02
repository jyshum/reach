"""Gmail API helpers for sending emails and checking replies."""

import base64
from email.mime.text import MIMEText
from email.utils import parseaddr

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
    """Send an email via Gmail API. Returns dict with 'message_id' and 'thread_id'."""
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
    """Check if a Gmail thread has a reply (more than one message)."""
    thread = service.users().threads().get(
        userId="me", id=thread_id, format="minimal"
    ).execute()

    messages = thread.get("messages", [])
    return len(messages) > 1


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

        from_raw = headers.get("from", "")
        _, from_email = parseaddr(from_raw)
        from_lower = from_email.lower()
        if from_lower == sender_lower:
            continue

        # Check X-Failed-Recipients header
        if "x-failed-recipients" in headers:
            return True

        # Check From for bounce senders
        if any(sender in from_lower for sender in BOUNCE_SENDERS):
            return True

        # Check Subject for bounce patterns
        subject = headers.get("subject", "").lower()
        if any(pattern in subject for pattern in BOUNCE_SUBJECTS):
            return True

    return False
