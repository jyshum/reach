"""Tests for outreach guidance rules engine."""

from backend.schemas import Guidance, CompanyBrief


def test_guidance_model_fields():
    g = Guidance(
        your_angle="Lead with Python",
        reference_this="Their enzyme platform",
        dont_say="Don't say you're passionate",
        your_ask="Offer to build a dashboard",
    )
    assert g.your_angle == "Lead with Python"
    assert g.reference_this == "Their enzyme platform"
    assert g.dont_say == "Don't say you're passionate"
    assert g.your_ask == "Offer to build a dashboard"


def test_company_brief_has_guidance_field():
    brief = CompanyBrief(id=1, name="Test")
    assert brief.guidance is None


from backend.guidance.rules import classify_skill_type


def test_classify_developer():
    assert classify_skill_type(["Python scripting", "API integration", "React frontend"]) == "developer"


def test_classify_designer():
    assert classify_skill_type(["UI/UX design", "Figma", "graphic design"]) == "designer"


def test_classify_data():
    assert classify_skill_type(["data analysis", "data visualization", "machine learning"]) == "data"


def test_classify_writer():
    assert classify_skill_type(["content writing", "scientific writing", "copywriting"]) == "writer"


def test_classify_business():
    assert classify_skill_type(["marketing", "social media marketing", "market research"]) == "business"


def test_classify_operations():
    assert classify_skill_type(["project management", "customer support", "QA testing"]) == "operations"


def test_classify_tie_breaks_by_company_tags():
    # Equal developer and data skills — company needs data, so data wins
    skills = ["Python scripting", "data analysis"]
    company_tags = ["data visualization", "data analysis"]
    assert classify_skill_type(skills, company_tags) == "data"


def test_classify_empty_skills():
    assert classify_skill_type([]) is None


def test_classify_unknown_skills_returns_none():
    assert classify_skill_type(["underwater basket weaving"]) is None


from backend.guidance.rules import map_industry_cluster


def test_map_software_industries():
    assert map_industry_cluster("enterprise-saas") == "software"
    assert map_industry_cluster("developer-tools") == "software"


def test_map_ai_ml():
    assert map_industry_cluster("ai-ml") == "ai-ml"


def test_map_fintech():
    assert map_industry_cluster("fintech") == "fintech"


def test_map_health_bio():
    assert map_industry_cluster("healthcare") == "health-bio"
    assert map_industry_cluster("biotech") == "health-bio"


def test_map_commerce():
    assert map_industry_cluster("e-commerce") == "commerce"
    assert map_industry_cluster("consumer") == "commerce"


def test_map_infrastructure():
    assert map_industry_cluster("security") == "infrastructure"


def test_map_impact():
    assert map_industry_cluster("climate") == "impact"
    assert map_industry_cluster("education") == "impact"
    assert map_industry_cluster("social-impact") == "impact"


def test_map_unmapped_to_general():
    assert map_industry_cluster("real-estate") == "general"
    assert map_industry_cluster("gaming") == "general"
    assert map_industry_cluster("totally-unknown") == "general"


from backend.guidance.rules import select_specific_project, fill_slots


def test_select_project_matches_developer():
    projects = [
        "Build a dashboard to visualize screening results",
        "Write case studies explaining cost reduction",
    ]
    assert select_specific_project(projects, "developer") == projects[0]


def test_select_project_matches_writer():
    projects = [
        "Build a dashboard to visualize screening results",
        "Write case studies explaining cost reduction",
    ]
    assert select_specific_project(projects, "writer") == projects[1]


def test_select_project_defaults_to_first():
    projects = [
        "Analyze enzyme screening data",
        "Create technical documentation",
    ]
    # "business" has no strong keyword match — defaults to first
    assert select_specific_project(projects, "business") == projects[0]


def test_select_project_empty_list():
    assert select_specific_project([], "developer") is None


def test_fill_slots_replaces_all_placeholders():
    template = "Lead with {matched_skill} — offer to {specific_project} for {company_name}."
    result = fill_slots(template, {
        "matched_skill": "Python scripting",
        "specific_project": "build a dashboard",
        "company_name": "Pando",
    })
    assert result == "Lead with Python scripting — offer to build a dashboard for Pando."
    assert "{" not in result


def test_fill_slots_missing_value_uses_generic():
    template = "Reference {company_name}'s work on {specific_project}."
    result = fill_slots(template, {
        "company_name": "Pando",
        "specific_project": None,
    })
    assert "Pando" in result
    assert "{" not in result


from backend.guidance.rules import generate_guidance


def _sample_company():
    return {
        "name": "Pando Bioscience",
        "summary": "Pando uses AI to design custom enzymes for pharmaceutical companies. Their platform tests thousands of enzyme variants.",
        "description": "Gen-AI Designed Enzymes for Pharmaceutical Innovation",
        "industry": "biotech",
        "stage_detail": "growing",
        "technical_level": "technical",
        "need_tags": ["Python scripting", "data visualization", "scientific writing"],
        "specific_projects": [
            "Analyze enzyme screening data to identify patterns",
            "Create technical documentation for the platform",
        ],
    }


def test_generate_guidance_developer_biotech_growing():
    company = _sample_company()
    user_skills = ["Python scripting", "data visualization"]
    result = generate_guidance(user_skills, company)

    assert isinstance(result, Guidance)
    assert len(result.your_angle) > 0
    assert len(result.reference_this) > 0
    assert len(result.dont_say) > 0
    assert len(result.your_ask) > 0
    # No unfilled placeholders
    assert "{" not in result.your_angle
    assert "{" not in result.reference_this
    assert "{" not in result.dont_say
    assert "{" not in result.your_ask


def test_generate_guidance_writer_commerce_mvp():
    company = {
        "name": "ShopFlow",
        "summary": "ShopFlow helps small retailers build online stores. Their drag-and-drop builder requires no coding.",
        "description": "E-commerce builder for small retailers",
        "industry": "e-commerce",
        "stage_detail": "building-mvp",
        "technical_level": "non-technical",
        "need_tags": ["content writing", "social media marketing", "graphic design"],
        "specific_projects": [
            "Write launch blog posts for the product announcement",
            "Design social media templates for retailer success stories",
        ],
    }
    user_skills = ["content writing", "blog writing"]
    result = generate_guidance(user_skills, company)

    assert isinstance(result, Guidance)
    assert "{" not in result.your_angle
    assert "{" not in result.reference_this


def test_generate_guidance_no_skills_returns_none():
    company = _sample_company()
    result = generate_guidance([], company)
    assert result is None


def test_generate_guidance_no_need_tags():
    company = _sample_company()
    company["need_tags"] = []
    user_skills = ["Python scripting"]
    result = generate_guidance(user_skills, company)

    # Still generates guidance from stage + industry layers
    assert isinstance(result, Guidance)
    assert len(result.your_angle) > 0


def test_generate_guidance_no_specific_projects():
    company = _sample_company()
    company["specific_projects"] = []
    user_skills = ["Python scripting"]
    result = generate_guidance(user_skills, company)

    assert isinstance(result, Guidance)
    # Falls back to generic — no unfilled placeholders
    assert "{" not in result.your_angle
    assert "{" not in result.your_ask


def test_generate_guidance_no_summary_uses_description():
    company = _sample_company()
    company["summary"] = None
    user_skills = ["Python scripting"]
    result = generate_guidance(user_skills, company)

    assert isinstance(result, Guidance)
    assert "{" not in result.reference_this
