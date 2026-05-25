from backend.matching.scorer import match_score, rank_companies


def test_match_score_full_overlap():
    user_caps = ["frontend-development", "backend-apis", "data-pipelines"]
    company_caps = ["frontend-development", "backend-apis", "data-pipelines"]
    assert match_score(user_caps, company_caps) == 3


def test_match_score_partial_overlap():
    user_caps = ["frontend-development", "backend-apis"]
    company_caps = ["frontend-development", "deep-learning", "ui-design"]
    assert match_score(user_caps, company_caps) == 1


def test_match_score_no_overlap():
    user_caps = ["ui-design", "ux-research"]
    company_caps = ["frontend-development", "data-pipelines"]
    assert match_score(user_caps, company_caps) == 0


def test_match_score_empty():
    assert match_score([], ["frontend-development"]) == 0
    assert match_score(["frontend-development"], []) == 0
    assert match_score([], []) == 0


def test_rank_uses_capability_tags():
    companies = [
        {"id": 1, "name": "NoMatch", "capability_tags": ["ui-design"], "reachability_probability": 0.9},
        {"id": 2, "name": "FullMatch", "capability_tags": ["frontend-development", "backend-apis"], "reachability_probability": 0.5},
        {"id": 3, "name": "PartialMatch", "capability_tags": ["frontend-development"], "reachability_probability": 0.7},
    ]
    user_caps = ["frontend-development", "backend-apis"]
    ranked = rank_companies(companies, user_caps)

    assert ranked[0]["name"] == "FullMatch"
    assert ranked[0]["match_score"] == 2


def test_rank_no_caps_uses_reachability_only():
    companies = [
        {"id": 1, "name": "Low", "capability_tags": ["x"], "reachability_probability": 0.3},
        {"id": 2, "name": "High", "capability_tags": ["y"], "reachability_probability": 0.9},
    ]
    ranked = rank_companies(companies, user_capabilities=None)

    assert ranked[0]["name"] == "High"
    assert ranked[1]["name"] == "Low"


def test_rank_falls_back_to_need_tags():
    """Companies without capability_tags yet should fall back to need_tags."""
    companies = [
        {"id": 1, "name": "OldData", "need_tags": ["frontend-development"], "reachability_probability": 0.5},
    ]
    ranked = rank_companies(companies, ["frontend-development"])
    assert ranked[0]["match_score"] == 1
