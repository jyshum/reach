"""Enrich YC companies with LLM-generated structured fields."""

import json
import os
import re
import requests
from difflib import get_close_matches

from backend.pipeline.enrich_config import (
    INDUSTRY_LIST, VALID_TECHNICAL_LEVELS, VALID_STAGE_DETAILS,
    SYSTEM_PROMPT, OLLAMA_URL, OLLAMA_MODEL,
    OLLAMA_TEMPERATURE, OLLAMA_NUM_PREDICT,
    MAX_RETRIES, SAVE_EVERY,
    RAW_DATA_PATH, ENRICHED_OUTPUT_PATH, FAILURES_OUTPUT_PATH,
    build_prompt,
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
        fixed["industry"] = match if match else "other"

    if "technical_level" in fixed and fixed["technical_level"] not in VALID_TECHNICAL_LEVELS:
        match = _closest_match(fixed["technical_level"], VALID_TECHNICAL_LEVELS)
        if match:
            fixed["technical_level"] = match

    if "stage_detail" in fixed and fixed["stage_detail"] not in VALID_STAGE_DETAILS:
        match = _closest_match(fixed["stage_detail"], VALID_STAGE_DETAILS)
        if match:
            fixed["stage_detail"] = match


    return fixed


def _call_ollama(prompt: str) -> str | None:
    """Call Ollama API and return raw response text."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": OLLAMA_TEMPERATURE,
            "num_predict": OLLAMA_NUM_PREDICT,
        },
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        # Qwen3 uses thinking mode by default — JSON lands in "thinking", not "response"
        return data.get("response", "") or data.get("thinking", "")
    except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
        print(f"[ERROR] Ollama call failed: {e}")
        return None


def enrich_company(company: dict) -> dict | None:
    """Enrich a single company. Returns enriched fields dict or None on failure."""
    prompt = build_prompt(company)
    attempts = 1 + MAX_RETRIES

    for attempt in range(attempts):
        raw = _call_ollama(prompt)
        if raw is None:
            continue

        data = parse_response(raw)
        if data is None:
            print(f"[WARN] {company['name']}: invalid JSON (attempt {attempt + 1})")
            continue

        data = auto_fix_enrichment(data)
        errors = validate_enrichment(data)

        if not errors:
            return data

        print(f"[WARN] {company['name']}: validation errors (attempt {attempt + 1}): {errors}")

    return None


def enrich_all(
    raw_data_path: str = RAW_DATA_PATH,
    output_path: str = ENRICHED_OUTPUT_PATH,
    failures_path: str = FAILURES_OUTPUT_PATH,
) -> list[dict]:
    """Enrich all companies. Resumable — skips already-enriched companies."""
    with open(raw_data_path) as f:
        companies = json.load(f)

    results = []
    done_names = set()
    if os.path.exists(output_path):
        with open(output_path) as f:
            results = json.load(f)
            done_names = {r["name"] for r in results}
        print(f"[INFO] Resuming: {len(done_names)} already enriched")

    failures = []
    to_process = [c for c in companies if c["name"] not in done_names]
    print(f"[INFO] Enriching {len(to_process)} companies ({len(done_names)} skipped)")

    for i, company in enumerate(to_process):
        print(f"[{i + 1}/{len(to_process)}] Enriching {company['name']}...", end=" ", flush=True)
        enriched = enrich_company(company)

        if enriched:
            merged = {**company, **enriched}
            results.append(merged)
            print("OK")
        else:
            failures.append({"name": company["name"], "reason": "max retries exceeded"})
            print("FAILED")

        if (i + 1) % SAVE_EVERY == 0:
            _save_json(results, output_path)
            print(f"[INFO] Progress saved: {len(results)} enriched, {len(failures)} failed ({i + 1}/{len(to_process)})")

    _save_json(results, output_path)
    if failures:
        _save_json(failures, failures_path)
    print(f"[DONE] Enriched {len(results)} companies, {len(failures)} failures")

    return results


def _save_json(data, path: str):
    """Write data to JSON file, creating parent dirs if needed."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    enrich_all()
