# LLM Enrichment Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich 1519 raw YC company records with 7 LLM-generated fields (summary, one_liner, need_tags, industry, technical_level, stage_detail, specific_projects), then normalize need_tags into a canonical skill vocabulary.

**Architecture:** Three new files in `backend/pipeline/`: config (prompts + constants), enrichment loop (Ollama calls + validation + resumability), and tag normalizer (post-processing). All run offline on dev machine via Ollama.

**Tech Stack:** Python, Ollama REST API (`localhost:11434`), `requests` (already in requirements.txt), `difflib` (stdlib, for fuzzy matching in normalization)

**Spec:** `docs/superpowers/specs/2026-05-20-llm-enrichment-design.md`

---

## File Structure

```
backend/pipeline/
├── scrape_yc.py          # existing, no changes
├── enrich_config.py      # NEW — prompts, model settings, industry list, validation constants
├── enrich.py             # NEW — main enrichment loop: build prompt, call Ollama, validate, save
├── normalize_tags.py     # NEW — collect raw need_tags, deduplicate, build skill vocabulary, remap
```

```
tests/pipeline/
├── test_scrape_yc.py     # existing, no changes
├── test_enrich_config.py # NEW — prompt building tests
├── test_enrich.py        # NEW — validation, parsing, enrichment loop tests
├── test_normalize_tags.py # NEW — dedup, clustering, remap tests
```

---

### Task 1: Enrichment Config — Constants and Prompt Builder

**Files:**
- Create: `backend/pipeline/enrich_config.py`
- Create: `tests/pipeline/test_enrich_config.py`

- [ ] **Step 1: Write test for prompt building**

```python
# tests/pipeline/test_enrich_config.py
from backend.pipeline.enrich_config import build_prompt, SYSTEM_PROMPT, INDUSTRY_LIST


def test_system_prompt_exists():
    assert "startup analyst" in SYSTEM_PROMPT.lower()
    assert "JSON" in SYSTEM_PROMPT


def test_build_prompt_includes_company_fields():
    company = {
        "name": "TestCo",
        "batch": "Winter 2024",
        "description": "AI for logistics.",
        "long_description": "We build AI tools for supply chain optimization.",
        "tags": ["AI", "Logistics"],
        "industries": ["B2B"],
        "team_size": 5,
        "stage": "Early",
    }
    prompt = build_prompt(company)
    assert "TestCo" in prompt
    assert "Winter 2024" in prompt
    assert "AI for logistics." in prompt
    assert "supply chain optimization" in prompt
    assert "summary" in prompt
    assert "need_tags" in prompt
    assert "specific_projects" in prompt


def test_build_prompt_handles_missing_long_description():
    company = {
        "name": "MinimalCo",
        "batch": "Summer 2023",
        "description": "Simple product.",
        "long_description": "",
        "tags": [],
        "industries": [],
        "team_size": None,
        "stage": "",
    }
    prompt = build_prompt(company)
    assert "MinimalCo" in prompt
    assert "Simple product." in prompt


def test_industry_list_has_expected_entries():
    assert "fintech" in INDUSTRY_LIST
    assert "healthcare" in INDUSTRY_LIST
    assert "other" in INDUSTRY_LIST
    assert len(INDUSTRY_LIST) == 17
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/pipeline/test_enrich_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.pipeline.enrich_config'`

- [ ] **Step 3: Implement enrich_config.py**

