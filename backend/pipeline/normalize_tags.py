"""Post-processing: normalize need_tags into a canonical skill vocabulary."""

import json
import os
from collections import Counter
from difflib import SequenceMatcher

from backend.pipeline.enrich_config import ENRICHED_OUTPUT_PATH, VOCAB_OUTPUT_PATH


def collect_raw_tags(companies: list[dict]) -> list[str]:
    """Collect all need_tags from all companies (including duplicates)."""
    tags = []
    for company in companies:
        tags.extend(company.get("need_tags", []))
    return tags


def deduplicate_tags(raw_tags: list[str], similarity_threshold: float = 0.75) -> list[str]:
    """Deduplicate tags using case normalization and fuzzy matching.

    Returns a sorted list of canonical (lowercased) tags.
    """
    normalized_counts = Counter(tag.lower().strip() for tag in raw_tags)
    unique_tags = sorted(normalized_counts.keys(), key=lambda t: -normalized_counts[t])

    canonical = []
    for tag in unique_tags:
        is_duplicate = False
        for existing in canonical:
            similarity = SequenceMatcher(None, tag, existing).ratio()
            if similarity >= similarity_threshold:
                is_duplicate = True
                break
        if not is_duplicate:
            canonical.append(tag)

    return sorted(canonical)


def _build_tag_mapping(raw_tags: list[str], canonical: list[str], similarity_threshold: float = 0.75) -> dict[str, str]:
    """Build a mapping from every raw tag to its canonical form."""
    mapping = {}
    for raw in set(raw_tags):
        lower = raw.lower().strip()
        if lower in canonical:
            mapping[raw] = lower
            continue
        best_match = None
        best_score = 0.0
        for canon in canonical:
            score = SequenceMatcher(None, lower, canon).ratio()
            if score > best_score:
                best_score = score
                best_match = canon
        if best_match and best_score >= similarity_threshold:
            mapping[raw] = best_match
        else:
            mapping[raw] = lower
    return mapping


def remap_company_tags(company: dict, tag_mapping: dict[str, str]) -> dict:
    """Remap a company's need_tags using the tag mapping. Returns a copy."""
    remapped = dict(company)
    remapped["need_tags"] = [
        tag_mapping.get(tag, tag) for tag in company.get("need_tags", [])
    ]
    return remapped


def normalize_all(
    enriched_path: str = ENRICHED_OUTPUT_PATH,
    vocab_output_path: str = VOCAB_OUTPUT_PATH,
):
    """Run full normalization: collect, dedup, remap, save."""
    with open(enriched_path) as f:
        companies = json.load(f)

    raw_tags = collect_raw_tags(companies)
    print(f"[INFO] Collected {len(raw_tags)} raw tags from {len(companies)} companies")

    canonical = deduplicate_tags(raw_tags)
    print(f"[INFO] Deduplicated to {len(canonical)} canonical tags")

    tag_mapping = _build_tag_mapping(raw_tags, canonical)

    remapped = [remap_company_tags(c, tag_mapping) for c in companies]

    os.makedirs(os.path.dirname(os.path.abspath(vocab_output_path)), exist_ok=True)
    with open(vocab_output_path, "w") as f:
        json.dump(canonical, f, indent=2)

    with open(enriched_path, "w") as f:
        json.dump(remapped, f, indent=2)

    print(f"[DONE] Saved {len(canonical)} skills to {vocab_output_path}")
    print(f"[DONE] Updated {len(remapped)} companies in {enriched_path}")


if __name__ == "__main__":
    normalize_all()
