import json
import pytest
from backend.pipeline.enrich import parse_response, validate_enrichment, auto_fix_enrichment


def test_parse_response_valid_json():
    raw = json.dumps({"summary": "Test.", "one_liner": "Test co"})
    result = parse_response(raw)
    assert result == {"summary": "Test.", "one_liner": "Test co"}


def test_parse_response_invalid_json():
    result = parse_response("not json at all")
    assert result is None


def test_parse_response_json_with_markdown_wrapper():
    raw = '```json\n{"summary": "Test."}\n```'
    result = parse_response(raw)
    assert result == {"summary": "Test."}


def test_validate_enrichment_valid():
    data = {
        "summary": "They build tools for logistics. It helps companies ship faster.",
        "one_liner": "Logistics tools for shippers",
        "need_tags": ["Python scripting", "data analysis", "web design"],
        "industry": "logistics",
        "technical_level": "mixed",
        "stage_detail": "growing",
        "specific_projects": [
            "Build a tracking dashboard for shipment status",
            "Write documentation for their API endpoints",
        ],
    }
    errors = validate_enrichment(data)
    assert errors == []


def test_validate_enrichment_missing_fields():
    data = {"summary": "Test.", "one_liner": "Test"}
    errors = validate_enrichment(data)
    assert any("need_tags" in e for e in errors)
    assert any("industry" in e for e in errors)


def test_validate_enrichment_summary_too_short():
    data = {
        "summary": "Short.",
        "one_liner": "Test co",
        "need_tags": ["Python", "React"],
        "industry": "fintech",
        "technical_level": "technical",
        "stage_detail": "launched",
        "specific_projects": ["Do task one for this company", "Do task two for them"],
    }
    errors = validate_enrichment(data)
    assert any("summary" in e for e in errors)


def test_validate_enrichment_bad_industry():
    data = {
        "summary": "They build tools for logistics. It helps companies ship faster.",
        "one_liner": "Logistics tools",
        "need_tags": ["Python", "React"],
        "industry": "invalid-industry",
        "technical_level": "technical",
        "stage_detail": "launched",
        "specific_projects": ["Do task one for this company", "Do task two for them"],
    }
    errors = validate_enrichment(data)
    assert any("industry" in e for e in errors)


def test_validate_enrichment_wrong_number_of_projects():
    data = {
        "summary": "They build tools for logistics. It helps companies ship faster.",
        "one_liner": "Logistics tools",
        "need_tags": ["Python", "React"],
        "industry": "logistics",
        "technical_level": "technical",
        "stage_detail": "launched",
        "specific_projects": ["Only one project here"],
    }
    errors = validate_enrichment(data)
    assert any("specific_projects" in e for e in errors)


def test_auto_fix_industry():
    data = {
        "summary": "They build tools for health. It helps doctors work faster.",
        "one_liner": "Health tools",
        "need_tags": ["Python", "React"],
        "industry": "health",
        "technical_level": "technical",
        "stage_detail": "launched",
        "specific_projects": ["Do task one for this company", "Do task two for them"],
    }
    fixed = auto_fix_enrichment(data)
    assert fixed["industry"] == "healthcare"


def test_auto_fix_technical_level():
    data = {
        "summary": "They build tools. It helps people.",
        "one_liner": "Tools",
        "need_tags": ["Python"],
        "industry": "fintech",
        "technical_level": "tech",
        "stage_detail": "launched",
        "specific_projects": ["Do task one", "Do task two"],
    }
    fixed = auto_fix_enrichment(data)
    assert fixed["technical_level"] == "technical"


def test_auto_fix_stage_detail():
    data = {
        "summary": "They build tools. It helps people.",
        "one_liner": "Tools",
        "need_tags": ["Python"],
        "industry": "fintech",
        "technical_level": "technical",
        "stage_detail": "mvp",
        "specific_projects": ["Do task one", "Do task two"],
    }
    fixed = auto_fix_enrichment(data)
    assert fixed["stage_detail"] == "building-mvp"