```python
# backend/pipeline/enrich_config.py
"""LLM enrichment configuration — prompts, model settings, constants."""

import os

_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")

RAW_DATA_PATH = os.path.join(_ROOT, "data", "raw_companies.json")
ENRICHED_OUTPUT_PATH = os.path.join(_ROOT, "data", "enriched_companies.json")
FAILURES_OUTPUT_PATH = os.path.join(_ROOT, "data", "enrichment_failures.json")
VOCAB_OUTPUT_PATH = os.path.join(_ROOT, "data", "skill_vocabulary.json")

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3:4b"
OLLAMA_TEMPERATURE = 0.3
OLLAMA_NUM_PREDICT = 512

MAX_RETRIES = 2
SAVE_EVERY = 50

INDUSTRY_LIST = [
    "fintech", "healthcare", "biotech", "developer-tools", "ai-ml",
    "education", "e-commerce", "logistics", "real-estate", "legal",
    "security", "enterprise-saas", "consumer", "media", "hardware",
    "climate", "other",
]

VALID_TECHNICAL_LEVELS = ["technical", "mixed", "non-technical"]
VALID_STAGE_DETAILS = ["building-mvp", "launched", "growing", "scaling"]

SYSTEM_PROMPT = (
    "You are a startup analyst. Given a YC startup's data, extract structured information.\n"
    "You MUST respond with valid JSON only. No commentary, no markdown, no explanation."
)

_FEW_SHOT_EXAMPLES = """
Example 1:
Company: Pando Bioscience
Batch: Winter 2023
Short description: Gen-AI Designed Enzymes for Pharmaceutical Innovation
Full description: Pando is an AI-driven synthetic biology company revolutionizing enzyme engineering for the pharmaceutical industry. Our ultra-high-throughput screening platform screens 1000-fold more enzymes 75% faster and 80% cheaper than traditional methods.
Tags: ['Generative AI', 'Synthetic Biology', 'Biotech', 'Diagnostics']
Industries: ['Healthcare', 'Industrial Bio']
Team size: 5
Stage: Early

Response:
{"summary": "Pando uses AI to design custom enzymes for pharmaceutical companies. Their screening platform tests thousands of enzyme variants faster and cheaper than traditional methods.", "one_liner": "AI enzyme design for pharma", "need_tags": ["Python scripting", "data visualization", "scientific writing", "web design", "lab data analysis"], "industry": "biotech", "technical_level": "technical", "stage_detail": "growing", "specific_projects": ["Build a dashboard to visualize enzyme screening results across experiments", "Write case studies explaining how their platform reduces drug manufacturing costs"]}

Example 2:
Company: BrightPath
Batch: Summer 2024
Short description: College admissions counseling for first-gen students
Full description: BrightPath provides affordable, AI-assisted college counseling to first-generation college students. We pair students with mentors and use AI to help them craft compelling applications.
Tags: ['Education', 'Consumer', 'AI']
Industries: ['Education']
Team size: 3
Stage: Early

Response:
{"summary": "BrightPath offers affordable college counseling for first-generation students. They combine AI-assisted application tools with human mentors to help students craft strong applications.", "one_liner": "College counseling for first-gen students", "need_tags": ["React frontend", "content writing", "social media marketing", "UX research", "graphic design"], "industry": "education", "technical_level": "mixed", "stage_detail": "building-mvp", "specific_projects": ["Design and build a student onboarding flow that collects academic background and goals", "Create social media content showcasing first-gen student success stories"]}
"""

_PROMPT_TEMPLATE = """{few_shot}

Now analyze this company:
Company: {name}
Batch: {batch}
Short description: {description}
Full description: {long_description}
Tags: {tags}
Industries: {industries}
Team size: {team_size}
Stage: {stage}

Return this exact JSON structure:
{{"summary": "2 sentences. What they build and why it matters. Plain English, no jargon.", "one_liner": "10 words max. Format: '[thing] for [audience]'", "need_tags": ["3-5 specific skills a student intern could help with. Be specific — not 'coding' but 'Python scripting' or 'React frontend'. Base this ONLY on what the descriptions tell you about the product."], "industry": "one of: {industry_list}", "technical_level": "technical | mixed | non-technical", "stage_detail": "building-mvp | launched | growing | scaling", "specific_projects": ["exactly 2 concrete tasks a student could offer to do for this company. Be specific to what this company builds — not generic. Each should be one sentence."]}}"""


def build_prompt(company: dict) -> str:
    """Build the user prompt for a single company."""
    return _PROMPT_TEMPLATE.format(
        few_shot=_FEW_SHOT_EXAMPLES,
        name=company.get("name", ""),
        batch=company.get("batch", ""),
        description=company.get("description", ""),
        long_description=company.get("long_description", ""),
        tags=company.get("tags", []),
        industries=company.get("industries", []),
        team_size=company.get("team_size", "Unknown"),
        stage=company.get("stage", ""),
        industry_list=", ".join(INDUSTRY_LIST),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/pipeline/test_enrich_config.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/enrich_config.py tests/pipeline/test_enrich_config.py
git commit -m "feat: add enrichment config with prompts, model settings, and constants"
```

