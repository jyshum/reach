# Outreach Guidance Rules Engine — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a composable, rule-based outreach guidance system that generates personalized advice (your_angle, reference_this, dont_say, your_ask) on each company brief, assembled from skill-type × stage × industry-cluster rule layers with template slot-filling.

**Architecture:** One new file `backend/guidance/rules.py` contains all rule dicts, classifiers, and the `generate_guidance()` function. The `Guidance` schema is added to `schemas.py` and wired into the existing `CompanyBrief` response via `routers/companies.py`. No new endpoints, DB tables, or external calls.

**Tech Stack:** Python, Pydantic, FastAPI, pytest

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Create | `backend/guidance/__init__.py` | Package marker |
| Create | `backend/guidance/rules.py` | Skill-type classifier, industry mapper, rule dicts, slot filler, `generate_guidance()` |
| Modify | `backend/schemas.py:50-75` | Add `Guidance` model, add `guidance` field to `CompanyBrief` |
| Modify | `backend/routers/companies.py:50-88` | Call `generate_guidance()` in brief endpoint |
| Create | `tests/guidance/__init__.py` | Package marker |
| Create | `tests/guidance/test_rules.py` | Unit + integration tests |

---

### Task 1: Add Guidance Schema

**Files:**
- Modify: `backend/schemas.py:50-75`

- [ ] **Step 1: Write the failing test**

Create `tests/guidance/__init__.py` (empty) and `tests/guidance/test_rules.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/guidance/test_rules.py::test_guidance_model_fields tests/guidance/test_rules.py::test_company_brief_has_guidance_field -v`
Expected: FAIL — `Guidance` not importable, `CompanyBrief` has no `guidance` field

- [ ] **Step 3: Add Guidance model and update CompanyBrief**

In `backend/schemas.py`, add after the `UserUpdate` class (before `# --- Companies ---`):

```python
# --- Guidance ---

class Guidance(BaseModel):
    your_angle: str
    reference_this: str
    dont_say: str
    your_ask: str
```

Add to the `CompanyBrief` class, after the `match_score` field:

```python
    guidance: Guidance | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/guidance/test_rules.py::test_guidance_model_fields tests/guidance/test_rules.py::test_company_brief_has_guidance_field -v`
Expected: PASS

- [ ] **Step 5: Run all existing tests to check nothing broke**

Run: `pytest tests/ -v`
Expected: All existing tests still pass

- [ ] **Step 6: Commit**

```bash
git add backend/schemas.py tests/guidance/__init__.py tests/guidance/test_rules.py
git commit -m "feat: add Guidance schema and guidance field to CompanyBrief"
```

---

### Task 2: Skill-Type Classifier

**Files:**
- Create: `backend/guidance/__init__.py`
- Create: `backend/guidance/rules.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/guidance/test_rules.py`:

```python
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


def test_classify_unknown_skills_returns_first_bucket():
    # Skills that don't match any bucket keyword — falls back to most common bucket
    assert classify_skill_type(["underwater basket weaving"]) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/guidance/test_rules.py::test_classify_developer -v`
Expected: FAIL — `rules` module not found

- [ ] **Step 3: Implement skill-type classifier**

Create `backend/guidance/__init__.py` (empty file).

Create `backend/guidance/rules.py`:

