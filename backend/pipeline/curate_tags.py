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
MAX_TAG_COUNT = 500

# Tags to remove entirely — too generic to be useful as interest filters.
# "AI" and "Artificial Intelligence" are vague; specific sub-tags (Generative AI,
# Machine Learning, Computer Vision) are kept. "B2B" and "SaaS" are business
# models, not domains.
REMOVE_TAGS = {"AI", "Artificial Intelligence", "B2B", "SaaS"}

# Tags that should be merged into a single canonical tag.
COLLAPSE_MAP = {
    "AIOps": "Machine Learning",
    "Enterprise": "Enterprise Software",
    "Enterprise Software": "Enterprise Software",
    "Hard Tech": "Hardware",
    "Digital Health": "Health Tech",
    "Supply Chain": "Logistics",
    # Industry name aliases (from fallback)
    "Engineering, Product and Design": "Developer Tools & Infrastructure",
    "Industrials": "Hardware & Robotics",
    "Manufacturing and Robotics": "Hardware & Robotics",
    "Supply Chain and Logistics": "Operations & Automation",
    "Finance and Accounting": "Finance & Payments",
    "Healthcare IT": "Healthcare & Bio",
    "Healthcare Services": "Healthcare & Bio",
    "Aviation and Space": "Hardware & Robotics",
}

# Manual assignment of curated tags to visual categories.
CATEGORY_ASSIGNMENTS = {
    "Generative AI": "AI / Machine Learning",
    "AI Assistant": "AI / Machine Learning",
    "Conversational AI": "AI / Machine Learning",
    "Computer Vision": "AI / Machine Learning",
    "NLP": "AI / Machine Learning",
    "Machine Learning": "AI / Machine Learning",
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
    "Manufacturing": "Operations & Automation",
    "Sales": "Sales & Marketing",
    "Marketing": "Sales & Marketing",
    "E-commerce": "Sales & Marketing",
    "Marketplace": "Sales & Marketing",
    "Compliance": "Security & Compliance",
    "Security": "Security & Compliance",
    "Education": "Education",
    "Climate": "Climate & Energy",
    "Robotics": "Hardware & Robotics",
    "Hardware": "Hardware & Robotics",
    "Consumer": "Consumer",
    "Video": "Consumer",
    "Productivity": "Productivity",
    "Enterprise Software": "Productivity",
    # Additional industry-name tags from fallback
    "Legal": "Security & Compliance",
    "Operations": "Operations & Automation",
    "Insurance": "Finance & Payments",
    "Real Estate and Construction": "Real Estate",
    "Energy": "Climate & Energy",
    "Gaming": "Consumer",
    "Defense": "Security & Compliance",
    "Agriculture": "Climate & Energy",
    "Recruiting": "Productivity",
    "Government": "Security & Compliance",
}


def get_company_raw_tags(company: dict) -> list[str]:
    """Get a company's tags, falling back to industries if tags is empty.

    Many YC companies (~28%) have empty tags arrays but always have
    industries. We use industries as a fallback source for domain tagging.
    """
    tags = [t for t in company.get("tags", []) if t not in REMOVE_TAGS]
    if tags:
        return tags
    # Fallback: use industries (skip "B2B" which is a business model, not a domain)
    return [ind for ind in company.get("industries", []) if ind != "B2B"]


def count_raw_tags(raw_path: str = RAW_DATA_PATH) -> dict[str, int]:
    """Count occurrences of each tag across all companies.

    Strips tags in REMOVE_TAGS. Falls back to industries for tagless companies.
    """
    with open(raw_path) as f:
        companies = json.load(f)
    counts: dict[str, int] = Counter()
    for company in companies:
        for tag in get_company_raw_tags(company):
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
    company: dict,
    collapse_map: dict[str, str],
    valid_tags: set[str],
) -> list[str]:
    """Map a company's raw tags (with industry fallback) to curated tags."""
    mapped = set()
    for tag in get_company_raw_tags(company):
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
