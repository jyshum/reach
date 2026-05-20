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
