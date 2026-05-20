import pandas as pd
from backend.ml.features import build_features


def test_build_features_returns_dataframe():
    companies = [
        {
            "name": "TestCo",
            "description": "A test company",
            "batch": "Winter 2024",
            "tags": ["AI", "SaaS"],
            "website": "https://test.com",
            "team_size": 5,
            "stage": "Early",
            "status": "Active",
            "is_hiring": True,
            "top_company": False,
            "launched_at": 1708029636,
            "nonprofit": False,
            "industries": ["B2B", "SaaS"],
            "subindustry": "B2B -> SaaS",
            "long_description": "A longer description here.",
            "all_locations": "SF, CA",
        }
    ]
    df = build_features(companies)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1


def test_build_features_expected_columns():
    companies = [
        {
            "name": "TestCo",
            "description": "A test company",
            "batch": "Winter 2024",
            "tags": ["AI", "SaaS"],
            "website": "https://test.com",
            "team_size": 5,
            "stage": "Early",
            "status": "Active",
            "is_hiring": True,
            "top_company": False,
            "launched_at": 1708029636,
            "nonprofit": False,
            "industries": ["B2B", "SaaS"],
            "subindustry": "B2B -> SaaS",
            "long_description": "A longer description here.",
            "all_locations": "SF, CA",
        }
    ]
    df = build_features(companies)
    expected_cols = [
        "team_size", "team_size_missing", "batch_recency_days",
        "stage_early", "stage_growth", "stage_late",
        "is_hiring", "top_company", "days_since_launch",
        "nonprofit", "description_length", "has_long_description",
        "num_tags", "num_industries", "is_active",
    ]
    assert list(df.columns) == expected_cols


def test_build_features_values_correct():
    companies = [
        {
            "name": "TestCo",
            "description": "Short desc",
            "batch": "Winter 2024",
            "tags": ["AI", "SaaS"],
            "website": "https://test.com",
            "team_size": 5,
            "stage": "Early",
            "status": "Active",
            "is_hiring": True,
            "top_company": False,
            "launched_at": 1708029636,
            "nonprofit": False,
            "industries": ["B2B", "SaaS"],
            "subindustry": "B2B -> SaaS",
            "long_description": "Longer text.",
            "all_locations": "SF, CA",
        }
    ]
    df = build_features(companies)
    row = df.iloc[0]
    assert row["team_size"] == 5
    assert row["team_size_missing"] == 0
    assert row["stage_early"] == 1
    assert row["stage_growth"] == 0
    assert row["stage_late"] == 0
    assert row["is_hiring"] == 1
    assert row["top_company"] == 0
    assert row["nonprofit"] == 0
    assert row["description_length"] == len("Short desc")
    assert row["has_long_description"] == 1
    assert row["num_tags"] == 2
    assert row["num_industries"] == 2
    assert row["is_active"] == 1
    assert row["batch_recency_days"] > 0
    assert row["days_since_launch"] > 0


def test_build_features_handles_missing_fields():
    companies = [
        {
            "name": "Bare",
            "description": "",
            "batch": "Summer 2023",
            "tags": [],
            "website": "",
            "team_size": None,
            "stage": "",
            "status": "",
            "is_hiring": False,
            "top_company": False,
            "launched_at": None,
            "nonprofit": False,
            "industries": [],
            "subindustry": "",
            "long_description": "",
            "all_locations": "",
        }
    ]
    df = build_features(companies)
    row = df.iloc[0]
    assert row["team_size_missing"] == 1
    assert row["stage_early"] == 0
    assert row["stage_growth"] == 0
    assert row["stage_late"] == 0
    assert row["has_long_description"] == 0
    assert row["num_tags"] == 0
    assert row["is_active"] == 0
    # team_size and days_since_launch should be filled with median (or 0 for single row)
    assert pd.notna(row["team_size"])
    assert pd.notna(row["days_since_launch"])