---

### Task 2: Validation — Parse and Validate LLM Responses

**Files:**
- Create: `backend/pipeline/enrich.py` (validation functions only, enrichment loop comes in Task 3)
- Create: `tests/pipeline/test_enrich.py`

- [ ] **Step 1: Write tests for JSON parsing and validation**

```python
# tests/pipeline/test_enrich.py
import json
import pytest
from backend.pipeline.enrich import parse_response, validate_enrichment, auto_fix_enrichment


def test_parse_response_valid_json():
    raw = json.dumps({"summary": "Test.", "one_liner": "Test co"})
    result = parse_response(raw)
    assert result == {"summary": "Test.", "one_liner": "Test co"}


def test_parse_response_invalid_json():
    result = parse_response("not json at all")
    assert result is None


def test_parse_response_json_with_markdown_wrapper():
    raw = '```json\n{"summary": "Test."}\n```'
    result = parse_response(raw)
    assert result == {"summary": "Test."}


def test_validate_enrichment_valid():
    data = {
        "summary": "They build tools for logistics. It helps companies ship faster.",
        "one_liner": "Logistics tools for shippers",
        "need_tags": ["Python scripting", "data analysis", "web design"],
        "industry": "logistics",
        "technical_level": "mixed",
        "stage_detail": "growing",
        "specific_projects": [
            "Build a tracking dashboard for shipment status",
            "Write documentation for their API endpoints",
        ],
    }
    errors = validate_enrichment(data)
    assert errors == []


def test_validate_enrichment_missing_fields():
    data = {"summary": "Test.", "one_liner": "Test"}
    errors = validate_enrichment(data)
    assert any("need_tags" in e for e in errors)
    assert any("industry" in e for e in errors)


def test_validate_enrichment_summary_too_short():
    data = {
        "summary": "Short.",
        "one_liner": "Test co",
        "need_tags": ["Python", "React"],
        "industry": "fintech",
        "technical_level": "technical",
        "stage_detail": "launched",
        "specific_projects": ["Do task one for this company", "Do task two for them"],
    }
    errors = validate_enrichment(data)
    assert any("summary" in e for e in errors)


def test_validate_enrichment_bad_industry():
    data = {
        "summary": "They build tools for logistics. It helps companies ship faster.",
        "one_liner": "Logistics tools",
        "need_tags": ["Python", "React"],
        "industry": "invalid-industry",
        "technical_level": "technical",
        "stage_detail": "launched",
        "specific_projects": ["Do task one for this company", "Do task two for them"],
    }
    errors = validate_enrichment(data)
    assert any("industry" in e for e in errors)


def test_validate_enrichment_wrong_number_of_projects():
    data = {
        "summary": "They build tools for logistics. It helps companies ship faster.",
        "one_liner": "Logistics tools",
        "need_tags": ["Python", "React"],
        "industry": "logistics",
        "technical_level": "technical",
        "stage_detail": "launched",
        "specific_projects": ["Only one project here"],
    }
    errors = validate_enrichment(data)
    assert any("specific_projects" in e for e in errors)


def test_auto_fix_industry():
    data = {
        "summary": "They build tools for health. It helps doctors work faster.",
        "one_liner": "Health tools",
        "need_tags": ["Python", "React"],
        "industry": "health",
        "technical_level": "technical",
        "stage_detail": "launched",
        "specific_projects": ["Do task one for this company", "Do task two for them"],
    }
    fixed = auto_fix_enrichment(data)
    assert fixed["industry"] == "healthcare"


def test_auto_fix_technical_level():
    data = {
        "summary": "They build tools. It helps people.",
        "one_liner": "Tools",
        "need_tags": ["Python"],
        "industry": "fintech",
        "technical_level": "tech",
        "stage_detail": "launched",
        "specific_projects": ["Do task one", "Do task two"],
    }
    fixed = auto_fix_enrichment(data)
    assert fixed["technical_level"] == "technical"


def test_auto_fix_stage_detail():
    data = {
        "summary": "They build tools. It helps people.",
        "one_liner": "Tools",
        "need_tags": ["Python"],
        "industry": "fintech",
        "technical_level": "technical",
        "stage_detail": "mvp",
        "stage_detail": "mvp",
        "specific_projects": ["Do task one", "Do task two"],
    }
    fixed = auto_fix_enrichment(data)
    assert fixed["stage_detail"] == "building-mvp"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/pipeline/test_enrich.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement parse_response, validate_enrichment, auto_fix_enrichment**

```python
# backend/pipeline/enrich.py
"""Enrich YC companies with LLM-generated structured fields."""

