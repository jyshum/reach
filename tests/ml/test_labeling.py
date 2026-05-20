import json
import os
import pandas as pd
from backend.ml.labeling import export_labeling_csv, import_labels


def test_export_labeling_csv_creates_file(tmp_path):
    companies = [
        {
            "name": "Co1", "description": "Desc 1", "batch": "Winter 2024",
            "tags": ["AI"], "website": "https://co1.com", "team_size": 3,
            "stage": "Early", "status": "Active", "is_hiring": True,
            "top_company": False, "launched_at": 1708029636, "nonprofit": False,
            "industries": ["B2B"], "subindustry": "", "long_description": "",
            "all_locations": "SF",
        },
        {
            "name": "Co2", "description": "Desc 2", "batch": "Summer 2023",
            "tags": [], "website": "https://co2.com", "team_size": 50,
            "stage": "Growth", "status": "Active", "is_hiring": False,
            "top_company": True, "launched_at": 1680000000, "nonprofit": False,
            "industries": ["Fintech"], "subindustry": "", "long_description": "",
            "all_locations": "NYC",
        },
    ]
    raw_path = tmp_path / "raw.json"
    raw_path.write_text(json.dumps(companies))

    output_csv = tmp_path / "to_label.csv"
    export_labeling_csv(str(raw_path), str(output_csv), sample_size=2)

    assert output_csv.exists()
    df = pd.read_csv(str(output_csv))
    expected_cols = [
        "name", "description", "batch", "team_size_bucket", "is_hiring",
        "industries", "website", "reachability_label",
    ]
    assert list(df.columns) == expected_cols
    assert len(df) == 2
    assert df["reachability_label"].isna().all()


def test_export_labeling_csv_samples_when_data_larger(tmp_path):
    companies = [
        {
            "name": f"Co{i}", "description": f"Desc {i}", "batch": "Winter 2024",
            "tags": [], "website": "", "team_size": i, "stage": "Early",
            "status": "Active", "is_hiring": False, "top_company": False,
            "launched_at": None, "nonprofit": False, "industries": [],
            "subindustry": "", "long_description": "", "all_locations": "",
        }
        for i in range(50)
    ]
    raw_path = tmp_path / "raw.json"
    raw_path.write_text(json.dumps(companies))

    output_csv = tmp_path / "to_label.csv"
    export_labeling_csv(str(raw_path), str(output_csv), sample_size=10)

    df = pd.read_csv(str(output_csv))
    assert len(df) == 10


def test_export_labeling_csv_filters_inactive(tmp_path):
    companies = [
        {
            "name": "ActiveCo", "description": "Active", "batch": "Winter 2024",
            "tags": [], "website": "", "team_size": 3, "stage": "Early",
            "status": "Active", "is_hiring": True, "top_company": False,
            "launched_at": None, "nonprofit": False, "industries": ["B2B"],
            "subindustry": "", "long_description": "", "all_locations": "",
        },
        {
            "name": "InactiveCo", "description": "Inactive", "batch": "Winter 2024",
            "tags": [], "website": "", "team_size": 10, "stage": "Early",
            "status": "Inactive", "is_hiring": False, "top_company": False,
            "launched_at": None, "nonprofit": False, "industries": [],
            "subindustry": "", "long_description": "", "all_locations": "",
        },
        {
            "name": "AcquiredCo", "description": "Acquired", "batch": "Winter 2024",
            "tags": [], "website": "", "team_size": 50, "stage": "Growth",
            "status": "Acquired", "is_hiring": False, "top_company": False,
            "launched_at": None, "nonprofit": False, "industries": [],
            "subindustry": "", "long_description": "", "all_locations": "",
        },
    ]
    raw_path = tmp_path / "raw.json"
    raw_path.write_text(json.dumps(companies))

    output_csv = tmp_path / "to_label.csv"
    export_labeling_csv(str(raw_path), str(output_csv), sample_size=10)

    df = pd.read_csv(str(output_csv))
    assert len(df) == 1
    assert df.iloc[0]["name"] == "ActiveCo"


def test_export_labeling_csv_team_size_bucket(tmp_path):
    companies = [
        {
            "name": "TinyCo", "description": "Tiny", "batch": "Winter 2024",
            "tags": [], "website": "", "team_size": 3, "stage": "Early",
            "status": "Active", "is_hiring": False, "top_company": False,
            "launched_at": None, "nonprofit": False, "industries": [],
            "subindustry": "", "long_description": "", "all_locations": "",
        },
        {
            "name": "BigCo", "description": "Big", "batch": "Winter 2024",
            "tags": [], "website": "", "team_size": 50, "stage": "Growth",
            "status": "Active", "is_hiring": False, "top_company": False,
            "launched_at": None, "nonprofit": False, "industries": [],
            "subindustry": "", "long_description": "", "all_locations": "",
        },
    ]
    raw_path = tmp_path / "raw.json"
    raw_path.write_text(json.dumps(companies))

    output_csv = tmp_path / "to_label.csv"
    export_labeling_csv(str(raw_path), str(output_csv), sample_size=10)

    df = pd.read_csv(str(output_csv))
    assert df[df["name"] == "TinyCo"].iloc[0]["team_size_bucket"] == "1-5"
    assert df[df["name"] == "BigCo"].iloc[0]["team_size_bucket"] == "30+"


def test_import_labels_reads_csv(tmp_path):
    csv_path = tmp_path / "labels.csv"
    csv_path.write_text(
        "name,description,batch,team_size_bucket,is_hiring,industries,website,reachability_label\n"
        "Co1,Desc,Winter 2024,1-5,True,B2B,https://co1.com,1\n"
        "Co2,Desc,Summer 2023,30+,False,Fintech,https://co2.com,0\n"
    )
    df = import_labels(str(csv_path))
    assert len(df) == 2
    assert list(df["reachability_label"]) == [1, 0]
    assert list(df["name"]) == ["Co1", "Co2"]


def test_import_labels_rejects_missing_labels(tmp_path):
    csv_path = tmp_path / "labels.csv"
    csv_path.write_text(
        "name,description,batch,team_size_bucket,is_hiring,industries,website,reachability_label\n"
        "Co1,Desc,Winter 2024,1-5,True,B2B,https://co1.com,1\n"
        "Co2,Desc,Summer 2023,30+,False,Fintech,https://co2.com,\n"
    )
    try:
        import_labels(str(csv_path))
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "missing" in str(e).lower() or "empty" in str(e).lower()
