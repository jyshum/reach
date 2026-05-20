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