import json
import re
from difflib import get_close_matches

from backend.pipeline.enrich_config import (
    INDUSTRY_LIST, VALID_TECHNICAL_LEVELS, VALID_STAGE_DETAILS,
)


def parse_response(raw: str) -> dict | None:
    """Parse LLM response as JSON. Handle markdown wrappers."""
    # Strip markdown code fences if present
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


def _closest_match(value: str, valid_list: list[str]) -> str | None:
    """Find closest match in a list using difflib."""
    matches = get_close_matches(value.lower(), valid_list, n=1, cutoff=0.5)
    return matches[0] if matches else None


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/pipeline/test_enrich.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/enrich.py tests/pipeline/test_enrich.py
git commit -m "feat: add LLM response parsing, validation, and auto-fix"
```

---

### Task 3: Enrichment Loop — Ollama Calls with Resumability

**Files:**
- Modify: `backend/pipeline/enrich.py` (add `enrich_company`, `enrich_all`)
- Modify: `tests/pipeline/test_enrich.py` (add loop tests)

- [ ] **Step 1: Write tests for single-company enrichment and the full loop**

Append to `tests/pipeline/test_enrich.py`:

```python
from unittest.mock import patch, Mock
from backend.pipeline.enrich import enrich_company, enrich_all


def _valid_response():
    return json.dumps({
        "summary": "They build tools for logistics. It helps companies ship faster.",
        "one_liner": "Logistics tools for shippers",
        "need_tags": ["Python scripting", "data analysis", "web design"],
        "industry": "logistics",
        "technical_level": "mixed",
        "stage_detail": "growing",
        "specific_projects": [
            "Build a tracking dashboard for shipment status",
            "Write documentation for their API endpoints",
        ],
    })


def _make_company(name="TestCo"):
    return {
        "name": name,
        "batch": "Winter 2024",
        "description": "AI for logistics.",
        "long_description": "We build AI tools for supply chain.",
        "tags": ["AI", "Logistics"],
        "industries": ["B2B"],
        "team_size": 5,
        "stage": "Early",
    }


def test_enrich_company_success():
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": _valid_response()}

    with patch("backend.pipeline.enrich.requests.post", return_value=mock_resp):
        result = enrich_company(_make_company())

    assert result is not None
    assert result["summary"] == "They build tools for logistics. It helps companies ship faster."
    assert result["industry"] == "logistics"
    assert len(result["need_tags"]) == 3


def test_enrich_company_retries_on_invalid_json():
    bad_resp = Mock()
    bad_resp.status_code = 200
    bad_resp.json.return_value = {"response": "not json"}

    good_resp = Mock()
    good_resp.status_code = 200
    good_resp.json.return_value = {"response": _valid_response()}

    with patch("backend.pipeline.enrich.requests.post", side_effect=[bad_resp, good_resp]):
        result = enrich_company(_make_company())

    assert result is not None
    assert result["industry"] == "logistics"


def test_enrich_company_returns_none_after_max_retries():
    bad_resp = Mock()
    bad_resp.status_code = 200
    bad_resp.json.return_value = {"response": "not json"}

    with patch("backend.pipeline.enrich.requests.post", return_value=bad_resp):
        result = enrich_company(_make_company())

    assert result is None


