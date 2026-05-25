from backend.scoring.reachability import compute_reachability


def test_small_team_building_mvp_hiring_nearby_contactable():
    """Perfect reachability: all factors present."""
    company = {
        "team_size": 3,
        "stage_detail": "building-mvp",
        "is_hiring": True,
        "founder_linkedin": "https://linkedin.com/in/founder",
        "founder_twitter": None,
        "all_locations": "San Francisco, CA",
    }
    score, factors = compute_reachability(company, student_location="San Francisco")
    assert score >= 0.9
    assert "Small team" in factors
    assert "Building MVP" in factors
    assert "Hiring" in factors
    assert "Near you" in factors
    assert "LinkedIn" in factors or "Twitter" in factors


def test_large_team_scaling_no_contact():
    """Worst reachability: no factors present."""
    company = {
        "team_size": 50,
        "stage_detail": "scaling",
        "is_hiring": False,
        "founder_linkedin": None,
        "founder_twitter": None,
        "all_locations": "London, UK",
    }
    score, factors = compute_reachability(company, student_location="San Francisco")
    assert score == 0.0
    assert factors == []


def test_missing_team_size_no_penalty():
    """None team_size should not contribute but not crash."""
    company = {
        "team_size": None,
        "stage_detail": "building-mvp",
        "is_hiring": True,
        "founder_linkedin": "https://linkedin.com/in/x",
        "founder_twitter": None,
        "all_locations": None,
    }
    score, factors = compute_reachability(company)
    assert score > 0.0
    assert "Small team" not in factors


def test_no_student_location_skips_proximity():
    """Without student location, proximity factor is skipped."""
    company = {
        "team_size": 2,
        "stage_detail": "launched",
        "is_hiring": False,
        "founder_linkedin": None,
        "founder_twitter": "https://twitter.com/founder",
        "all_locations": "San Francisco, CA",
    }
    score, factors = compute_reachability(company, student_location=None)
    assert "Near you" not in factors


def test_score_bucketing():
    """Score converts to high/medium/low labels correctly."""
    from backend.scoring.reachability import bucket_score
    assert bucket_score(0.75) == "high"
    assert bucket_score(0.5) == "medium"
    assert bucket_score(0.3) == "low"
    assert bucket_score(0.7) == "high"
    assert bucket_score(0.4) == "medium"
    assert bucket_score(0.39) == "low"


def test_location_match_case_insensitive():
    """Location matching should be case-insensitive substring."""
    company = {
        "team_size": 3,
        "stage_detail": "building-mvp",
        "is_hiring": False,
        "founder_linkedin": None,
        "founder_twitter": None,
        "all_locations": "San Francisco, CA",
    }
    score_match, factors_match = compute_reachability(company, student_location="san francisco")
    score_no, factors_no = compute_reachability(company, student_location="New York")
    assert "Near you" in factors_match
    assert "Near you" not in factors_no
    assert score_match > score_no
