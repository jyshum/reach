"""GitHub repo summarization endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from backend.auth import get_current_user
from backend.db import get_db
from backend.schemas import RepoCreate, RepoResponse
from backend.github_fetcher import fetch_repo_metadata, validate_repo_url
from backend.summarizer import summarize_repo

router = APIRouter()

MAX_REPOS = 3
MAX_SUMMARIZATIONS = 10


@router.post("/me/repos", response_model=RepoResponse)
def create_repo(body: RepoCreate, user_id: str = Depends(get_current_user)):
    """Summarize a GitHub repo and store it."""
    try:
        owner, repo = validate_repo_url(body.repo_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    db = get_db()

    user_result = db.table("users").select("summarization_count").eq("id", user_id).execute()
    summarization_count = user_result.data[0].get("summarization_count", 0) if user_result.data else 0
    if summarization_count >= MAX_SUMMARIZATIONS:
        raise HTTPException(status_code=400, detail="You've used all 10 project summarizations.")

    existing = db.table("user_repos").select("id").eq("user_id", user_id).execute()
    if len(existing.data) >= MAX_REPOS:
        raise HTTPException(status_code=400, detail="You can store up to 3 repos. Remove one to add another.")

    try:
        metadata = fetch_repo_metadata(owner, repo)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    summary = summarize_repo(
        repo_name=metadata["repo_name"],
        readme=metadata["readme"],
        language=metadata["language"],
        description=metadata["description"],
        stars=metadata["stars"],
    )

    insert_result = db.table("user_repos").insert({
        "user_id": user_id,
        "repo_url": body.repo_url,
        "repo_name": metadata["repo_name"],
        "summary": summary,
        "language": metadata["language"],
        "stars": metadata["stars"],
    }).execute()

    db.table("users").update({
        "summarization_count": summarization_count + 1,
    }).eq("id", user_id).execute()

    row = insert_result.data[0]
    return {
        **row,
        "warning": metadata["warning"],
    }


@router.get("/me/repos", response_model=list[RepoResponse])
def list_repos(user_id: str = Depends(get_current_user)):
    """List all repos for the current user (max 3)."""
    db = get_db()
    result = db.table("user_repos").select("*").eq("user_id", user_id).execute()
    return result.data


@router.delete("/me/repos/{repo_id}")
def delete_repo(repo_id: int, user_id: str = Depends(get_current_user)):
    """Remove a repo slot. Does NOT decrement summarization count."""
    db = get_db()
    db.table("user_repos").delete().eq("id", repo_id).eq("user_id", user_id).execute()
    return {"ok": True}
