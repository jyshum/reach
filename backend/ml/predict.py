"""Predict reachability scores for all companies."""

import json
import os
from collections import Counter

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

    dist = Counter(r["reachability_score"] for r in results)
    print(f"[DONE] Scored {len(results)} companies: {dict(dist)}")

    return results


if __name__ == "__main__":
    predict_all()
