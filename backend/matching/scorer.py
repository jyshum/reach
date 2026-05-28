"""Match scoring: rank companies by interest overlap, reachability as tiebreaker.

New matching logic: count overlapping curated tags between user's interests
and company's yc_tags. Sort by match_score descending, then by
reachability_probability descending. No weighted formula.
"""


def match_score(user_interests: list[str], company_tags: list[str]) -> int:
    """Count overlapping curated tags between user interests and company tags."""
    if not user_interests or not company_tags:
        return 0
    return len(set(user_interests) & set(company_tags))


def rank_companies(
    companies: list[dict],
    user_interests: list[str] | None = None,
) -> list[dict]:
    """Rank companies: match_score descending, reachability as tiebreaker.

    Companies with zero overlap are still returned, ranked below matches.
    If user has no interests, rank by reachability only.
    """
    scored = []
    for company in companies:
        company_tags = company.get("yc_tags") or []
        reachability = company.get("reachability_probability", 0.0) or 0.0

        if user_interests:
            ms = match_score(user_interests, company_tags)
        else:
            ms = 0

        scored.append({**company, "match_score": ms})

    scored.sort(key=lambda c: (c["match_score"], c.get("reachability_probability", 0.0) or 0.0), reverse=True)
    return scored
