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
