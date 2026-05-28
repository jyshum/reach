"""Tests for YC tag curation logic."""

import pytest
from backend.pipeline.curate_tags import (
    collapse_duplicates,
    filter_by_frequency,
    build_categories,
)


SAMPLE_TAG_COUNTS = {
    "Artificial Intelligence": 422,
    "AI": 381,
    "Machine Learning": 51,
    "B2B": 351,
    "SaaS": 249,
    "Developer Tools": 191,
    "Generative AI": 143,
    "Fintech": 118,
    "Healthcare": 65,
    "Open Source": 66,
    "Biotech": 35,
    "Niche Tag": 3,
}

# Collapse map: keys are raw tags, values are the canonical name they merge into
COLLAPSE_MAP = {
    "AI": "AI / Machine Learning",
    "Artificial Intelligence": "AI / Machine Learning",
    "Machine Learning": "AI / Machine Learning",
}


def test_collapse_duplicates_merges_counts():
    collapsed = collapse_duplicates(SAMPLE_TAG_COUNTS, COLLAPSE_MAP)
    # AI + Artificial Intelligence + Machine Learning = 422 + 381 + 51 = 854
    assert collapsed["AI / Machine Learning"] == 854
    assert "AI" not in collapsed
    assert "Artificial Intelligence" not in collapsed
    assert "Machine Learning" not in collapsed
    # Unaffected tags remain
    assert collapsed["Developer Tools"] == 191


def test_filter_by_frequency_removes_extremes():
    tag_counts = {
        "Too Broad": 400,
        "Good Tag": 50,
        "Also Good": 20,
        "Too Niche": 3,
    }
    filtered = filter_by_frequency(tag_counts, min_count=5, max_count=300)
    assert "Good Tag" in filtered
    assert "Also Good" in filtered
    assert "Too Broad" not in filtered
    assert "Too Niche" not in filtered


def test_build_categories_groups_tags():
    tags = ["Generative AI", "Developer Tools", "Open Source", "Fintech", "Biotech"]
    # Category assignments map tag -> category name
    category_assignments = {
        "Generative AI": "AI / Machine Learning",
        "Developer Tools": "Developer Tools & Infrastructure",
        "Open Source": "Developer Tools & Infrastructure",
        "Fintech": "Finance",
        "Biotech": "Healthcare & Bio",
    }
    categories = build_categories(tags, category_assignments)
    ai_cat = next(c for c in categories if c["name"] == "AI / Machine Learning")
    assert "Generative AI" in ai_cat["tags"]
    devtools_cat = next(c for c in categories if c["name"] == "Developer Tools & Infrastructure")
    assert "Developer Tools" in devtools_cat["tags"]
    assert "Open Source" in devtools_cat["tags"]
