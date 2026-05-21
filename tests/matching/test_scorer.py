from backend.matching.scorer import match_score, rank_companies


def test_match_score_full_overlap():
    user_skills = ["python scripting", "react frontend", "data analysis"]
    company_tags = ["python scripting", "react frontend", "data analysis"]
    assert match_score(user_skills, company_tags) == 3


def test_match_score_partial_overlap():
    user_skills = ["python scripting", "react frontend"]
    company_tags = ["python scripting", "data analysis", "graphic design"]
    assert match_score(user_skills, company_tags) == 1


def test_match_score_no_overlap():
    user_skills = ["video editing", "photography"]
    company_tags = ["python scripting", "data analysis"]
    assert match_score(user_skills, company_tags) == 0


def test_match_score_empty_skills():
    assert match_score([], ["python scripting"]) == 0
    assert match_score(["python scripting"], []) == 0
    assert match_score([], []) == 0


def test_rank_companies_with_skills():
    companies = [
        {"id": 1, "name": "LowMatch", "need_tags": ["video editing"], "reachability_probability": 0.9},
        {"id": 2, "name": "HighMatch", "need_tags": ["python scripting", "react frontend"], "reachability_probability": 0.5},
        {"id": 3, "name": "MedMatch", "need_tags": ["python scripting"], "reachability_probability": 0.7},
    ]
    user_skills = ["python scripting", "react frontend"]
    ranked = rank_companies(companies, user_skills)

    # HighMatch has best combined score (2 skill matches + 0.5 reachability)
    assert ranked[0]["name"] == "HighMatch"
    assert "match_score" in ranked[0]


def test_rank_companies_no_skills():
    companies = [
        {"id": 1, "name": "Low", "need_tags": ["x"], "reachability_probability": 0.3},
        {"id": 2, "name": "High", "need_tags": ["y"], "reachability_probability": 0.9},
        {"id": 3, "name": "Med", "need_tags": ["z"], "reachability_probability": 0.6},
    ]
    ranked = rank_companies(companies, user_skills=None)

    # With no skills, rank by reachability only
    assert ranked[0]["name"] == "High"
    assert ranked[1]["name"] == "Med"
    assert ranked[2]["name"] == "Low"


def test_rank_companies_includes_match_score():
    companies = [
        {"id": 1, "name": "Co", "need_tags": ["python scripting", "react frontend"], "reachability_probability": 0.8},
    ]
    ranked = rank_companies(companies, ["python scripting"])

    assert ranked[0]["match_score"] == 1
