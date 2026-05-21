"""Outreach tracking endpoints."""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from backend.auth import get_current_user
from backend.db import get_db
from backend.schemas import OutreachCreate, OutreachUpdate, OutreachEntry

router = APIRouter()

FOLLOWUP_DAYS = 5


@router.get("/outreach", response_model=list[OutreachEntry])
def list_outreach(user_id: str = Depends(get_current_user)):
    """List user's outreach log with company names."""
    db = get_db()

    result = db.table("outreach_log").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
    entries = result.data

    if not entries:
        return []

    # Fetch company names for display
    company_ids = list({e["company_id"] for e in entries})
    companies_result = db.table("companies").select("id, name").in_("id", company_ids).execute()
    name_map = {c["id"]: c["name"] for c in companies_result.data}

    for entry in entries:
        entry["company_name"] = name_map.get(entry["company_id"])

    return entries


@router.post("/outreach", response_model=OutreachEntry, status_code=201)
def create_outreach(body: OutreachCreate, user_id: str = Depends(get_current_user)):
    """Log a new outreach entry."""
    db = get_db()

    record = {
        "user_id": user_id,
        "company_id": body.company_id,
        "status": body.status,
        "notes": body.notes,
        "sent_at": body.sent_at,
    }

    # Compute followup date if sent_at is provided
    if body.sent_at:
        try:
            sent_dt = datetime.fromisoformat(body.sent_at.replace("Z", "+00:00"))
            record["followup_date"] = (sent_dt + timedelta(days=FOLLOWUP_DAYS)).isoformat()
        except ValueError:
            pass

    result = db.table("outreach_log").insert(record).execute()
    return result.data[0]


@router.put("/outreach/{outreach_id}", response_model=OutreachEntry)
def update_outreach(outreach_id: int, body: OutreachUpdate, user_id: str = Depends(get_current_user)):
    """Update an outreach entry's status or notes."""
    db = get_db()

    # Verify ownership
    check = db.table("outreach_log").select("id").eq("id", outreach_id).eq("user_id", user_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Outreach entry not found")

    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Nothing to update")

    result = db.table("outreach_log").update(update_data).eq("id", outreach_id).execute()
    return result.data[0]
