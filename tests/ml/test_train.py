import json
import os
import pandas as pd
import numpy as np
from backend.ml.train import train_and_evaluate, load_training_data


def _make_companies(n=40):
    """Generate synthetic companies for testing."""
    rng = np.random.RandomState(42)
    companies = []
    for i in range(n):
        companies.append({
            "name": f"Co{i}",
            "description": f"Description {i}",
            "batch": rng.choice(["Winter 2023", "Summer 2023", "Winter 2024", "Summer 2024"]),
            "tags": ["AI"] * rng.randint(0, 5),
            "website": f"https://co{i}.com",
            "team_size": int(rng.choice([2, 5, 10, 25, 50])),
            "stage": rng.choice(["Early", "Early", "Growth", "Late"]),
            "status": rng.choice(["Active", "Active", "Active", "Inactive"]),
            "is_hiring": bool(rng.choice([True, False])),
            "top_company": bool(rng.choice([False, False, False, True])),
            "launched_at": int(1700000000 + rng.randint(0, 10000000)),
            "nonprofit": False,
            "industries": ["B2B"],
            "subindustry": "B2B -> SaaS",
            "long_description": "Some text." * rng.randint(0, 5),
            "all_locations": "SF, CA",
        })
    return companies


def _make_labels(companies):
    """Generate labels: small + early + not top = 1, else 0."""
    labels = []
    for c in companies:
        reachable = (
            (c["team_size"] or 99) < 15
            and c["stage"] == "Early"
            and not c["top_company"]
        )
        labels.append(1 if reachable else 0)
    return labels


def test_load_training_data(tmp_path):
    companies = _make_companies(20)
    labels = _make_labels(companies)

    raw_path = tmp_path / "raw.json"
    raw_path.write_text(json.dumps(companies))

    label_df = pd.DataFrame(companies)[["name"]].copy()
    label_df["reachability_label"] = labels
    label_path = tmp_path / "labels.csv"
    label_df.to_csv(str(label_path), index=False)

    X, y = load_training_data(str(raw_path), str(label_path))
    assert len(X) == 20
    assert len(y) == 20
    assert set(y.unique()) == {0, 1}


def test_train_and_evaluate_returns_results(tmp_path):
    companies = _make_companies(40)
    labels = _make_labels(companies)

    raw_path = tmp_path / "raw.json"
    raw_path.write_text(json.dumps(companies))

    label_df = pd.DataFrame(companies)[["name"]].copy()
    label_df["reachability_label"] = labels
    label_path = tmp_path / "labels.csv"
    label_df.to_csv(str(label_path), index=False)

    model_path = tmp_path / "model.joblib"
    cols_path = tmp_path / "feature_cols.json"

    results = train_and_evaluate(
        str(raw_path), str(label_path),
        str(model_path), str(cols_path),
        n_folds=3,
    )

    assert "lr" in results
    assert "xgb" in results
    assert "winner" in results
    assert results["winner"] in ["lr", "xgb"]
    assert model_path.exists()
    assert cols_path.exists()

    # Check saved feature columns
    with open(str(cols_path)) as f:
        saved_cols = json.load(f)
    assert len(saved_cols) == 15