def test_enrich_company_auto_fixes_industry():
    response_data = {
        "summary": "They build tools for health. It helps doctors and patients.",
        "one_liner": "Health tools for doctors",
        "need_tags": ["Python scripting", "data analysis"],
        "industry": "health",
        "technical_level": "technical",
        "stage_detail": "launched",
        "specific_projects": [
            "Build a patient intake form",
            "Create a data export feature",
        ],
    }
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": json.dumps(response_data)}

    with patch("backend.pipeline.enrich.requests.post", return_value=mock_resp):
        result = enrich_company(_make_company())

    assert result is not None
    assert result["industry"] == "healthcare"


def test_enrich_all_writes_output(tmp_path):
    companies = [_make_company("Co1"), _make_company("Co2")]
    raw_path = tmp_path / "raw.json"
    raw_path.write_text(json.dumps(companies))

    output_path = tmp_path / "enriched.json"
    failures_path = tmp_path / "failures.json"

    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": _valid_response()}

    with patch("backend.pipeline.enrich.requests.post", return_value=mock_resp):
        results = enrich_all(
            raw_data_path=str(raw_path),
            output_path=str(output_path),
            failures_path=str(failures_path),
        )

    assert len(results) == 2
    assert output_path.exists()
    saved = json.loads(output_path.read_text())
    assert len(saved) == 2
    # Original fields preserved
    assert saved[0]["name"] == "Co1"
    assert saved[0]["batch"] == "Winter 2024"
    # Enriched fields added
    assert "summary" in saved[0]
    assert "need_tags" in saved[0]


def test_enrich_all_resumes_from_existing(tmp_path):
    companies = [_make_company("Co1"), _make_company("Co2"), _make_company("Co3")]
    raw_path = tmp_path / "raw.json"
    raw_path.write_text(json.dumps(companies))

    # Co1 already enriched
    existing = [{**_make_company("Co1"), "summary": "Already done.", "one_liner": "Done",
                 "need_tags": ["x"], "industry": "fintech", "technical_level": "technical",
                 "stage_detail": "launched", "specific_projects": ["a", "b"]}]
    output_path = tmp_path / "enriched.json"
    output_path.write_text(json.dumps(existing))

    failures_path = tmp_path / "failures.json"

    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": _valid_response()}

    with patch("backend.pipeline.enrich.requests.post", return_value=mock_resp) as mock_post:
        results = enrich_all(
            raw_data_path=str(raw_path),
            output_path=str(output_path),
            failures_path=str(failures_path),
        )

    assert len(results) == 3
    # Only 2 new companies should have triggered Ollama calls
    assert mock_post.call_count == 2


def test_enrich_all_logs_failures(tmp_path):
    companies = [_make_company("FailCo")]
    raw_path = tmp_path / "raw.json"
    raw_path.write_text(json.dumps(companies))

    output_path = tmp_path / "enriched.json"
    failures_path = tmp_path / "failures.json"

    bad_resp = Mock()
    bad_resp.status_code = 200
    bad_resp.json.return_value = {"response": "not json"}

    with patch("backend.pipeline.enrich.requests.post", return_value=bad_resp):
        results = enrich_all(
            raw_data_path=str(raw_path),
            output_path=str(output_path),
            failures_path=str(failures_path),
        )

    assert len(results) == 0
    assert failures_path.exists()
    failures = json.loads(failures_path.read_text())
    assert len(failures) == 1
    assert failures[0]["name"] == "FailCo"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/pipeline/test_enrich.py::test_enrich_company_success -v`
Expected: FAIL — `ImportError: cannot import name 'enrich_company'`

- [ ] **Step 3: Implement enrich_company and enrich_all**

Append to `backend/pipeline/enrich.py`:

```python
import os
import requests

