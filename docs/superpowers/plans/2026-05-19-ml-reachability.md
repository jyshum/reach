# ML Reachability Scoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Train a logistic regression + XGBoost model on hand-labeled YC company data to predict founder reachability, replacing the planned LLM-based reachability_score.

**Architecture:** Expand the Algolia scraper to capture ML-relevant fields, build a feature engineering module, export a labeling CSV for hand-labeling, then train/evaluate/predict. Model outputs `data/reachability_scores.json` consumed by the rest of the pipeline.

**Tech Stack:** Python 3.11+, pandas, scikit-learn, xgboost, joblib

---

## File Structure

| File | Responsibility |
|---|---|
| `backend/pipeline/scrape_yc.py` | **Modify:** expand `extract_company()` to capture 11 additional Algolia fields |
| `tests/pipeline/test_scrape_yc.py` | **Modify:** update test fixtures for expanded fields |
| `backend/ml/__init__.py` | Package marker |
| `backend/ml/config.py` | Paths, thresholds, hyperparameters |
| `backend/ml/features.py` | `build_features(companies) → DataFrame` — shared by train + predict |
| `backend/ml/labeling.py` | Export labeling CSV, import labeled CSV |
| `backend/ml/train.py` | 5-fold CV on LR + XGBoost, save winner |
| `backend/ml/predict.py` | Load model, score all companies, write JSON |
| `tests/ml/__init__.py` | Package marker |
| `tests/ml/test_features.py` | Unit tests for feature engineering |
| `tests/ml/test_labeling.py` | Unit tests for labeling export/import |
| `tests/ml/test_train.py` | Unit tests for training pipeline |
| `tests/ml/test_predict.py` | Unit tests for prediction pipeline |
| `requirements.txt` | **Modify:** add pandas, scikit-learn, xgboost, joblib |
| `.gitignore` | **Modify:** add `backend/ml/artifacts/` |

---

### Task 1: Add ML dependencies and update gitignore

**Files:**
- Modify: `requirements.txt`
- Modify: `.gitignore`

- [ ] **Step 1: Update requirements.txt**

Replace contents of `requirements.txt` with:

```
requests==2.32.3
pytest==8.3.5
pandas>=2.0
scikit-learn>=1.3
xgboost>=2.0
joblib>=1.3
```

- [ ] **Step 2: Update .gitignore**

Replace contents of `.gitignore` with:

```
data/
__pycache__/
*.pyc
.env
venv/
.venv/
backend/ml/artifacts/
```

- [ ] **Step 3: Create ML package directories**

Create empty files:
- `backend/ml/__init__.py`
- `tests/ml/__init__.py`

- [ ] **Step 4: Install dependencies**

Run: `pip install -r requirements.txt`

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .gitignore backend/ml/__init__.py tests/ml/__init__.py
git commit -m "chore: add ML dependencies and package structure"
```

---

### Task 2: Expand scraper to capture ML fields

**Files:**
- Modify: `backend/pipeline/scrape_yc.py:15-23`
- Modify: `tests/pipeline/test_scrape_yc.py`

- [ ] **Step 1: Update test fixtures for expanded extract_company**

Replace the two extract_company tests in `tests/pipeline/test_scrape_yc.py`:

```python
def test_extract_company_maps_fields():
    hit = {
        "name": "Acme Corp",
        "one_liner": "AI for supply chains.",
        "batch": "Winter 2024",
        "tags": ["B2B", "Supply Chain", "AI"],
        "website": "https://acmecorp.com",
        "team_size": 7,
        "stage": "Early",
        "status": "Active",
        "isHiring": True,
        "top_company": False,
        "launched_at": 1708029636,
        "nonprofit": False,
        "industries": ["B2B", "Supply Chain and Logistics"],
        "subindustry": "B2B -> Supply Chain and Logistics",
        "long_description": "We are building a safer supply chain.",
        "all_locations": "San Francisco, CA, USA",
        "objectID": "acme-corp",
        "logo": "https://example.com/logo.png",
        "extra_field": "should be ignored",
    }
    result = extract_company(hit)
    assert result == {
        "name": "Acme Corp",
        "description": "AI for supply chains.",
        "batch": "Winter 2024",
        "tags": ["B2B", "Supply Chain", "AI"],
        "website": "https://acmecorp.com",
        "team_size": 7,
        "stage": "Early",
        "status": "Active",
        "is_hiring": True,
        "top_company": False,
        "launched_at": 1708029636,
        "nonprofit": False,
        "industries": ["B2B", "Supply Chain and Logistics"],
        "subindustry": "B2B -> Supply Chain and Logistics",
        "long_description": "We are building a safer supply chain.",
        "all_locations": "San Francisco, CA, USA",
    }


