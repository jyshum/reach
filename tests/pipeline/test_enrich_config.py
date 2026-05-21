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
    assert len(INDUSTRY_LIST) == 30