from backend.pipeline.enrich_config import (
    SYSTEM_PROMPT, OLLAMA_URL, OLLAMA_MODEL,
    OLLAMA_TEMPERATURE, OLLAMA_NUM_PREDICT,
    MAX_RETRIES, SAVE_EVERY,
    RAW_DATA_PATH, ENRICHED_OUTPUT_PATH, FAILURES_OUTPUT_PATH,
    build_prompt,
)


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
        return resp.json().get("response", "")
    except Exception as e:
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

    # Load existing progress
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
        enriched = enrich_company(company)

        if enriched:
            merged = {**company, **enriched}
            results.append(merged)
        else:
            failures.append({"name": company["name"], "reason": "max retries exceeded"})

        # Save progress periodically
        if (i + 1) % SAVE_EVERY == 0:
            _save_json(results, output_path)
            print(f"[INFO] Progress saved: {len(results)} enriched, {len(failures)} failed ({i + 1}/{len(to_process)})")

    # Final save
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
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `python -m pytest tests/pipeline/test_enrich.py -v`
Expected: 17 passed

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/enrich.py tests/pipeline/test_enrich.py
git commit -m "feat: add enrichment loop with Ollama calls, resumability, and retry logic"
```

---

### Task 4: Tag Normalization — Build Skill Vocabulary

**Files:**
- Create: `backend/pipeline/normalize_tags.py`
- Create: `tests/pipeline/test_normalize_tags.py`

- [ ] **Step 1: Write tests for tag collection, dedup, and remapping**

```python
# tests/pipeline/test_normalize_tags.py
import json
from backend.pipeline.normalize_tags import (
    collect_raw_tags,
    deduplicate_tags,
    remap_company_tags,
)


def test_collect_raw_tags():
    companies = [
        {"name": "A", "need_tags": ["Python scripting", "React frontend"]},
        {"name": "B", "need_tags": ["python scripting", "data analysis"]},
        {"name": "C", "need_tags": ["React frontend", "content writing"]},
    ]
    tags = collect_raw_tags(companies)
    assert "Python scripting" in tags
    assert "React frontend" in tags
    assert "data analysis" in tags
    assert "content writing" in tags
    assert len(tags) == 6  # includes duplicates


def test_deduplicate_tags_merges_case_variants():
    raw_tags = [
        "Python scripting", "python scripting", "Python Scripting",
        "React frontend", "react frontend",
        "data analysis",
    ]
    canonical = deduplicate_tags(raw_tags)
    # Should have 3 unique skills
    assert len(canonical) == 3
    # Each canonical tag should be lowercase
    for tag in canonical:
        assert tag == tag.lower()


def test_deduplicate_tags_merges_close_matches():
    raw_tags = [
        "frontend development", "front-end development", "frontend dev",
        "data analysis", "data analytics",
        "graphic design",
    ]
    canonical = deduplicate_tags(raw_tags)
    # "frontend development", "front-end development", "frontend dev" should merge
    # "data analysis" and "data analytics" should merge
    # "graphic design" stays
    assert len(canonical) <= 3


def test_remap_company_tags():
    company = {
        "name": "TestCo",
        "need_tags": ["Python Scripting", "react Frontend", "Data Analysis"],
    }
    tag_mapping = {
        "python scripting": "python scripting",
        "python Scripting": "python scripting",
        "react frontend": "react frontend",
        "react Frontend": "react frontend",
        "data analysis": "data analysis",
        "Data Analysis": "data analysis",
    }
    remapped = remap_company_tags(company, tag_mapping)
    assert remapped["need_tags"] == ["python scripting", "react frontend", "data analysis"]
    # Original fields preserved
    assert remapped["name"] == "TestCo"


def test_remap_company_tags_unknown_tag_kept():
    company = {
        "name": "TestCo",
        "need_tags": ["unknown skill xyz"],
    }
    tag_mapping = {}
    remapped = remap_company_tags(company, tag_mapping)
    assert remapped["need_tags"] == ["unknown skill xyz"]


