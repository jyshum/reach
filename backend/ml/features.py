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
