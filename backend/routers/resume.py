"""Resume PDF upload and delete endpoints."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

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

    db.table("users").update({"resume_url": public_url}).eq("id", user_id).execute()

    return {"resume_url": public_url}


@router.delete("/me/resume")
def delete_resume(user_id: str = Depends(get_current_user)):
    """Delete resume from storage and clear URL."""
    db = get_db()
    path = f"{user_id}/resume.pdf"

    db.storage.from_(BUCKET).remove([path])
    db.table("users").update({"resume_url": None}).eq("id", user_id).execute()

    return {"ok": True}
