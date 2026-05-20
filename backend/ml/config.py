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
