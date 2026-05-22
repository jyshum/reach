"""Company browsing and brief endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from backend.auth import get_current_user, get_optional_user
from backend.db import get_db
from backend.matching.scorer import rank_companies, match_score
from backend.guidance.rules import generate_guidance
from backend.schemas import CompanyCard, CompanyBrief

router = APIRouter()

FREE_BRIEF_LIMIT = 3


@router.get("/companies", response_model=list[CompanyCard])
def list_companies(
    request: Request,
    industry: str | None = Query(None),
    reachability: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
):
    """Browse company cards. Ranked by match score if authenticated."""
    db = get_db()
    user_id = get_optional_user(request)

    # Build query
    query = db.table("companies").select("*").eq("status", "Active")

    if industry:
        query = query.eq("industry", industry)
    if reachability:
        query = query.eq("reachability_score", reachability)

    result = query.execute()
    companies = result.data

    # Get user skills if authenticated
    user_skills = None
    if user_id:
        user_result = db.table("users").select("skills").eq("id", user_id).execute()
        if user_result.data and user_result.data[0].get("skills"):
            user_skills = user_result.data[0]["skills"]

    # Rank and paginate
    ranked = rank_companies(companies, user_skills)
    start = (page - 1) * limit
    return ranked[start:start + limit]


@router.get("/companies/{company_id}", response_model=CompanyBrief)
def get_brief(
    company_id: int,
    request: Request,
    user_id: str = Depends(get_current_user),
):
    """Get full company brief. Gated by tier for free users."""
    db = get_db()

    # Get company
    result = db.table("companies").select("*").eq("id", company_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Company not found")
    company = result.data[0]

    # Get user for tier check
    user_result = db.table("users").select("skills, tier").eq("id", user_id).execute()
    user = user_result.data[0] if user_result.data else {"skills": [], "tier": "free"}

    # Check brief limit for free tier
    if user["tier"] == "free":
        views_result = db.table("brief_views").select("company_id").eq("user_id", user_id).execute()
        viewed_ids = [v["company_id"] for v in views_result.data]

        if company_id not in viewed_ids and len(viewed_ids) >= FREE_BRIEF_LIMIT:
            raise HTTPException(status_code=403, detail="Free tier limit reached. Upgrade to unlock more briefs.")

    # Record the view (ignore if already exists due to unique constraint)
    try:
        db.table("brief_views").insert({"user_id": user_id, "company_id": company_id}).execute()
    except Exception:
        pass  # Already viewed — unique constraint prevents duplicate

    # Add match score and guidance
    user_skills = user.get("skills", []) or []
    ms = match_score(user_skills, company.get("need_tags", []) or [])
    company["match_score"] = ms
    company["guidance"] = generate_guidance(user_skills, company)

    return company
