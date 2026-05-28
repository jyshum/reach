"""Interest vocabulary — loads curated YC tags for matching and the frontend picker.

Replaces capabilities.py for matching purposes. capabilities.py is kept
for backwards compatibility but no longer used in ranking.
"""

import json
import os

_CURATED_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "curated_tags.json")

_CACHE: dict | None = None


def _load() -> dict:
    global _CACHE
    if _CACHE is None:
        with open(_CURATED_PATH) as f:
            _CACHE = json.load(f)
    return _CACHE


def get_categories() -> list[dict]:
    """Return list of {name, tags} for the frontend picker."""
    return _load()["categories"]


def get_valid_tags() -> set[str]:
    """Return the set of all valid curated tag strings."""
    return set(_load()["valid_tags"])


def get_tag_to_category() -> dict[str, str]:
    """Return mapping of curated tag -> category name."""
    return _load()["tag_to_category"]
