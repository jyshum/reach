"""Resume PDF upload, delete, and public redirect endpoints."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import RedirectResponse

from backend.auth import get_current_user
from backend.db import get_db

router = APIRouter()

MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB
BUCKET = "resumes"


@router.post("/me/resume")
async def upload_resume(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
):
    """Upload a resume PDF to Supabase Storage."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    if file.content_type and file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 2MB.")

    db = get_db()
    path = f"{user_id}/resume.pdf"

    db.storage.from_(BUCKET).upload(
        path,
        content,
        file_options={"content-type": "application/pdf", "upsert": "true"},
    )

    public_url = db.storage.from_(BUCKET).get_public_url(path)

    # Derive slug from user email (e.g. "jshum" from "jshum@example.com")
    user_result = db.table("users").select("email").eq("id", user_id).execute()
    slug = user_id  # fallback
    if user_result.data and user_result.data[0].get("email"):
        slug = user_result.data[0]["email"].split("@")[0]

    db.table("users").update({
        "resume_url": public_url,
        "resume_slug": slug,
    }).eq("id", user_id).execute()

    return {"resume_url": public_url, "resume_slug": slug}


@router.delete("/me/resume")
def delete_resume(user_id: str = Depends(get_current_user)):
    """Delete resume from storage and clear URL."""
    db = get_db()
    path = f"{user_id}/resume.pdf"

    db.storage.from_(BUCKET).remove([path])
    db.table("users").update({"resume_url": None, "resume_slug": None}).eq("id", user_id).execute()

    return {"ok": True}


@router.get("/resume/{slug}")
def public_resume(slug: str):
    """Redirect a friendly resume URL to the actual Supabase storage URL."""
    db = get_db()
    result = db.table("users").select("resume_url").eq("resume_slug", slug).execute()
    if not result.data or not result.data[0].get("resume_url"):
        raise HTTPException(status_code=404, detail="Resume not found")
    return RedirectResponse(result.data[0]["resume_url"])