```python
"""Composable outreach guidance rules engine.

Generates personalized guidance by combining three rule layers:
skill-type, stage, and industry cluster. Templates use slot-filling
from enriched company data.
"""

# --- Skill-Type Classification ---

SKILL_TYPE_KEYWORDS = {
    "developer": [
        "python", "javascript", "react", "frontend", "backend", "api",
        "mobile", "ios", "android", "coding", "programming", "software",
        "web development", "full-stack", "node", "typescript", "django",
        "flask", "database", "sql", "devops", "cloud", "aws",
    ],
    "designer": [
        "design", "figma", "ui", "ux", "graphic", "illustration",
        "branding", "prototyping", "wireframe", "adobe", "sketch",
        "visual", "layout", "typography",
    ],
    "data": [
        "data analysis", "data visualization", "machine learning",
        "statistics", "analytics", "modeling", "tableau", "excel",
        "data science", "deep learning", "ai model", "neural",
        "data engineering", "etl", "data pipeline",
    ],
    "writer": [
        "writing", "content", "copywriting", "blog", "technical writing",
        "scientific writing", "documentation", "editing", "journalism",
        "storytelling", "communications",
    ],
    "business": [
        "marketing", "sales", "social media", "market research",
        "business development", "strategy", "growth", "seo",
        "advertising", "partnerships", "outreach", "fundraising",
        "investor", "pitch",
    ],
    "operations": [
        "project management", "customer support", "operations",
        "qa", "testing", "logistics", "recruiting", "hr",
        "administrative", "coordination", "process",
    ],
}


def classify_skill_type(
    user_skills: list[str],
    company_tags: list[str] | None = None,
) -> str | None:
    """Classify a user's skills into one of 6 skill-type buckets.

    Returns None if skills list is empty or no keywords match.
    Ties are broken by overlap with company_tags if provided.
    """
    if not user_skills:
        return None

    scores: dict[str, int] = {}
    for bucket, keywords in SKILL_TYPE_KEYWORDS.items():
        count = 0
        for skill in user_skills:
            skill_lower = skill.lower()
            if any(kw in skill_lower for kw in keywords):
                count += 1
        if count > 0:
            scores[bucket] = count

    if not scores:
        return None

    max_score = max(scores.values())
    top_buckets = [b for b, s in scores.items() if s == max_score]

    if len(top_buckets) == 1:
        return top_buckets[0]

    # Tie-break: which bucket has more keyword overlap with company tags
    if company_tags:
        best_bucket = None
        best_overlap = -1
        for bucket in top_buckets:
            keywords = SKILL_TYPE_KEYWORDS[bucket]
            overlap = sum(
                1 for tag in company_tags
                if any(kw in tag.lower() for kw in keywords)
            )
            if overlap > best_overlap:
                best_overlap = overlap
                best_bucket = bucket
        if best_bucket:
            return best_bucket

    # If still tied, return first alphabetically for determinism
    return sorted(top_buckets)[0]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/guidance/test_rules.py -k "classify" -v`
Expected: All 9 classify tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/guidance/__init__.py backend/guidance/rules.py tests/guidance/test_rules.py
git commit -m "feat: add skill-type classifier with 6 buckets and tie-breaking"
```

---

### Task 3: Industry Cluster Mapper

**Files:**
- Modify: `backend/guidance/rules.py`
- Modify: `tests/guidance/test_rules.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/guidance/test_rules.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/guidance/test_rules.py -k "map_" -v`
Expected: FAIL — `map_industry_cluster` not importable

- [ ] **Step 3: Implement industry cluster mapper**

Add to `backend/guidance/rules.py`:

```python
# --- Industry Cluster Mapping ---

INDUSTRY_CLUSTER_MAP = {
    # software
    "enterprise-saas": "software",
    "developer-tools": "software",
    # ai-ml
    "ai-ml": "ai-ml",
    # fintech
    "fintech": "fintech",
    # health-bio
    "healthcare": "health-bio",
    "biotech": "health-bio",
    # commerce
    "e-commerce": "commerce",
    "consumer": "commerce",
    # infrastructure
    "security": "infrastructure",
    "hardware": "infrastructure",
    # impact
    "climate": "impact",
    "education": "impact",
    "government": "impact",
    "social-impact": "impact",
}


def map_industry_cluster(industry: str) -> str:
    """Map an enrichment industry to one of 8 broader clusters.

    Returns 'general' for any unmapped industry.
    """
    return INDUSTRY_CLUSTER_MAP.get(industry, "general")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/guidance/test_rules.py -k "map_" -v`
Expected: All 8 map tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/guidance/rules.py tests/guidance/test_rules.py
git commit -m "feat: add industry cluster mapper — 30 industries to 8 clusters"
```

---

### Task 4: Rule Dictionaries and Slot Filler

**Files:**
- Modify: `backend/guidance/rules.py`
- Modify: `tests/guidance/test_rules.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/guidance/test_rules.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/guidance/test_rules.py -k "select_project or fill_slots" -v`
Expected: FAIL — functions not importable

- [ ] **Step 3: Implement project selector and slot filler**

Add to `backend/guidance/rules.py`:

