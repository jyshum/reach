import json
import pytest
from unittest.mock import patch, Mock
from backend.pipeline.enrich import parse_response, validate_enrichment, auto_fix_enrichment, enrich_company, enrich_all
from backend.pipeline.normalize_tags import normalize_all


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
        "specific_projects": ["Do task one", "Do task two"],
    }
    fixed = auto_fix_enrichment(data)
    assert fixed["stage_detail"] == "building-mvp"


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
    assert saved[0]["name"] == "Co1"
    assert saved[0]["batch"] == "Winter 2024"
    assert "summary" in saved[0]
    assert "need_tags" in saved[0]


def test_enrich_all_resumes_from_existing(tmp_path):
    companies = [_make_company("Co1"), _make_company("Co2"), _make_company("Co3")]
    raw_path = tmp_path / "raw.json"
    raw_path.write_text(json.dumps(companies))

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

    enriched = json.loads(enriched_path.read_text())
    assert len(enriched) == 3
    assert all("summary" in c for c in enriched)
    assert all("need_tags" in c for c in enriched)

    normalize_all(
        enriched_path=str(enriched_path),
        vocab_output_path=str(vocab_path),
    )

    vocab = json.loads(vocab_path.read_text())
    assert isinstance(vocab, list)

    python_variants = [v for v in vocab if "python" in v]
    assert len(python_variants) == 1

    dataviz_variants = [v for v in vocab if "data vis" in v]
    assert len(dataviz_variants) == 1

    updated = json.loads(enriched_path.read_text())
    for company in updated:
        for tag in company["need_tags"]:
            assert tag == tag.lower(), f"Tag not lowercase: {tag}"
