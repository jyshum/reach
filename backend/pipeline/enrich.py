"""Enrich YC companies with LLM-generated structured fields."""

import json
import re
from difflib import get_close_matches

from backend.pipeline.enrich_config import (
    INDUSTRY_LIST, VALID_TECHNICAL_LEVELS, VALID_STAGE_DETAILS,
)


def parse_response(raw: str) -> dict | None:
    """Parse LLM response as JSON. Handle markdown wrappers."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        return None


def validate_enrichment(data: dict) -> list[str]:
    """Validate enrichment data. Return list of error strings (empty = valid)."""
    errors = []

    required_fields = [
        "summary", "one_liner", "need_tags", "industry",
        "technical_level", "stage_detail", "specific_projects",
    ]
    for field in required_fields:
        if field not in data:
            errors.append(f"missing field: {field}")

    if "summary" in data:
        word_count = len(data["summary"].split())
        if word_count < 5:
            errors.append(f"summary too short: {word_count} words")
        if word_count > 100:
            errors.append(f"summary too long: {word_count} words")

    if "one_liner" in data:
        word_count = len(data["one_liner"].split())
        if word_count > 15:
            errors.append(f"one_liner too long: {word_count} words")

    if "need_tags" in data:
        tags = data["need_tags"]
        if not isinstance(tags, list) or len(tags) < 2 or len(tags) > 5:
            errors.append(f"need_tags must be a list of 2-5 items, got {tags}")

    if "industry" in data:
        if data["industry"] not in INDUSTRY_LIST:
            errors.append(f"industry '{data['industry']}' not in valid list")

    if "technical_level" in data:
        if data["technical_level"] not in VALID_TECHNICAL_LEVELS:
            errors.append(f"technical_level '{data['technical_level']}' invalid")

    if "stage_detail" in data:
        if data["stage_detail"] not in VALID_STAGE_DETAILS:
            errors.append(f"stage_detail '{data['stage_detail']}' invalid")

    if "specific_projects" in data:
        projects = data["specific_projects"]
        if not isinstance(projects, list) or len(projects) != 2:
            errors.append(f"specific_projects must be exactly 2 items, got {projects}")

    return errors


def _closest_match(value: str, value_list: list[str]) -> str | None:
    """Find closest match in a list using difflib, with substring fallback."""
    normalized = value.lower()
    matches = get_close_matches(normalized, value_list, n=1, cutoff=0.5)
    if matches:
        return matches[0]
    # Fallback: check if value is a substring of any valid item
    for item in value_list:
        if normalized in item:
            return item
    return None


def auto_fix_enrichment(data: dict) -> dict:
    """Attempt to auto-fix enum fields. Returns a copy with fixes applied."""
    fixed = dict(data)

    if "industry" in fixed and fixed["industry"] not in INDUSTRY_LIST:
        match = _closest_match(fixed["industry"], INDUSTRY_LIST)
        if match:
            fixed["industry"] = match

    if "technical_level" in fixed and fixed["technical_level"] not in VALID_TECHNICAL_LEVELS:
        match = _closest_match(fixed["technical_level"], VALID_TECHNICAL_LEVELS)
        if match:
            fixed["technical_level"] = match

    if "stage_detail" in fixed and fixed["stage_detail"] not in VALID_STAGE_DETAILS:
        match = _closest_match(fixed["stage_detail"], VALID_STAGE_DETAILS)
        if match:
            fixed["stage_detail"] = match


    return fixed
