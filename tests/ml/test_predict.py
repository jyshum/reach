import json
import numpy as np
import pandas as pd
from unittest.mock import patch, Mock

from backend.ml.predict import score_to_category, predict_all


def test_score_to_category():
    assert score_to_category(0.8) == "high"
    assert score_to_category(0.6) == "high"
    assert score_to_category(0.5) == "medium"
    assert score_to_category(0.3) == "medium"
    assert score_to_category(0.29) == "low"
    assert score_to_category(0.0) == "low"


def test_predict_all_writes_json(tmp_path):
    # Create a minimal fake model
    fake_model = Mock()
    fake_model.predict_proba.return_value = np.array([[0.2, 0.8], [0.7, 0.3]])

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
        "stage_early", "stage_growth", "stage_late",
        "is_hiring", "top_company", "days_since_launch",
        "nonprofit", "description_length", "has_long_description",
        "num_tags", "num_industries", "is_active",
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
    assert scores[0]["reachability_probability"] == 0.8
    assert scores[1]["name"] == "LowReach"
    assert scores[1]["reachability_score"] == "medium"
    assert scores[1]["reachability_probability"] == 0.3