def test_normalize_all_writes_files(tmp_path):
    from backend.pipeline.normalize_tags import normalize_all

    companies = [
        {**_base_company("A"), "need_tags": ["Python scripting", "React frontend"]},
        {**_base_company("B"), "need_tags": ["python scripting", "data analysis"]},
    ]
    enriched_path = tmp_path / "enriched.json"
    enriched_path.write_text(json.dumps(companies))

    vocab_path = tmp_path / "vocab.json"

    normalize_all(
        enriched_path=str(enriched_path),
        vocab_output_path=str(vocab_path),
    )

    assert vocab_path.exists()
    vocab = json.loads(vocab_path.read_text())
    assert isinstance(vocab, list)
    assert len(vocab) > 0

    # Enriched file should be updated with remapped tags
    updated = json.loads(enriched_path.read_text())
    for company in updated:
        for tag in company["need_tags"]:
            assert tag == tag.lower()


def _base_company(name):
    return {
        "name": name,
        "batch": "Winter 2024",
        "description": "Test.",
        "summary": "Test summary. More info.",
        "one_liner": "Test co",
        "industry": "fintech",
        "technical_level": "technical",
        "stage_detail": "launched",
        "specific_projects": ["Task one", "Task two"],
    }
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/pipeline/test_normalize_tags.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement normalize_tags.py**

```python
# backend/pipeline/normalize_tags.py
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
    # First pass: case-normalize and count
    normalized_counts = Counter(tag.lower().strip() for tag in raw_tags)
    unique_tags = sorted(normalized_counts.keys(), key=lambda t: -normalized_counts[t])

    # Second pass: merge similar tags (keep the more frequent one)
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
        # Exact match first
        if lower in canonical:
            mapping[raw] = lower
            continue
        # Fuzzy match
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
            mapping[raw] = lower  # Keep as-is, lowercased
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

    # Remap all companies
    remapped = [remap_company_tags(c, tag_mapping) for c in companies]

    # Save vocab
    os.makedirs(os.path.dirname(os.path.abspath(vocab_output_path)), exist_ok=True)
    with open(vocab_output_path, "w") as f:
        json.dump(canonical, f, indent=2)

    # Overwrite enriched file with remapped tags
    with open(enriched_path, "w") as f:
        json.dump(remapped, f, indent=2)

    print(f"[DONE] Saved {len(canonical)} skills to {vocab_output_path}")
    print(f"[DONE] Updated {len(remapped)} companies in {enriched_path}")


if __name__ == "__main__":
    normalize_all()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/pipeline/test_normalize_tags.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/normalize_tags.py tests/pipeline/test_normalize_tags.py
git commit -m "feat: add tag normalization — dedup, fuzzy matching, skill vocabulary generation"
```

---

### Task 5: Integration Test — End-to-End with Mocked Ollama

**Files:**
- Modify: `tests/pipeline/test_enrich.py` (add integration test)

- [ ] **Step 1: Write end-to-end integration test**

Append to `tests/pipeline/test_enrich.py`:

