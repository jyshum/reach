"""Match scoring: rank companies by skill overlap + reachability."""

# Weights for combining match score and reachability
REACHABILITY_WEIGHT = 0.4
MATCH_WEIGHT = 0.6
# Max match score for normalization (assumes user picks ~5 skills)
MAX_MATCH_SCORE = 5


def match_score(user_skills: list[str], company_tags: list[str]) -> int:
    """Count overlapping skills between user and company."""
    if not user_skills or not company_tags:
        return 0
    return len(set(user_skills) & set(company_tags))


def rank_companies(
    companies: list[dict],
    user_skills: list[str] | None = None,
) -> list[dict]:
    """Rank companies by combined match + reachability score.

    Each company dict gets a 'match_score' and 'rank_score' field added.
    Returns a new list sorted by rank_score descending.
    """
    scored = []
    for company in companies:
        company_tags = company.get("need_tags", []) or []
        reachability = company.get("reachability_probability", 0.0) or 0.0

        if user_skills:
            ms = match_score(user_skills, company_tags)
            normalized_match = min(ms / MAX_MATCH_SCORE, 1.0)
            rank = (REACHABILITY_WEIGHT * reachability) + (MATCH_WEIGHT * normalized_match)
        else:
            ms = 0
            rank = reachability

        scored.append({**company, "match_score": ms, "rank_score": round(rank, 4)})

    scored.sort(key=lambda c: c["rank_score"], reverse=True)
    return scored
