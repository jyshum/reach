"""Tests for outreach guidance rules engine."""

from backend.schemas import Guidance, CompanyBrief


def test_guidance_model_fields():
    g = Guidance(
        your_angle="Lead with Python",
        reference_this="Their enzyme platform",
        dont_say="Don't say you're passionate",
        your_ask="Offer to build a dashboard",
    )
    assert g.your_angle == "Lead with Python"
    assert g.reference_this == "Their enzyme platform"
    assert g.dont_say == "Don't say you're passionate"
    assert g.your_ask == "Offer to build a dashboard"


def test_company_brief_has_guidance_field():
    brief = CompanyBrief(id=1, name="Test")
    assert brief.guidance is None


from backend.guidance.rules import classify_skill_type


def test_classify_developer():
    assert classify_skill_type(["Python scripting", "API integration", "React frontend"]) == "developer"


def test_classify_designer():
    assert classify_skill_type(["UI/UX design", "Figma", "graphic design"]) == "designer"


def test_classify_data():
    assert classify_skill_type(["data analysis", "data visualization", "machine learning"]) == "data"


def test_classify_writer():
    assert classify_skill_type(["content writing", "scientific writing", "copywriting"]) == "writer"


def test_classify_business():
    assert classify_skill_type(["marketing", "social media marketing", "market research"]) == "business"


def test_classify_operations():
    assert classify_skill_type(["project management", "customer support", "QA testing"]) == "operations"


def test_classify_tie_breaks_by_company_tags():
    # Equal developer and data skills — company needs data, so data wins
    skills = ["Python scripting", "data analysis"]
    company_tags = ["data visualization", "data analysis"]
    assert classify_skill_type(skills, company_tags) == "data"


def test_classify_empty_skills():
    assert classify_skill_type([]) is None


def test_classify_unknown_skills_returns_none():
    assert classify_skill_type(["underwater basket weaving"]) is None
