"""Email pipeline endpoints: Gmail OAuth, generation, send, reply checking."""

from datetime import datetime, timedelta, timezone

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
from backend.email.gmail import build_gmail_service, send_email, check_thread_for_reply, check_thread_for_bounce
from backend.email.generate import generate_draft
from backend.schemas import EmailGenerate, EmailDraft, EmailSend, GmailStatus

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

    service = build_gmail_service(access_token)
    profile = service.users().getProfile(userId="me").execute()
    gmail_email = profile["emailAddress"]

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


# --- Email Generation ---


@router.post("/generate", response_model=EmailDraft)
def generate_email(body: EmailGenerate, user_id: str = Depends(get_current_user)):
    """Generate a cold email draft for a company."""
    db = get_db()

    company_result = db.table("companies").select("*").eq("id", body.company_id).execute()
    if not company_result.data:
        raise HTTPException(status_code=404, detail="Company not found")
    company = company_result.data[0]

    user_result = db.table("users").select(
        "interests, bio, portfolio_url, github_url, resume_url, resume_slug"
    ).eq("id", user_id).execute()
    user = user_result.data[0] if user_result.data else {}

    repos_result = db.table("user_repos").select(
        "repo_name, summary, language, stars"
    ).eq("user_id", user_id).execute()
    repo_summaries = repos_result.data if repos_result.data else []

    # Use clean resume URL if slug exists, otherwise raw URL
    resume_link = None
    if user.get("resume_slug"):
        resume_link = f"https://reachyc.com/resume/{user['resume_slug']}"
    elif user.get("resume_url"):
        resume_link = user["resume_url"]

    subject_line, draft = generate_draft(
        student_bio=user.get("bio") or "High school student",
        repo_summaries=repo_summaries,
        student_interests=user.get("interests") or [],
        signature_links={
            "github_url": user.get("github_url"),
            "resume_url": resume_link,
            "portfolio_url": user.get("portfolio_url"),
        },
        company_name=company.get("name", ""),
        company_summary=company.get("summary") or company.get("description") or "",
        specific_projects=company.get("specific_projects") or [],
        founder_name=company.get("founder_name") or "the founder",
        founder_bio=company.get("founder_bio"),
        tone=body.tone,
    )

    return {
        "draft": draft,
        "subject_line": subject_line,
        "tone": body.tone,
        "company_id": body.company_id,
        "company_name": company.get("name", ""),
        "founder_name": company.get("founder_name"),
    }


# --- Email Sending ---


@router.post("/send")
def send_email_endpoint(body: EmailSend, user_id: str = Depends(get_current_user)):
    """Send an email via the user's connected Gmail account."""
    db = get_db()

    token_result = db.table("gmail_tokens").select("encrypted_refresh_token, gmail_email").eq("user_id", user_id).execute()
    if not token_result.data:
        raise HTTPException(status_code=400, detail="Gmail not connected. Please connect your Gmail account first.")

    token_row = token_result.data[0]

    company_result = db.table("companies").select("founder_email, founder_email_status, name").eq("id", body.company_id).execute()
    if not company_result.data:
        raise HTTPException(status_code=404, detail="Company not found")

    company = company_result.data[0]
    founder_email = company.get("founder_email")
    if not founder_email:
        raise HTTPException(status_code=400, detail="No email address found for this founder")

    if company.get("founder_email_status") == "bounced":
        raise HTTPException(
            status_code=400,
            detail="This founder's email previously bounced. The address may be invalid.",
        )

    refresh_token = decrypt_token(token_row["encrypted_refresh_token"])
    access_token = refresh_access_token(refresh_token)
    service = build_gmail_service(access_token)

    result = send_email(
        service=service,
        to=founder_email,
        subject=body.subject_line,
        body=body.final_text,
        sender_email=token_row["gmail_email"],
    )

    now = datetime.now(timezone.utc).isoformat()

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


# --- Reply Checking ---


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
