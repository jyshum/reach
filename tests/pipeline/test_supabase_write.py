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