```python
# --- Specific Project Selection ---

PROJECT_SKILL_KEYWORDS = {
    "developer": ["build", "implement", "code", "develop", "integrate", "api", "app", "tool", "platform", "automate", "script", "dashboard"],
    "designer": ["design", "prototype", "wireframe", "ui", "ux", "layout", "visual", "brand", "mockup", "interface"],
    "data": ["analyze", "data", "visualization", "model", "metrics", "analytics", "dashboard", "track", "measure", "statistics"],
    "writer": ["write", "document", "content", "blog", "case study", "copy", "article", "story", "communication", "guide"],
    "business": ["research", "market", "strategy", "outreach", "campaign", "growth", "sales", "partner", "competitive", "pricing"],
    "operations": ["organize", "process", "manage", "coordinate", "test", "qa", "support", "onboard", "workflow", "schedule"],
}


def select_specific_project(
    projects: list[str],
    skill_type: str,
) -> str | None:
    """Pick the specific_project most relevant to the student's skill-type.

    Returns the project with the most keyword matches for the skill-type.
    Defaults to the first project if no clear match or tie.
    Returns None if projects list is empty.
    """
    if not projects:
        return None

    keywords = PROJECT_SKILL_KEYWORDS.get(skill_type, [])
    if not keywords:
        return projects[0]

    best_project = projects[0]
    best_count = 0
    for project in projects:
        project_lower = project.lower()
        count = sum(1 for kw in keywords if kw in project_lower)
        if count > best_count:
            best_count = count
            best_project = project

    return best_project


# --- Slot Filling ---

GENERIC_FALLBACKS = {
    "matched_skill": "your strongest relevant skill",
    "specific_project": "a concrete deliverable they need",
    "company_name": "the company",
    "summary_snippet": "what they're building",
}


def fill_slots(template: str, values: dict[str, str | None]) -> str:
    """Fill {placeholder} slots in a template string.

    Missing or None values are replaced with generic fallbacks.
    """
    result = template
    for key, value in values.items():
        placeholder = "{" + key + "}"
        if value:
            result = result.replace(placeholder, value)
        else:
            fallback = GENERIC_FALLBACKS.get(key, "this")
            result = result.replace(placeholder, fallback)
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/guidance/test_rules.py -k "select_project or fill_slots" -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/guidance/rules.py tests/guidance/test_rules.py
git commit -m "feat: add project selector and slot filler for guidance templates"
```

---

### Task 5: Rule Dictionaries and generate_guidance()

**Files:**
- Modify: `backend/guidance/rules.py`
- Modify: `tests/guidance/test_rules.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/guidance/test_rules.py`:

```python
from backend.guidance.rules import generate_guidance
from backend.schemas import Guidance


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/guidance/test_rules.py -k "generate_guidance" -v`
Expected: FAIL — `generate_guidance` not importable

- [ ] **Step 3: Implement rule dictionaries and generate_guidance**

Add to `backend/guidance/rules.py`:

```python
from backend.schemas import Guidance

# --- Rule Dictionaries ---

SKILL_TYPE_RULES = {
    "developer": {
        "your_angle": "Lead with something you've built — mention a {matched_skill} project and connect it to {specific_project}.",
    },
    "designer": {
        "your_angle": "Lead with your design eye — show how you'd approach {specific_project} visually, reference a design you've shipped.",
    },
    "data": {
        "your_angle": "Lead with an insight — mention a {matched_skill} project where you found something surprising in the data, and connect it to {specific_project}.",
    },
    "writer": {
        "your_angle": "Lead with your voice — reference a piece you've written and explain how you'd approach {specific_project} for {company_name}.",
    },
    "business": {
        "your_angle": "Lead with a specific observation about their market — show you've done {matched_skill} work and connect it to {specific_project}.",
    },
    "operations": {
        "your_angle": "Lead with how you make things run — describe a time you improved a process, and connect it to {specific_project}.",
    },
}

STAGE_RULES = {
    "building-mvp": {
        "dont_say": "Don't say 'I love your vision' — they're still figuring it out. Show you understand the problem, not the pitch.",
        "your_ask": "Offer to build something small and concrete this week: '{specific_project}' — MVPs need hands, not advisors.",
    },
    "launched": {
        "dont_say": "Don't say 'I want to learn from you' — they need doers, not students. Show what you'd contribute.",
        "your_ask": "Offer a specific deliverable with a deadline: 'I could do {specific_project} and send you a draft by Friday.'",
    },
    "growing": {
        "dont_say": "Don't say 'I'm passionate about {company_name}' — every student says this. Show you understand their actual problem.",
        "your_ask": "Offer to own {specific_project} end-to-end — growing teams need people who can run with a task independently.",
    },
    "scaling": {
        "dont_say": "Don't say 'I'd love an internship' — they're past informal roles. Frame it as a specific project engagement.",
        "your_ask": "Propose a defined project: 'I'll spend 2 weeks on {specific_project} and deliver a working result.'",
    },
}

INDUSTRY_RULES = {
    "software": {
        "reference_this": "Mention {company_name}'s specific product — {summary_snippet}. Reference a feature or user problem, not just the category.",
    },
    "ai-ml": {
        "reference_this": "Mention {company_name}'s AI approach — {summary_snippet}. Show you understand the technical challenge, not just 'they use AI.'",
    },
    "fintech": {
        "reference_this": "Mention the specific financial problem {company_name} solves — {summary_snippet}. Founders know students don't have finance backgrounds; show you get the user pain.",
    },
    "health-bio": {
        "reference_this": "Mention {company_name}'s specific domain — {summary_snippet}. You don't need to know the science; show you understand who they help and why it matters.",
    },
    "commerce": {
        "reference_this": "Mention {company_name}'s target customer — {summary_snippet}. Show you understand who buys and why, not just what the product does.",
    },
    "infrastructure": {
        "reference_this": "Mention the technical problem {company_name} solves — {summary_snippet}. Infrastructure founders appreciate when you reference the hard part.",
    },
    "impact": {
        "reference_this": "Mention the real-world outcome {company_name} drives — {summary_snippet}. Impact founders want people who care about the mission and can execute.",
    },
    "general": {
        "reference_this": "Mention something specific about {company_name} — {summary_snippet}. Generic praise is invisible; one real detail shows you did your homework.",
    },
}


# --- Guidance Generator ---

def generate_guidance(
    user_skills: list[str],
    company: dict,
) -> Guidance | None:
    """Generate personalized outreach guidance from composable rule layers.

    Returns None if user has no skills. Assembles guidance from skill-type,
    stage, and industry cluster rules with slot-filling from company data.
    """
    if not user_skills:
        return None

    # Classify and map
    company_tags = company.get("need_tags") or []
    skill_type = classify_skill_type(user_skills, company_tags)
    if skill_type is None:
        skill_type = "developer"  # safe fallback for unrecognized skills

    industry = company.get("industry") or ""
    cluster = map_industry_cluster(industry)
    stage = company.get("stage_detail") or "launched"

    # Find the best matched skill (first user skill that overlaps with company tags)
    matched_skill = None
    if company_tags:
        user_skills_lower = {s.lower(): s for s in user_skills}
        for tag in company_tags:
            if tag.lower() in user_skills_lower:
                matched_skill = user_skills_lower[tag.lower()]
                break
    if not matched_skill:
        matched_skill = user_skills[0]

    # Select the most relevant specific project
    projects = company.get("specific_projects") or []
    specific_project = select_specific_project(projects, skill_type)

    # Build summary snippet (first sentence of summary, or description)
    summary = company.get("summary") or company.get("description") or ""
    summary_snippet = summary.split(". ")[0] if summary else None

    # Slot values
    slots = {
        "matched_skill": matched_skill,
        "specific_project": specific_project,
        "company_name": company.get("name"),
        "summary_snippet": summary_snippet,
    }

    # Look up rules
    skill_rules = SKILL_TYPE_RULES.get(skill_type, SKILL_TYPE_RULES["developer"])
    stage_rules = STAGE_RULES.get(stage, STAGE_RULES["launched"])
    industry_rules = INDUSTRY_RULES.get(cluster, INDUSTRY_RULES["general"])

    # Assemble and fill slots
    return Guidance(
        your_angle=fill_slots(skill_rules["your_angle"], slots),
        reference_this=fill_slots(industry_rules["reference_this"], slots),
        dont_say=fill_slots(stage_rules["dont_say"], slots),
        your_ask=fill_slots(stage_rules["your_ask"], slots),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/guidance/test_rules.py -k "generate_guidance" -v`
Expected: All 6 generate_guidance tests PASS

