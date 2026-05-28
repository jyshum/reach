"""Company browsing and brief endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from backend.auth import get_current_user, get_optional_user
from backend.db import get_db
from backend.matching.scorer import rank_companies, match_score
from backend.guidance.rules import generate_guidance
from backend.scoring.reachability import compute_reachability, bucket_score
from backend.schemas import CompanyCard, CompanyBrief

router = APIRouter()


@router.get("/companies", response_model=list[CompanyCard])
def list_companies(
    request: Request,
    industry: str | None = Query(None),
    reachability: str | None = Query(None),
    search: str | None = Query(None),
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
    if search:
        query = query.or_(f"name.ilike.%{search}%,founder_name.ilike.%{search}%")

    result = query.execute()
    companies = result.data

    # Get user interests and location if authenticated
    user_interests = None
    student_location = None
    if user_id:
        user_result = db.table("users").select("interests, location").eq("id", user_id).execute()
        if user_result.data:
            user_interests = user_result.data[0].get("interests")
            student_location = user_result.data[0].get("location")

    # Compute reachability scores on the fly
    for company in companies:
        score, factors = compute_reachability(company, student_location)
        company["reachability_probability"] = score
        company["reachability_score"] = bucket_score(score)

    # Rank and paginate
    ranked = rank_companies(companies, user_interests)
    start = (page - 1) * limit
    return ranked[start:start + limit]


@router.get("/companies/{company_id}", response_model=CompanyBrief)
def get_brief(
    company_id: int,
    request: Request,
    user_id: str = Depends(get_current_user),
):
    """Get full company brief."""
    db = get_db()

    # Get company
    result = db.table("companies").select("*").eq("id", company_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Company not found")
    company = result.data[0]

    # Get user for matching and location
    user_result = db.table("users").select("interests, location").eq("id", user_id).execute()
    user = user_result.data[0] if user_result.data else {"interests": [], "location": None}

    # Record the view (ignore if already exists due to unique constraint)
    try:
        db.table("brief_views").insert({"user_id": user_id, "company_id": company_id}).execute()
    except Exception:
        pass  # Already viewed — unique constraint prevents duplicate

    # Compute reachability
    user_interests = user.get("interests", []) or []
    student_location = user.get("location")
    score, factors = compute_reachability(company, student_location)
    company["reachability_probability"] = score
    company["reachability_score"] = bucket_score(score)
    company["reachability_factors"] = factors

    # Match score and guidance
    ms = match_score(user_interests, company.get("yc_tags") or [])
    company["match_score"] = ms
    company["guidance"] = generate_guidance(user_interests, company)

    return company
