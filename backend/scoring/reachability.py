"""Rule-based reachability scoring for companies."""

# Weights must sum to 1.0
TEAM_SIZE_WEIGHT = 0.30
STAGE_WEIGHT = 0.25
HIRING_WEIGHT = 0.20
LOCATION_WEIGHT = 0.15
CONTACT_WEIGHT = 0.10

SMALL_TEAM_MAX = 5
HIGH_THRESHOLD = 0.70
LOW_THRESHOLD = 0.40


def compute_reachability(
    company: dict,
    student_location: str | None = None,
) -> tuple[float, list[str]]:
    """Compute rule-based reachability score.

    Returns (score 0.0-1.0, list of contributing factor labels).
    """
    score = 0.0
    factors: list[str] = []

    # Factor 1: Team size
    team_size = company.get("team_size")
    if team_size is not None and 1 <= team_size <= SMALL_TEAM_MAX:
        score += TEAM_SIZE_WEIGHT
        factors.append("Small team")

    # Factor 2: Stage
    stage = company.get("stage_detail")
    if stage == "building-mvp":
        score += STAGE_WEIGHT
        factors.append("Building MVP")
    elif stage == "launched":
        score += STAGE_WEIGHT * 0.6
        factors.append("Recently launched")

    # Factor 3: Hiring
    if company.get("is_hiring"):
        score += HIRING_WEIGHT
        factors.append("Hiring")

    # Factor 4: Location proximity
    company_location = company.get("all_locations") or ""
    if student_location and company_location:
        if student_location.lower() in company_location.lower():
            score += LOCATION_WEIGHT
            factors.append("Near you")

    # Factor 5: Contactable
    has_linkedin = bool(company.get("founder_linkedin"))
    has_twitter = bool(company.get("founder_twitter"))
    if has_linkedin or has_twitter:
        score += CONTACT_WEIGHT
        if has_linkedin:
            factors.append("LinkedIn")
        if has_twitter:
            factors.append("Twitter")

    return round(score, 4), factors


def bucket_score(score: float) -> str:
    """Convert 0-1 score to high/medium/low label."""
    if score >= HIGH_THRESHOLD:
        return "high"
    elif score >= LOW_THRESHOLD:
        return "medium"
    return "low"