- [ ] **Step 5: Run all guidance tests together**

Run: `pytest tests/guidance/test_rules.py -v`
Expected: All tests PASS (schema + classify + map + select + fill + generate)

- [ ] **Step 6: Commit**

```bash
git add backend/guidance/rules.py tests/guidance/test_rules.py
git commit -m "feat: add rule dicts and generate_guidance with composable layers"
```

---

### Task 6: Wire Guidance Into Brief Endpoint

**Files:**
- Modify: `backend/routers/companies.py:50-88`
- Modify: `tests/api/test_companies.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/api/test_companies.py`:

```python
def test_get_company_brief_includes_guidance(client, auth_headers):
    mock_db = MagicMock()

    company = _sample_companies()[0]  # AlphaCo: ai-ml, growing, python scripting + data analysis
    user_data = [{"id": "user-uuid-123", "skills": ["python scripting", "data analysis"], "tier": "paid"}]
    brief_views = []

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "companies":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [company]
        elif table_name == "users":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = user_data
        elif table_name == "brief_views":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = brief_views
            mock_table.insert.return_value.execute.return_value.data = [{}]
        return mock_table

    mock_db.table.side_effect = table_side_effect

    with _mock_auth(), patch("backend.routers.companies.get_db", return_value=mock_db):
        response = client.get("/companies/1", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["guidance"] is not None
    assert "your_angle" in data["guidance"]
    assert "reference_this" in data["guidance"]
    assert "dont_say" in data["guidance"]
    assert "your_ask" in data["guidance"]
    # No unfilled placeholders
    for field in data["guidance"].values():
        assert "{" not in field


def test_get_company_brief_no_skills_no_guidance(client, auth_headers):
    mock_db = MagicMock()

    company = _sample_companies()[0]
    user_data = [{"id": "user-uuid-123", "skills": [], "tier": "paid"}]
    brief_views = []

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "companies":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [company]
        elif table_name == "users":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = user_data
        elif table_name == "brief_views":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = brief_views
            mock_table.insert.return_value.execute.return_value.data = [{}]
        return mock_table

    mock_db.table.side_effect = table_side_effect

    with _mock_auth(), patch("backend.routers.companies.get_db", return_value=mock_db):
        response = client.get("/companies/1", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["guidance"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/api/test_companies.py::test_get_company_brief_includes_guidance -v`
Expected: FAIL — `guidance` field is None (not yet wired)

- [ ] **Step 3: Wire generate_guidance into the brief endpoint**

In `backend/routers/companies.py`, add the import at the top:

```python
from backend.guidance.rules import generate_guidance
```

In the `get_brief` function, replace the block after `# Add match score` (lines 83-88) with:

```python
    # Add match score and guidance
    user_skills = user.get("skills", []) or []
    ms = match_score(user_skills, company.get("need_tags", []) or [])
    company["match_score"] = ms
    company["guidance"] = generate_guidance(user_skills, company)

    return company
```

- [ ] **Step 4: Run the new tests to verify they pass**

Run: `pytest tests/api/test_companies.py::test_get_company_brief_includes_guidance tests/api/test_companies.py::test_get_company_brief_no_skills_no_guidance -v`
Expected: PASS

- [ ] **Step 5: Run all tests to check nothing broke**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/routers/companies.py tests/api/test_companies.py
git commit -m "feat: wire guidance into company brief endpoint"
```

---

### Task 7: Final Verification

**Files:** None (verification only)

- [ ] **Step 1: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests PASS — no regressions

- [ ] **Step 2: Verify guidance output manually**

Run a quick Python check to confirm guidance generates sensible output for a real company:

```bash
python -c "
from backend.guidance.rules import generate_guidance
import json

with open('data/enriched_companies.json') as f:
    companies = json.load(f)

company = companies[0]  # Pando Bioscience
skills = ['Python scripting', 'data visualization']
g = generate_guidance(skills, company)
print(f'your_angle: {g.your_angle}')
print(f'reference_this: {g.reference_this}')
print(f'dont_say: {g.dont_say}')
print(f'your_ask: {g.your_ask}')
"
```

Expected: 4 filled-out guidance strings with no `{placeholder}` markers

- [ ] **Step 3: Commit any final fixes if needed**

If manual verification reveals issues, fix and commit. Otherwise, this task is done.
