import json
import numpy as np
import pandas as pd
from unittest.mock import patch, Mock

from backend.ml.predict import score_to_category, predict_all


def test_score_to_category():
    assert score_to_category(0.99) == "high"
    assert score_to_category(0.95) == "high"
    assert score_to_category(0.8) == "medium"
    assert score_to_category(0.7) == "medium"
    assert score_to_category(0.69) == "low"
    assert score_to_category(0.0) == "low"


def test_predict_all_writes_json(tmp_path):
    # Create a minimal fake model
    fake_model = Mock()
    fake_model.predict_proba.return_value = np.array([[0.02, 0.98], [0.25, 0.75]])

    companies = [
        {
            "name": "HighReach",
            "description": "Small team",
            "batch": "Winter 2024",
            "tags": ["AI"],
            "website": "https://hr.com",
            "team_size": 3,
            "stage": "Early",
            "status": "Active",
            "is_hiring": True,
            "top_company": False,
            "launched_at": 1708029636,
            "nonprofit": False,
            "industries": ["B2B"],
            "subindustry": "",
            "long_description": "",
            "all_locations": "",
        },
        {
            "name": "LowReach",
            "description": "Big company",
            "batch": "Winter 2023",
            "tags": [],
            "website": "https://lr.com",
            "team_size": 100,
            "stage": "Late",
            "status": "Active",
            "is_hiring": False,
            "top_company": True,
            "launched_at": 1600000000,
            "nonprofit": False,
            "industries": [],
            "subindustry": "",
            "long_description": "",
            "all_locations": "",
        },
    ]
    raw_path = tmp_path / "raw.json"
    raw_path.write_text(json.dumps(companies))

    feature_cols = [
        "team_size", "team_size_missing", "batch_recency_days",
        "is_growth", "is_hiring", "days_since_launch",
        "description_length", "has_long_description",
        "num_tags", "num_industries",
    ]
    cols_path = tmp_path / "feature_cols.json"
    cols_path.write_text(json.dumps(feature_cols))

    output_path = tmp_path / "scores.json"

    with patch("backend.ml.predict.joblib.load", return_value=fake_model):
        predict_all(
            str(raw_path), "fake_model.joblib",
            str(cols_path), str(output_path),
        )

    assert output_path.exists()
    scores = json.loads(output_path.read_text())
    assert len(scores) == 2
    assert scores[0]["name"] == "HighReach"
    assert scores[0]["reachability_score"] == "high"
    assert scores[0]["reachability_probability"] == 0.98
    assert scores[1]["name"] == "LowReach"
    assert scores[1]["reachability_score"] == "medium"
    assert scores[1]["reachability_probability"] == 0.75


def test_predict_all_inactive_auto_low(tmp_path):
    """Inactive/acquired companies are auto-scored as low without model."""
    fake_model = Mock()
    fake_model.predict_proba.return_value = np.array([[0.02, 0.98]])

    companies = [
        {
            "name": "ActiveCo",
            "description": "Active company",
            "batch": "Winter 2024",
            "tags": ["AI"],
            "website": "https://active.com",
            "team_size": 3,
            "stage": "Early",
            "status": "Active",
            "is_hiring": True,
            "top_company": False,
            "launched_at": 1708029636,
            "nonprofit": False,
            "industries": ["B2B"],
            "subindustry": "",
            "long_description": "",
            "all_locations": "",
        },
        {
            "name": "InactiveCo",
            "description": "Inactive company",
            "batch": "Winter 2023",
            "tags": [],
            "website": "",
            "team_size": 50,
            "stage": "Late",
            "status": "Inactive",
            "is_hiring": False,
            "top_company": False,
            "launched_at": 1600000000,
            "nonprofit": False,
            "industries": [],
            "subindustry": "",
            "long_description": "",
            "all_locations": "",
        },
        {
            "name": "AcquiredCo",
            "description": "Acquired company",
            "batch": "Summer 2023",
            "tags": [],
            "website": "",
            "team_size": 20,
            "stage": "Growth",
            "status": "Acquired",
            "is_hiring": False,
            "top_company": False,
            "launched_at": 1650000000,
            "nonprofit": False,
            "industries": [],
            "subindustry": "",
            "long_description": "",
            "all_locations": "",
        },
    ]
    raw_path = tmp_path / "raw.json"
    raw_path.write_text(json.dumps(companies))

    feature_cols = [
        "team_size", "team_size_missing", "batch_recency_days",
        "is_growth", "is_hiring", "days_since_launch",
        "description_length", "has_long_description",
        "num_tags", "num_industries",
    ]
    cols_path = tmp_path / "feature_cols.json"
    cols_path.write_text(json.dumps(feature_cols))

    output_path = tmp_path / "scores.json"

    with patch("backend.ml.predict.joblib.load", return_value=fake_model):
        results = predict_all(
            str(raw_path), "fake_model.joblib",
            str(cols_path), str(output_path),
        )

    assert len(results) == 3

    # Model only called with 1 active company
    assert fake_model.predict_proba.call_count == 1

    active_result = next(r for r in results if r["name"] == "ActiveCo")
    assert active_result["reachability_score"] == "high"
    assert active_result["reachability_probability"] == 0.98

    inactive_result = next(r for r in results if r["name"] == "InactiveCo")
    assert inactive_result["reachability_score"] == "low"
    assert inactive_result["reachability_probability"] == 0.0

    acquired_result = next(r for r in results if r["name"] == "AcquiredCo")
    assert acquired_result["reachability_score"] == "low"
    assert acquired_result["reachability_probability"] == 0.0
