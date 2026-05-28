"""Curate YC's 232 raw tags into a clean interest vocabulary.

Collapses duplicates, removes too-broad/too-niche tags, groups into
visual categories for the frontend interest picker.
"""

import json
import os
from collections import Counter

_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
RAW_DATA_PATH = os.path.join(_ROOT, "data", "raw_companies.json")
OUTPUT_PATH = os.path.join(_ROOT, "data", "curated_tags.json")

MIN_TAG_COUNT = 5
MAX_TAG_COUNT = 300

# Tags that should be merged into a single canonical tag.
COLLAPSE_MAP = {
    "AI": "AI / Machine Learning",
    "Artificial Intelligence": "AI / Machine Learning",
    "Machine Learning": "AI / Machine Learning",
    "AIOps": "AI / Machine Learning",
    "Enterprise": "Enterprise Software",
    "Enterprise Software": "Enterprise Software",
}

# Manual assignment of curated tags to visual categories.
CATEGORY_ASSIGNMENTS = {
    "Generative AI": "AI / Machine Learning",
    "AI Assistant": "AI / Machine Learning",
    "Conversational AI": "AI / Machine Learning",
    "Computer Vision": "AI / Machine Learning",
    "NLP": "AI / Machine Learning",
    "Developer Tools": "Developer Tools & Infrastructure",
    "Infrastructure": "Developer Tools & Infrastructure",
    "Open Source": "Developer Tools & Infrastructure",
    "API": "Developer Tools & Infrastructure",
    "DevOps": "Developer Tools & Infrastructure",
    "Fintech": "Finance & Payments",
    "Payments": "Finance & Payments",
    "Finance": "Finance & Payments",
    "Healthcare": "Healthcare & Bio",
    "Health Tech": "Healthcare & Bio",
    "Biotech": "Healthcare & Bio",
    "Drug Discovery": "Healthcare & Bio",
    "Diagnostics": "Healthcare & Bio",
    "Analytics": "Data & Analytics",
    "Data Engineering": "Data & Analytics",
    "Automation": "Operations & Automation",
    "Workflow Automation": "Operations & Automation",
    "Logistics": "Operations & Automation",
    "Sales": "Sales & Marketing",
    "Marketing": "Sales & Marketing",
    "Compliance": "Security & Compliance",
    "Security": "Security & Compliance",
    "Education": "Education & Research",
    "Climate": "Climate & Energy",
    "Robotics": "Hardware & Robotics",
    "Consumer": "Consumer",
    "Productivity": "Productivity",
}


def count_raw_tags(raw_path: str = RAW_DATA_PATH) -> dict[str, int]:
    """Count occurrences of each tag across all companies."""
    with open(raw_path) as f:
        companies = json.load(f)
    counts: dict[str, int] = Counter()
    for company in companies:
        for tag in company.get("tags", []):
            counts[tag] += 1
    return dict(counts)


def collapse_duplicates(
    tag_counts: dict[str, int], collapse_map: dict[str, str]
) -> dict[str, int]:
    """Merge duplicate tags into canonical names, summing their counts."""
    collapsed: dict[str, int] = {}
    for tag, count in tag_counts.items():
        canonical = collapse_map.get(tag, tag)
        collapsed[canonical] = collapsed.get(canonical, 0) + count
    return collapsed


def filter_by_frequency(
    tag_counts: dict[str, int],
    min_count: int = MIN_TAG_COUNT,
    max_count: int = MAX_TAG_COUNT,
) -> dict[str, int]:
    """Remove tags that are too broad or too niche."""
    return {
        tag: count
        for tag, count in tag_counts.items()
        if min_count <= count <= max_count
    }


def build_categories(
    tags: list[str], category_assignments: dict[str, str]
) -> list[dict]:
    """Group tags into named categories for the frontend picker."""
    cat_map: dict[str, list[str]] = {}
    for tag in sorted(tags):
        category = category_assignments.get(tag, "Other")
        cat_map.setdefault(category, []).append(tag)

    return [{"name": name, "tags": tags} for name, tags in sorted(cat_map.items())]


def map_company_tags(
    company_raw_tags: list[str],
    collapse_map: dict[str, str],
    valid_tags: set[str],
) -> list[str]:
    """Map a company's raw YC tags to curated tags, dropping invalid ones."""
    mapped = set()
    for tag in company_raw_tags:
        canonical = collapse_map.get(tag, tag)
        if canonical in valid_tags:
            mapped.add(canonical)
    return sorted(mapped)


def curate_tags(raw_path: str = RAW_DATA_PATH, output_path: str = OUTPUT_PATH):
    """Full curation pipeline: count -> collapse -> filter -> categorize -> save."""
    raw_counts = count_raw_tags(raw_path)
    print(f"[INFO] Raw unique tags: {len(raw_counts)}")

    collapsed = collapse_duplicates(raw_counts, COLLAPSE_MAP)
    print(f"[INFO] After collapsing duplicates: {len(collapsed)}")

    filtered = filter_by_frequency(collapsed)
    print(f"[INFO] After frequency filter ({MIN_TAG_COUNT}-{MAX_TAG_COUNT}): {len(filtered)}")

    valid_tags = set(filtered.keys())
    categories = build_categories(list(valid_tags), CATEGORY_ASSIGNMENTS)

    # Build reverse mapping: tag -> category
    tag_to_category = {}
    for cat in categories:
        for tag in cat["tags"]:
            tag_to_category[tag] = cat["name"]

    # Track what was removed and why
    removed = {
        "too_broad": {t: c for t, c in collapsed.items() if c > MAX_TAG_COUNT},
        "too_niche": {t: c for t, c in collapsed.items() if c < MIN_TAG_COUNT},
        "collapsed_into": {k: v for k, v in COLLAPSE_MAP.items() if k != v},
    }

    output = {
        "categories": categories,
        "tag_to_category": tag_to_category,
        "valid_tags": sorted(valid_tags),
        "removed": removed,
        "stats": {
            "raw_unique": len(raw_counts),
            "after_collapse": len(collapsed),
            "final_curated": len(filtered),
            "num_categories": len(categories),
        },
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"[DONE] {len(filtered)} curated tags in {len(categories)} categories -> {output_path}")

    # Print distribution
    for cat in categories:
        print(f"  {cat['name']}: {', '.join(cat['tags'])}")

    return output


if __name__ == "__main__":
    curate_tags()