def test_extract_company_handles_missing_fields():
    hit = {
        "name": "Bare Minimum Co",
        "batch": "Summer 2023",
    }
    result = extract_company(hit)
    assert result == {
        "name": "Bare Minimum Co",
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/pipeline/test_scrape_yc.py::test_extract_company_maps_fields -v`
Expected: FAIL (old extract_company returns only 5 fields)

- [ ] **Step 3: Update extract_company in scrape_yc.py**

Replace the `extract_company` function in `backend/pipeline/scrape_yc.py`:

```python
def extract_company(hit: dict) -> dict:
    """Extract relevant fields from a single Algolia hit."""
    return {
        "name": hit.get("name", ""),
        "description": hit.get("one_liner", ""),
        "batch": hit.get("batch", ""),
        "tags": hit.get("tags", []),
        "website": hit.get("website", ""),
        "team_size": hit.get("team_size", None),
        "stage": hit.get("stage", ""),
        "status": hit.get("status", ""),
        "is_hiring": hit.get("isHiring", False),
        "top_company": hit.get("top_company", False),
        "launched_at": hit.get("launched_at", None),
        "nonprofit": hit.get("nonprofit", False),
        "industries": hit.get("industries", []),
        "subindustry": hit.get("subindustry", ""),
        "long_description": hit.get("long_description", ""),
        "all_locations": hit.get("all_locations", ""),
    }
```

Note: `isHiring` in Algolia maps to `is_hiring` in our schema (snake_case).

- [ ] **Step 4: Run all tests**

Run: `python -m pytest tests/pipeline/test_scrape_yc.py -v`
Expected: 10 passed

- [ ] **Step 5: Re-run scraper to regenerate data with expanded fields**

Run: `python -m backend.pipeline.scrape_yc`
Expected: `[DONE] Wrote ~990 companies to data/raw_companies.json`

Verify new fields present:
Run: `python3 -c "import json; d=json.load(open('data/raw_companies.json')); print(list(d[0].keys()))"`
Expected: list includes `team_size`, `stage`, `status`, `is_hiring`, etc.

- [ ] **Step 6: Commit**

```bash
git add backend/pipeline/scrape_yc.py tests/pipeline/test_scrape_yc.py
git commit -m "feat: expand scraper to capture ML-relevant Algolia fields"
```

---

### Task 3: ML config module

**Files:**
- Create: `backend/ml/config.py`

- [ ] **Step 1: Create config.py**

```python
"""ML pipeline configuration."""

import os

_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")

RAW_DATA_PATH = os.path.join(_ROOT, "data", "raw_companies.json")
LABELING_DIR = os.path.join(_ROOT, "data", "labeling")
LABEL_EXPORT_PATH = os.path.join(LABELING_DIR, "to_label.csv")
LABEL_PATH = os.path.join(LABELING_DIR, "labels.csv")
SCORES_OUTPUT_PATH = os.path.join(_ROOT, "data", "reachability_scores.json")

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")
MODEL_PATH = os.path.join(ARTIFACTS_DIR, "model.joblib")
FEATURE_COLS_PATH = os.path.join(ARTIFACTS_DIR, "feature_cols.json")

# Probability -> category thresholds
HIGH_THRESHOLD = 0.6
LOW_THRESHOLD = 0.3

# Training
N_FOLDS = 5
RANDOM_SEED = 42
LABELING_SAMPLE_SIZE = 200
```

- [ ] **Step 2: Commit**

```bash
git add backend/ml/config.py
git commit -m "feat: add ML config module with paths and thresholds"
```

---

### Task 4: Feature engineering

**Files:**
- Create: `tests/ml/test_features.py`
- Create: `backend/ml/features.py`

- [ ] **Step 1: Write failing tests for build_features**

Create `tests/ml/test_features.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/ml/test_features.py -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement build_features**

Create `backend/ml/features.py`:

```python
"""Feature engineering for reachability model."""

from datetime import datetime, timezone

import pandas as pd

# Approximate batch start dates (month/year)
_BATCH_DATES = {
    "Winter": 1,   # January
    "Summer": 6,   # June
}

FEATURE_COLUMNS = [
    "team_size", "team_size_missing", "batch_recency_days",
    "stage_early", "stage_growth", "stage_late",
    "is_hiring", "top_company", "days_since_launch",
    "nonprofit", "description_length", "has_long_description",
    "num_tags", "num_industries", "is_active",
]


def _parse_batch_date(batch: str) -> datetime | None:
    """Parse 'Winter 2024' -> datetime(2024, 1, 1)."""
    parts = batch.split()
    if len(parts) != 2:
        return None
    season, year_str = parts
    month = _BATCH_DATES.get(season)
    if month is None:
        return None
    try:
        return datetime(int(year_str), month, 1, tzinfo=timezone.utc)
    except ValueError:
        return None


def build_features(companies: list[dict]) -> pd.DataFrame:
    """Transform raw company dicts into a feature matrix."""
    now = datetime.now(timezone.utc)
    rows = []

    for c in companies:
        team_size = c.get("team_size")
        launched_at = c.get("launched_at")

        # Batch recency
        batch_date = _parse_batch_date(c.get("batch", ""))
        batch_recency_days = (now - batch_date).days if batch_date else None

        # Days since launch
        if launched_at is not None:
            launch_dt = datetime.fromtimestamp(launched_at, tz=timezone.utc)
            days_since_launch = (now - launch_dt).days
        else:
            days_since_launch = None

        stage = c.get("stage", "")

        rows.append({
            "team_size": team_size,
            "team_size_missing": 1 if team_size is None else 0,
            "batch_recency_days": batch_recency_days,
            "stage_early": 1 if stage == "Early" else 0,
            "stage_growth": 1 if stage == "Growth" else 0,
            "stage_late": 1 if stage == "Late" else 0,
            "is_hiring": 1 if c.get("is_hiring") else 0,
            "top_company": 1 if c.get("top_company") else 0,
            "days_since_launch": days_since_launch,
            "nonprofit": 1 if c.get("nonprofit") else 0,
            "description_length": len(c.get("description", "")),
            "has_long_description": 1 if len(c.get("long_description", "")) > 0 else 0,
            "num_tags": len(c.get("tags", [])),
            "num_industries": len(c.get("industries", [])),
            "is_active": 1 if c.get("status") == "Active" else 0,
        })

    df = pd.DataFrame(rows, columns=FEATURE_COLUMNS)

    # Median-fill nulls
    for col in ["team_size", "batch_recency_days", "days_since_launch"]:
        median = df[col].median()
        fill_val = median if pd.notna(median) else 0
        df[col] = df[col].fillna(fill_val)

    return df
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/ml/test_features.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/ml/features.py tests/ml/test_features.py
git commit -m "feat: feature engineering for reachability model"
```

---

### Task 5: Labeling workflow

**Files:**
- Create: `tests/ml/test_labeling.py`
- Create: `backend/ml/labeling.py`

- [ ] **Step 1: Write failing tests for labeling export/import**

Create `tests/ml/test_labeling.py`:

```python
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
    assert "name" in df.columns
    assert "reachability_label" in df.columns
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


def test_import_labels_reads_csv(tmp_path):
    csv_path = tmp_path / "labels.csv"
    csv_path.write_text(
        "name,description,batch,team_size,stage,top_company,website,reachability_label\n"
        "Co1,Desc,Winter 2024,3,Early,False,https://co1.com,1\n"
        "Co2,Desc,Summer 2023,50,Growth,True,https://co2.com,0\n"
    )
    df = import_labels(str(csv_path))
    assert len(df) == 2
    assert list(df["reachability_label"]) == [1, 0]
    assert list(df["name"]) == ["Co1", "Co2"]


def test_import_labels_rejects_missing_labels(tmp_path):
    csv_path = tmp_path / "labels.csv"
    csv_path.write_text(
        "name,description,batch,team_size,stage,top_company,website,reachability_label\n"
        "Co1,Desc,Winter 2024,3,Early,False,https://co1.com,1\n"
        "Co2,Desc,Summer 2023,50,Growth,True,https://co2.com,\n"
    )
    try:
        import_labels(str(csv_path))
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "missing" in str(e).lower() or "empty" in str(e).lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/ml/test_labeling.py -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement labeling.py**

Create `backend/ml/labeling.py`:

```python
"""Labeling workflow for reachability training data."""

import json
import os

import pandas as pd

from backend.ml.config import LABELING_SAMPLE_SIZE

LABELING_COLUMNS = [
    "name", "description", "batch", "team_size", "stage",
    "top_company", "website", "reachability_label",
]

LABELING_GUIDE = """Reachability Labeling Guide
============================

Label each company: will the founder likely respond to a cold email from a
high school or early-college student offering to help?

Label 1 (likely responds) if MOST of these are true:
  - Team size under 10
  - Early stage (pre-seed, seed)
  - NOT a "top company" (not Airbnb-level famous)
  - Recently launched (last 1-2 years)
  - Description suggests they need hands-on help

Label 0 (unlikely responds) if ANY of these are true:
  - Large team (30+)
  - Growth or Late stage
  - Top company flag is True
  - Company is acquired or inactive
  - Description suggests enterprise/government focus with no student angle

When in doubt, label 0 (conservative).
"""


def export_labeling_csv(
    raw_data_path: str,
    output_path: str,
    sample_size: int = LABELING_SAMPLE_SIZE,
) -> None:
    """Export a CSV of companies for hand-labeling."""
    with open(raw_data_path) as f:
        companies = json.load(f)

    df = pd.DataFrame(companies)

    if len(df) > sample_size:
        df = df.sample(n=sample_size, random_state=42)

    # Select columns for labeling, add empty label column
    export_cols = [c for c in LABELING_COLUMNS if c != "reachability_label" and c in df.columns]
    out = df[export_cols].copy()
    out["reachability_label"] = pd.NA

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    out.to_csv(output_path, index=False)

    # Write guide alongside CSV
    guide_path = os.path.join(os.path.dirname(os.path.abspath(output_path)), "labeling_guide.txt")
    with open(guide_path, "w") as f:
        f.write(LABELING_GUIDE)

    print(f"[DONE] Exported {len(out)} companies to {output_path}")
    print(f"[DONE] Labeling guide written to {guide_path}")


def import_labels(label_path: str) -> pd.DataFrame:
    """Import hand-labeled CSV and validate."""
    df = pd.read_csv(label_path)

    if "reachability_label" not in df.columns:
        raise ValueError("CSV missing 'reachability_label' column")

    missing = df["reachability_label"].isna().sum()
    if missing > 0:
        raise ValueError(f"{missing} rows have empty/missing labels. Fill all labels before importing.")

    df["reachability_label"] = df["reachability_label"].astype(int)
    print(f"[DONE] Imported {len(df)} labels: {df['reachability_label'].value_counts().to_dict()}")
    return df


if __name__ == "__main__":
    from backend.ml.config import RAW_DATA_PATH, LABEL_EXPORT_PATH
    export_labeling_csv(RAW_DATA_PATH, LABEL_EXPORT_PATH)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/ml/test_labeling.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/ml/labeling.py tests/ml/test_labeling.py
git commit -m "feat: labeling workflow for hand-labeling reachability data"
```

---

### Task 6: Training pipeline

**Files:**
- Create: `tests/ml/test_train.py`
- Create: `backend/ml/train.py`

- [ ] **Step 1: Write failing tests for training pipeline**

Create `tests/ml/test_train.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/ml/test_train.py -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement train.py**

Create `backend/ml/train.py`:

```python
"""Train and evaluate reachability models."""

import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics import classification_report
from xgboost import XGBClassifier

from backend.ml.features import build_features, FEATURE_COLUMNS
from backend.ml.config import (
    RAW_DATA_PATH, LABEL_PATH, MODEL_PATH, FEATURE_COLS_PATH,
    N_FOLDS, RANDOM_SEED,
)


def load_training_data(raw_data_path: str, label_path: str) -> tuple[pd.DataFrame, pd.Series]:
    """Load raw companies and labels, return feature matrix and label vector."""
    with open(raw_data_path) as f:
        companies = json.load(f)

    labels_df = pd.read_csv(label_path)
    label_map = dict(zip(labels_df["name"], labels_df["reachability_label"]))

    # Filter to only labeled companies
    labeled = [c for c in companies if c["name"] in label_map]
    if not labeled:
        raise ValueError("No matching companies found between raw data and labels")

    X = build_features(labeled)
    y = pd.Series([label_map[c["name"]] for c in labeled], dtype=int)

    print(f"[INFO] Training data: {len(X)} samples, {y.sum()} positive, {len(y) - y.sum()} negative")
    return X, y


def train_and_evaluate(
    raw_data_path: str = RAW_DATA_PATH,
    label_path: str = LABEL_PATH,
    model_path: str = MODEL_PATH,
    cols_path: str = FEATURE_COLS_PATH,
    n_folds: int = N_FOLDS,
) -> dict:
    """Train LR + XGBoost, evaluate with CV, save winner."""
    X, y = load_training_data(raw_data_path, label_path)

    cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=RANDOM_SEED)
    scoring = ["accuracy", "precision", "recall", "f1", "roc_auc"]

    models = {
        "lr": LogisticRegression(
            class_weight="balanced", max_iter=1000, random_state=RANDOM_SEED,
        ),
        "xgb": XGBClassifier(
            n_estimators=100, max_depth=3, eval_metric="logloss",
            random_state=RANDOM_SEED, use_label_encoder=False,
        ),
    }

    results = {}
    for name, model in models.items():
        cv_results = cross_validate(model, X, y, cv=cv, scoring=scoring)
        metrics = {}
        for metric in scoring:
            key = f"test_{metric}"
            scores = cv_results[key]
            metrics[metric] = {"mean": float(np.mean(scores)), "std": float(np.std(scores))}
            print(f"  {name} {metric}: {np.mean(scores):.3f} ± {np.std(scores):.3f}")
        results[name] = metrics

    # Pick winner by F1
    lr_f1 = results["lr"]["f1"]["mean"]
    xgb_f1 = results["xgb"]["f1"]["mean"]
    winner_name = "xgb" if xgb_f1 > lr_f1 else "lr"
    print(f"\n[INFO] Winner: {winner_name} (F1: {results[winner_name]['f1']['mean']:.3f})")
    results["winner"] = winner_name

    # Retrain winner on all data
    winner_model = models[winner_name]
    winner_model.fit(X, y)

    # Print feature importances
    if winner_name == "lr":
        importances = dict(zip(FEATURE_COLUMNS, winner_model.coef_[0]))
    else:
        importances = dict(zip(FEATURE_COLUMNS, winner_model.feature_importances_))
    print("\n[INFO] Feature importances:")
    for feat, imp in sorted(importances.items(), key=lambda x: abs(x[1]), reverse=True):
        print(f"  {feat}: {imp:.4f}")

    # Print classification report on full training set (for quick inspection)
    y_pred = winner_model.predict(X)
    print(f"\n[INFO] Classification report (full training set):")
    print(classification_report(y, y_pred))

    # Save model and feature columns
    os.makedirs(os.path.dirname(os.path.abspath(model_path)), exist_ok=True)
    joblib.dump(winner_model, model_path)
    with open(cols_path, "w") as f:
        json.dump(FEATURE_COLUMNS, f)

    print(f"[DONE] Model saved to {model_path}")
    return results


if __name__ == "__main__":
    train_and_evaluate()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/ml/test_train.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add backend/ml/train.py tests/ml/test_train.py
git commit -m "feat: training pipeline with LR + XGBoost and CV evaluation"
```

---

### Task 7: Prediction pipeline

**Files:**
- Create: `tests/ml/test_predict.py`
- Create: `backend/ml/predict.py`

- [ ] **Step 1: Write failing tests for predict**

Create `tests/ml/test_predict.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/ml/test_predict.py -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement predict.py**

Create `backend/ml/predict.py`:

```python
"""Predict reachability scores for all companies."""

import json
import os

import joblib
import pandas as pd

from backend.ml.features import build_features
from backend.ml.config import (
    RAW_DATA_PATH, MODEL_PATH, FEATURE_COLS_PATH,
    SCORES_OUTPUT_PATH, HIGH_THRESHOLD, LOW_THRESHOLD,
)


def score_to_category(probability: float) -> str:
    """Map probability to reachability category."""
    if probability >= HIGH_THRESHOLD:
        return "high"
    elif probability >= LOW_THRESHOLD:
        return "medium"
    else:
        return "low"


def predict_all(
    raw_data_path: str = RAW_DATA_PATH,
    model_path: str = MODEL_PATH,
    cols_path: str = FEATURE_COLS_PATH,
    output_path: str = SCORES_OUTPUT_PATH,
) -> list[dict]:
    """Load model, score all companies, write results."""
    with open(raw_data_path) as f:
        companies = json.load(f)

    with open(cols_path) as f:
        feature_cols = json.load(f)

    model = joblib.load(model_path)
    X = build_features(companies)
    X = X[feature_cols]  # ensure column order matches training

    probas = model.predict_proba(X)[:, 1]

    results = []
    for company, proba in zip(companies, probas):
        results.append({
            "name": company["name"],
            "reachability_score": score_to_category(float(proba)),
            "reachability_probability": round(float(proba), 4),
        })

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    # Print distribution
    from collections import Counter
    dist = Counter(r["reachability_score"] for r in results)
    print(f"[DONE] Scored {len(results)} companies: {dict(dist)}")

    return results


if __name__ == "__main__":
    predict_all()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/ml/test_predict.py -v`
Expected: 2 passed

- [ ] **Step 5: Run all tests**

Run: `python -m pytest tests/ -v -k "not integration"`
Expected: all tests pass (scraper tests + ML tests)

- [ ] **Step 6: Commit**

```bash
git add backend/ml/predict.py tests/ml/test_predict.py
git commit -m "feat: prediction pipeline outputs reachability scores"
```

---

### Task 8: Export labeling CSV from real data

**Files:**
- None (running existing code)

- [ ] **Step 1: Run labeling export**

Run: `python -m backend.ml.labeling`

Expected:
```
[DONE] Exported 200 companies to data/labeling/to_label.csv
[DONE] Labeling guide written to data/labeling/labeling_guide.txt
```

- [ ] **Step 2: Verify the export**

Run: `python3 -c "import pandas as pd; df=pd.read_csv('data/labeling/to_label.csv'); print(f'{len(df)} rows'); print(df.columns.tolist()); print(df.head(3).to_string())"`

Verify:
- 200 rows
- Columns include: name, description, batch, team_size, stage, top_company, website, reachability_label
- reachability_label column is all empty/NaN

- [ ] **Step 3: Commit the labeling CSV to repo (so user can fill it in)**

```bash
mkdir -p data/labeling
git add -f data/labeling/to_label.csv data/labeling/labeling_guide.txt
git commit -m "chore: export labeling CSV for hand-labeling (200 companies)"
```

Note: `data/` is gitignored, so use `git add -f` to force-add the labeling files specifically.
