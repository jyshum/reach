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