```python
from backend.pipeline.normalize_tags import normalize_all


def test_full_pipeline_enrich_then_normalize(tmp_path):
    """End-to-end: enrich 3 companies, then normalize tags."""
    companies = [
        _make_company("AlphaCo"),
        _make_company("BetaCo"),
        _make_company("GammaCo"),
    ]
    raw_path = tmp_path / "raw.json"
    raw_path.write_text(json.dumps(companies))

    enriched_path = tmp_path / "enriched.json"
    failures_path = tmp_path / "failures.json"
    vocab_path = tmp_path / "vocab.json"

    # Each company gets slightly different tags to test normalization
    responses = [
        json.dumps({
            "summary": "Alpha builds logistics tools. They optimize shipping routes.",
            "one_liner": "Logistics optimization platform",
            "need_tags": ["Python scripting", "data visualization", "React frontend"],
            "industry": "logistics",
            "technical_level": "technical",
            "stage_detail": "growing",
            "specific_projects": [
                "Build a route optimization dashboard",
                "Create API documentation for shipping endpoints",
            ],
        }),
        json.dumps({
            "summary": "Beta builds logistics tools. They track shipments in real time.",
            "one_liner": "Real-time shipment tracking",
            "need_tags": ["python scripting", "Data Visualization", "mobile development"],
            "industry": "logistics",
            "technical_level": "technical",
            "stage_detail": "launched",
            "specific_projects": [
                "Build a mobile tracking interface",
                "Set up real-time notification system",
            ],
        }),
        json.dumps({
            "summary": "Gamma helps restaurants manage orders. They reduce food waste.",
            "one_liner": "Restaurant order management",
            "need_tags": ["graphic design", "content writing", "social media marketing"],
            "industry": "consumer",
            "technical_level": "mixed",
            "stage_detail": "building-mvp",
            "specific_projects": [
                "Design menu display templates for partner restaurants",
                "Write blog posts about food waste reduction strategies",
            ],
        }),
    ]

    call_count = 0

    def mock_post(*args, **kwargs):
        nonlocal call_count
        resp = Mock()
        resp.status_code = 200
        resp.json.return_value = {"response": responses[call_count]}
        resp.raise_for_status = Mock()
        call_count += 1
        return resp

    with patch("backend.pipeline.enrich.requests.post", side_effect=mock_post):
        enrich_all(
            raw_data_path=str(raw_path),
            output_path=str(enriched_path),
            failures_path=str(failures_path),
        )

    # Verify enrichment
    enriched = json.loads(enriched_path.read_text())
    assert len(enriched) == 3
    assert all("summary" in c for c in enriched)
    assert all("need_tags" in c for c in enriched)

    # Now normalize
    normalize_all(
        enriched_path=str(enriched_path),
        vocab_output_path=str(vocab_path),
    )

    # Verify normalization
    vocab = json.loads(vocab_path.read_text())
    assert isinstance(vocab, list)

    # "Python scripting" and "python scripting" should have merged
    python_variants = [v for v in vocab if "python" in v]
    assert len(python_variants) == 1

    # "data visualization" and "Data Visualization" should have merged
    dataviz_variants = [v for v in vocab if "data vis" in v]
    assert len(dataviz_variants) == 1

    # Updated enriched file should have lowercase tags
    updated = json.loads(enriched_path.read_text())
    for company in updated:
        for tag in company["need_tags"]:
            assert tag == tag.lower(), f"Tag not lowercase: {tag}"
```

- [ ] **Step 2: Run the integration test**

Run: `python -m pytest tests/pipeline/test_enrich.py::test_full_pipeline_enrich_then_normalize -v`
Expected: PASS

- [ ] **Step 3: Run the full test suite to check nothing is broken**

Run: `python -m pytest tests/ -v`
Expected: All tests pass (existing 26 ML tests + new enrichment tests)

- [ ] **Step 4: Commit**

```bash
git add tests/pipeline/test_enrich.py
git commit -m "test: add end-to-end integration test for enrich + normalize pipeline"
```

---

### Task 6: Update Requirements and Add __main__ Runner

**Files:**
- Modify: `requirements.txt` (no new deps needed — `requests` and `difflib` already available)
- Verify: `backend/pipeline/__init__.py` exists

- [ ] **Step 1: Verify imports work cleanly**

Run: `python -c "from backend.pipeline.enrich import enrich_all; from backend.pipeline.normalize_tags import normalize_all; print('OK')"`
Expected: `OK`

- [ ] **Step 2: Run full test suite one final time**

Run: `python -m pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 3: Commit any remaining changes**

```bash
git add -A
git commit -m "chore: verify enrichment pipeline imports and full test suite"
```

---

## Running the Pipeline

After implementation, the actual enrichment run:

```bash
# 1. Start Ollama (if not already running)
ollama serve

# 2. Run enrichment (~90 minutes)
python -m backend.pipeline.enrich

# 3. Run tag normalization (~1 minute)
python -m backend.pipeline.normalize_tags

# 4. Check results
python -c "import json; d=json.load(open('data/enriched_companies.json')); print(f'{len(d)} enriched')"
python -c "import json; d=json.load(open('data/skill_vocabulary.json')); print(f'{len(d)} skills')"
```

If enrichment crashes partway through, just re-run step 2 — it resumes from where it left off.
