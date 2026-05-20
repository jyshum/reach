"""Labeling workflow for reachability training data."""

import json
import os

import pandas as pd

from backend.ml.config import LABELING_SAMPLE_SIZE

LABELING_COLUMNS = [
    "name", "description", "batch", "team_size_bucket", "is_hiring",
    "industries", "website", "reachability_label",
]

LABELING_GUIDE = """Reachability Labeling Guide
============================

Label each company: will the founder likely respond to a cold email from a
high school or early-college student offering to help?

All companies here are Active (inactive/acquired are pre-filtered out).

Label 1 (likely responds) if MOST of these are true:
  - Small team (1-5 people) — founder reads their own email
  - Recent batch (2025-2026) — still in early scrappy phase
  - Industry where a student could contribute (software, marketing, content)
  - Hiring is a plus, but not required (hiring status changes frequently)

Label 0 (unlikely responds) if ANY of these are true:
  - Large team (16+) — founder has layers between them and cold email
  - Specialized domain where students can't contribute (deep biotech, hardware)
  - Enterprise/government focus with no student angle
  - Company was recently acquired or shut down (YC directory may lag behind —
    check the website if something feels off)

Weaker negative signals (not automatic 0, but lean toward 0 when combined):
  - Not hiring — suggests less immediate need, but can change quickly
  - Older batch (2023) with no other positive signals

When in doubt, label 0 (conservative).
"""


def _team_size_bucket(size) -> str:
    """Convert team_size to a readable bucket."""
    if pd.isna(size) or size is None:
        return "unknown"
    size = int(size)
    if size <= 5:
        return "1-5"
    elif size <= 15:
        return "6-15"
    elif size <= 30:
        return "16-30"
    else:
        return "30+"


def export_labeling_csv(
    raw_data_path: str,
    output_path: str,
    sample_size: int = LABELING_SAMPLE_SIZE,
) -> None:
    """Export a CSV of Active companies for hand-labeling."""
    with open(raw_data_path) as f:
        companies = json.load(f)

    df = pd.DataFrame(companies)

    # Pre-filter: only Active companies
    active_count = len(df)
    df = df[df["status"] == "Active"]
    filtered_count = active_count - len(df)
    print(f"[INFO] Filtered out {filtered_count} inactive/acquired companies")

    if len(df) > sample_size:
        df = df.sample(n=sample_size, random_state=42)

    # Build export dataframe with labeling-friendly columns
    out = pd.DataFrame()
    out["name"] = df["name"].values
    out["description"] = df["description"].values
    out["batch"] = df["batch"].values
    out["team_size_bucket"] = df["team_size"].apply(_team_size_bucket).values
    out["is_hiring"] = df["is_hiring"].values
    out["industries"] = df["industries"].apply(lambda x: ", ".join(x) if isinstance(x, list) else "").values
    out["website"] = df["website"].values
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
