"""Re-enrich companies with constrained capability tags from fixed vocabulary."""

import json
import time
import requests

from backend.capabilities import ALL_TIER2, TIER2_LABELS
from backend.pipeline.enrich_config import (
    OLLAMA_URL,
    OLLAMA_MODEL,
    OLLAMA_TEMPERATURE,
)

SAVE_EVERY = 50
MAX_RETRIES = 3

SYSTEM_PROMPT = "You are a startup analyst. Given a company description, select the most relevant capabilities from the provided list. RESPOND WITH VALID JSON ONLY."

PROMPT_TEMPLATE = """Company: {name}
Description: {description}
Long description: {long_description}
Tags: {tags}
Industries: {industries}

From ONLY this list of capabilities, select 2-4 that this company most needs help with:
{capability_list}

Respond with a JSON object: {{"capability_tags": ["tag1", "tag2", ...]}}
Only use exact values from the list above. Pick 2-4."""


def build_prompt(company: dict) -> str:
    capability_list = "\n".join(f"- {cap} ({TIER2_LABELS[cap]})" for cap in ALL_TIER2)
    return PROMPT_TEMPLATE.format(
        name=company.get("name", ""),
        description=company.get("description", ""),
        long_description=(company.get("long_description") or "")[:500],
        tags=", ".join(company.get("tags", []) or []),
        industries=", ".join(company.get("industries", []) or []),
        capability_list=capability_list,
    )


def call_ollama(prompt: str) -> dict | None:
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "system": SYSTEM_PROMPT,
                "stream": False,
                "options": {"temperature": OLLAMA_TEMPERATURE, "num_predict": 128},
            },
            timeout=60,
        )
        response.raise_for_status()
        text = response.json()["response"]
        # Strip markdown code fences if present
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    except Exception:
        return None


def validate_tags(data: dict) -> list[str]:
    tags = data.get("capability_tags", [])
    if not isinstance(tags, list):
        return []
    valid = [t for t in tags if t in ALL_TIER2]
    return valid


def enrich_company(company: dict) -> list[str]:
    prompt = build_prompt(company)
    for attempt in range(MAX_RETRIES):
        result = call_ollama(prompt)
        if result:
            tags = validate_tags(result)
            if 2 <= len(tags) <= 4:
                return tags
    return []


def enrich_all(
    input_path: str = "data/enriched_companies.json",
    output_path: str = "data/capability_tags.json",
):
    with open(input_path) as f:
        companies = json.load(f)

    # Load existing progress
    try:
        with open(output_path) as f:
            results = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        results = {}

    total = len(companies)
    for i, company in enumerate(companies):
        name = company.get("name", "")
        if name in results:
            continue

        tags = enrich_company(company)
        results[name] = tags

        if (i + 1) % SAVE_EVERY == 0:
            with open(output_path, "w") as f:
                json.dump(results, f, indent=2)
            print(f"  Saved progress: {i + 1}/{total}")

        time.sleep(0.5)

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    tagged = sum(1 for v in results.values() if v)
    print(f"Done. {tagged}/{total} companies tagged.")
    return results


if __name__ == "__main__":
    enrich_all()
