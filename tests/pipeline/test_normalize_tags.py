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
    assert len(tags) == 6


def test_deduplicate_tags_merges_case_variants():
    raw_tags = [
        "Python scripting", "python scripting", "Python Scripting",
        "React frontend", "react frontend",
        "data analysis",
    ]
    canonical = deduplicate_tags(raw_tags)
    assert len(canonical) == 3
    for tag in canonical:
        assert tag == tag.lower()


def test_deduplicate_tags_merges_close_matches():
    raw_tags = [
        "frontend development", "front-end development", "frontend dev",
        "data analysis", "data analytics",
        "graphic design",
    ]
    canonical = deduplicate_tags(raw_tags)
    assert len(canonical) <= 3


def test_remap_company_tags():
    company = {
        "name": "TestCo",
        "need_tags": ["Python Scripting", "react Frontend", "Data Analysis"],
    }
    tag_mapping = {
        "Python Scripting": "python scripting",
        "react Frontend": "react frontend",
        "Data Analysis": "data analysis",
    }
    remapped = remap_company_tags(company, tag_mapping)
    assert remapped["need_tags"] == ["python scripting", "react frontend", "data analysis"]
    assert remapped["name"] == "TestCo"


def test_remap_company_tags_unknown_tag_kept():
    company = {
        "name": "TestCo",
        "need_tags": ["unknown skill xyz"],
    }
    tag_mapping = {}
    remapped = remap_company_tags(company, tag_mapping)
    assert remapped["need_tags"] == ["unknown skill xyz"]


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

    updated = json.loads(enriched_path.read_text())
    for company in updated:
        for tag in company["need_tags"]:
            assert tag == tag.lower()
