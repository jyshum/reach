import json
import pytest
from unittest.mock import patch, MagicMock

from backend.pipeline.supabase_write import merge_company_data, upload_to_supabase


def test_merge_company_data():
    enriched = [
        {"name": "AlphaCo", "batch": "W24", "summary": "Alpha does things.", "one_liner": "Alpha tools",
         "need_tags": ["python"], "industry": "ai-ml", "technical_level": "technical",
         "stage_detail": "growing", "specific_projects": ["Build dashboard", "Write docs"],
         "description": "Alpha.", "long_description": "Full alpha.", "tags": ["AI"],
         "industries": ["AI"], "website": "https://alpha.com", "team_size": 5,
         "stage": "Early", "status": "Active", "is_hiring": False, "all_locations": "SF"},
    ]
    scores = [
        {"name": "AlphaCo", "reachability_score": "high", "reachability_probability": 0.98},
    ]
    raw = [
        {"name": "AlphaCo", "slug": "alphaco", "small_logo_thumb_url": "https://example.com/logo.png"},
    ]
    founders = [
        {"company_name": "AlphaCo", "founder_name": "Ada Founder", "founder_title": "CEO",
         "founder_avatar_url": "https://example.com/ada.png", "founder_linkedin": "https://linkedin.com/in/ada",
         "founder_twitter": "https://x.com/ada"},
    ]

    merged = merge_company_data(enriched, scores, raw, founders)

    assert len(merged) == 1
    assert merged[0]["name"] == "AlphaCo"
    assert merged[0]["summary"] == "Alpha does things."
    assert merged[0]["reachability_score"] == "high"
    assert merged[0]["reachability_probability"] == 0.98
    assert merged[0]["slug"] == "alphaco"
    assert merged[0]["small_logo_url"] == "https://example.com/logo.png"
    assert merged[0]["founder_name"] == "Ada Founder"
    assert merged[0]["founder_email"] is None


def test_merge_company_data_missing_score():
    enriched = [
        {"name": "NoCo", "batch": "W24", "summary": "No score.", "one_liner": "No",
         "need_tags": [], "industry": "other", "technical_level": "mixed",
         "stage_detail": "building-mvp", "specific_projects": ["A", "B"],
         "description": "No.", "long_description": "", "tags": [],
         "industries": [], "website": "", "team_size": None,
         "stage": "", "status": "Active", "is_hiring": False, "all_locations": ""},
    ]
    scores = []
    raw = []
    founders = []

    merged = merge_company_data(enriched, scores, raw, founders)
    assert merged[0]["reachability_score"] == "low"
    assert merged[0]["reachability_probability"] == 0.0
    assert merged[0]["slug"] is None
    assert merged[0]["small_logo_url"] is None
    assert merged[0]["founder_name"] is None


def test_upload_to_supabase():
    companies = [
        {"name": "AlphaCo", "yc_batch": "W24", "summary": "Test.",
         "reachability_score": "high", "reachability_probability": 0.98},
    ]

    mock_db = MagicMock()
    mock_db.table.return_value.upsert.return_value.execute.return_value.data = companies

    with patch("backend.pipeline.supabase_write.get_supabase_client", return_value=mock_db):
        upload_to_supabase(companies)

    mock_db.table.assert_called_with("companies")
    mock_db.table.return_value.upsert.assert_called_once()


