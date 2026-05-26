from backend.email.prompt import build_email_prompt


def test_build_prompt_contains_student_info():
    result = build_email_prompt(
        student_bio="HS junior interested in ML, built a sentiment analysis project",
        student_capabilities=["deep-learning", "data-pipelines"],
        company_name="Pando Bioscience",
        company_summary="Pando uses AI to design custom enzymes for pharma",
        specific_projects=["Analyze enzyme screening data", "Create technical docs"],
        founder_name="Alex Chen",
        guidance_angle="Lead with your ML project experience",
    )
    assert "sentiment analysis" in result
    assert "Pando Bioscience" in result
    assert "Alex Chen" in result
    assert "enzyme" in result.lower()


def test_build_prompt_with_missing_optionals():
    result = build_email_prompt(
        student_bio="CS student",
        student_capabilities=["frontend-development"],
        company_name="Acme Corp",
        company_summary="Building dev tools",
        specific_projects=[],
        founder_name="Jane Doe",
        guidance_angle=None,
    )
    assert "Acme Corp" in result
    assert "Jane Doe" in result


def test_prompt_enforces_constraints():
    result = build_email_prompt(
        student_bio="Student",
        student_capabilities=["backend-apis"],
        company_name="Test Co",
        company_summary="Test summary",
        specific_projects=["Build an API"],
        founder_name="Sam",
        guidance_angle="Lead with API experience",
    )
    # Prompt should instruct short, student-voice email
    assert "4-5 sentences" in result or "short" in result.lower()
    assert "student" in result.lower()
