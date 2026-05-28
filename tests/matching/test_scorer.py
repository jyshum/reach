"""Tests for interest-based matching scorer."""

from backend.matching.scorer import match_score, rank_companies


def test_match_score_full_overlap():
    user_interests = ["Generative AI", "Developer Tools"]
    company_tags = ["Generative AI", "Developer Tools", "Open Source"]
    assert match_score(user_interests, company_tags) == 2


def test_match_score_partial_overlap():
    user_interests = ["Generative AI", "Fintech"]
    company_tags = ["Generative AI", "Healthcare"]
    assert match_score(user_interests, company_tags) == 1


def test_match_score_no_overlap():
    user_interests = ["Fintech", "Payments"]
    company_tags = ["Generative AI", "Developer Tools"]
    assert match_score(user_interests, company_tags) == 0


def test_match_score_empty():
    assert match_score([], ["Generative AI"]) == 0
    assert match_score(["Generative AI"], []) == 0
    assert match_score([], []) == 0


def test_rank_matches_first_then_reachability():
    companies = [
        {"id": 1, "name": "HighReachNoMatch", "yc_tags": ["Healthcare"], "reachability_probability": 0.95},
        {"id": 2, "name": "LowReachFullMatch", "yc_tags": ["Generative AI", "Fintech"], "reachability_probability": 0.3},
        {"id": 3, "name": "MidReachOneMatch", "yc_tags": ["Generative AI", "Healthcare"], "reachability_probability": 0.6},
    ]
    ranked = rank_companies(companies, ["Generative AI", "Fintech"])

    # Full match (2) comes first despite lowest reachability
    assert ranked[0]["name"] == "LowReachFullMatch"
    assert ranked[0]["match_score"] == 2
    # Partial match (1) second
    assert ranked[1]["name"] == "MidReachOneMatch"
    assert ranked[1]["match_score"] == 1
    # No match last despite highest reachability
    assert ranked[2]["name"] == "HighReachNoMatch"
    assert ranked[2]["match_score"] == 0


def test_rank_tiebreaks_by_reachability():
    companies = [
        {"id": 1, "name": "LowReach", "yc_tags": ["Generative AI"], "reachability_probability": 0.3},
        {"id": 2, "name": "HighReach", "yc_tags": ["Generative AI"], "reachability_probability": 0.9},
    ]
    ranked = rank_companies(companies, ["Generative AI"])

    # Same match score, higher reachability wins
    assert ranked[0]["name"] == "HighReach"
    assert ranked[1]["name"] == "LowReach"


def test_rank_no_interests_uses_reachability_only():
    companies = [
        {"id": 1, "name": "Low", "yc_tags": ["AI"], "reachability_probability": 0.3},
        {"id": 2, "name": "High", "yc_tags": ["AI"], "reachability_probability": 0.9},
    ]
    ranked = rank_companies(companies, user_interests=None)
    assert ranked[0]["name"] == "High"


def test_rank_zero_match_still_included():
    companies = [
        {"id": 1, "name": "NoMatch", "yc_tags": ["Healthcare"], "reachability_probability": 0.9},
    ]
    ranked = rank_companies(companies, ["Fintech"])
    assert len(ranked) == 1