def test_full_pipeline_writes(tmp_path):
    from backend.pipeline.supabase_write import write_to_supabase

    enriched = [
        {"name": "TestCo", "batch": "W24", "summary": "Test.", "one_liner": "Test",
         "need_tags": ["python"], "industry": "ai-ml", "technical_level": "technical",
         "stage_detail": "growing", "specific_projects": ["A", "B"],
         "description": "Test.", "long_description": "Full test.", "tags": ["AI"],
         "industries": ["AI"], "website": "https://test.com", "team_size": 3,
         "stage": "Early", "status": "Active", "is_hiring": False, "all_locations": "SF"},
    ]
    scores = [
        {"name": "TestCo", "reachability_score": "high", "reachability_probability": 0.95},
    ]
    raw = [
        {"name": "TestCo", "slug": "testco", "small_logo_thumb_url": "https://example.com/test.png"},
    ]
    founders = [
        {"company_name": "TestCo", "founder_name": "Test Founder", "founder_title": "Founder",
         "founder_avatar_url": "https://example.com/founder.png", "founder_linkedin": None,
         "founder_twitter": None},
    ]

    enriched_path = tmp_path / "enriched.json"
    enriched_path.write_text(json.dumps(enriched))
    scores_path = tmp_path / "scores.json"
    scores_path.write_text(json.dumps(scores))
    raw_path = tmp_path / "raw.json"
    raw_path.write_text(json.dumps(raw))
    founders_path = tmp_path / "founders.json"
    founders_path.write_text(json.dumps(founders))

    mock_db = MagicMock()
    mock_db.table.return_value.upsert.return_value.execute.return_value.data = []

    with patch("backend.pipeline.supabase_write.get_supabase_client", return_value=mock_db):
        write_to_supabase(
            enriched_path=str(enriched_path),
            scores_path=str(scores_path),
            raw_path=str(raw_path),
            founders_path=str(founders_path),
        )

    mock_db.table.return_value.upsert.assert_called_once()
    call_args = mock_db.table.return_value.upsert.call_args[0][0]
    assert len(call_args) == 1
    assert call_args[0]["name"] == "TestCo"
    assert call_args[0]["reachability_score"] == "high"
    assert call_args[0]["slug"] == "testco"
    assert call_args[0]["founder_name"] == "Test Founder"


def test_merge_includes_new_fields():
    """Verify founder_bio, has_email, email fields, and yc_tags are included."""
    enriched = [
        {"name": "FinCo", "batch": "S24", "summary": "Fintech startup.", "one_liner": "Payments",
         "need_tags": ["python"], "industry": "fintech", "technical_level": "technical",
         "stage_detail": "growing", "specific_projects": ["Build API"],
         "description": "FinCo.", "long_description": "Full finco.", "tags": ["Fintech"],
         "industries": ["Finance and Accounting"], "website": "https://finco.com", "team_size": 8,
         "stage": "Growth", "status": "Active", "is_hiring": True, "all_locations": "NYC"},
    ]
    scores = [
        {"name": "FinCo", "reachability_score": "high", "reachability_probability": 0.92},
    ]
    raw = [
        {"name": "FinCo", "slug": "finco", "small_logo_thumb_url": "https://example.com/finco.png",
         "tags": ["Fintech", "Payments"], "industries": ["Finance and Accounting"]},
    ]
    founders = [
        {"company_name": "FinCo", "founder_name": "Fin Founder", "founder_title": "CEO",
         "founder_avatar_url": "https://example.com/fin.png", "founder_linkedin": "https://linkedin.com/in/fin",
         "founder_twitter": None, "founder_bio": "Serial fintech entrepreneur with 10 years experience.",
         "has_email": True},
    ]
    emails = [
        {"company_name": "FinCo", "founder_email": "fin@finco.com",
         "email_source": "linkedin", "email_confidence": 0.95},
    ]
    tag_mapping_data = {
        "collapse_map": {
            "AIOps": "Machine Learning",
            "Finance and Accounting": "Finance & Payments",
        },
        "valid_tags": {"Fintech", "Payments", "Finance & Payments", "Machine Learning", "Developer Tools"},
    }

    merged = merge_company_data(enriched, scores, raw, founders, emails=emails, tag_mapping_data=tag_mapping_data)

    assert len(merged) == 1
    record = merged[0]

    # founder_bio and has_email
    assert record["founder_bio"] == "Serial fintech entrepreneur with 10 years experience."
    assert record["has_email"] is True

    # email fields
    assert record["founder_email"] == "fin@finco.com"
    assert record["email_source"] == "linkedin"
    assert record["email_confidence"] == 0.95

    # yc_tags mapped from raw data
    assert "Fintech" in record["yc_tags"]
    assert "Payments" in record["yc_tags"]


def test_merge_new_fields_defaults_without_data():
    """Verify defaults when no email/tag data is provided."""
    enriched = [
        {"name": "NoCo", "batch": "W24", "summary": "No extras.", "one_liner": "No",
         "need_tags": [], "industry": "other", "technical_level": "mixed",
         "stage_detail": "building-mvp", "specific_projects": [],
         "description": "No.", "long_description": "", "tags": [],
         "industries": [], "website": "", "team_size": None,
         "stage": "", "status": "Active", "is_hiring": False, "all_locations": ""},
    ]

    merged = merge_company_data(enriched, [], [], [])

    record = merged[0]
    assert record["founder_bio"] is None
    assert record["has_email"] is False
    assert record["founder_email"] is None
    assert record["email_source"] is None
    assert record["email_confidence"] is None
    assert record["yc_tags"] == []
