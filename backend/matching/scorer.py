"""Match scoring: rank companies by capability overlap + reachability."""

REACHABILITY_WEIGHT = 0.4
MATCH_WEIGHT = 0.6
MAX_MATCH_SCORE = 3  # Students pick up to 3 tier-2 capabilities


def match_score(user_capabilities: list[str], company_capabilities: list[str]) -> int:
    """Count overlapping capabilities between user and company."""
    if not user_capabilities or not company_capabilities:
        return 0
    return len(set(user_capabilities) & set(company_capabilities))


def rank_companies(
    companies: list[dict],
    user_capabilities: list[str] | None = None,
) -> list[dict]:
    """Rank companies by combined match + reachability score.

    Uses capability_tags for matching, falls back to need_tags if
    capability_tags is empty (for companies not yet re-enriched).
    """
    scored = []
    for company in companies:
        company_caps = company.get("capability_tags") or []
        if not company_caps:
            company_caps = company.get("need_tags") or []
        reachability = company.get("reachability_probability", 0.0) or 0.0

        if user_capabilities:
            ms = match_score(user_capabilities, company_caps)
            normalized_match = min(ms / MAX_MATCH_SCORE, 1.0)
            rank = (REACHABILITY_WEIGHT * reachability) + (MATCH_WEIGHT * normalized_match)
        else:
            ms = 0
            rank = reachability

        scored.append({**company, "match_score": ms, "rank_score": round(rank, 4)})

    scored.sort(key=lambda c: c["rank_score"], reverse=True)
    return scored
