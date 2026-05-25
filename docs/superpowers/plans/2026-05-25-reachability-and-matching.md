# Reachability + Capability Matching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace ML reachability with rule-based scoring, and replace the 3,128 free-form tags with a fixed 20-item two-tier capability system.

**Architecture:** New `backend/scoring/reachability.py` computes a weighted rule score. New `frontend/lib/capabilities.ts` defines the fixed vocabulary. `CapabilityPicker` replaces `SkillPicker`. Companies get re-enriched via a constrained-vocabulary script. Matching uses 0-3 capability overlap. Student tier-2 picks are stored in the existing `users.skills` column (avoids migration) — the column now holds tier-2 capability slugs instead of free-form skill strings.

**Tech Stack:** Python/FastAPI (backend), Next.js/React/Tailwind (frontend), Supabase/PostgreSQL (database), Ollama/Qwen3 (re-enrichment)

---

### Task 1: Define Capability Vocabulary

**Files:**
- Create: `backend/capabilities.py`
- Create: `frontend/lib/capabilities.ts`

- [ ] **Step 1: Create backend capability definitions**

```python
# backend/capabilities.py
"""Two-tier capability vocabulary for student-company matching."""

TIER1_CATEGORIES = {
    "engineering": "Engineering (Software)",
    "data-ml": "Data & ML",
    "design": "Design & UX",
    "content": "Content & Research",
    "business": "Business & Ops",
}

TIER2_CAPABILITIES: dict[str, list[str]] = {
    "engineering": [
        "frontend-development",
        "backend-apis",
        "mobile-development",
        "devops-infrastructure",
        "systems-programming",
    ],
    "data-ml": [
        "deep-learning",
        "nlp-language-models",
        "computer-vision",
        "data-pipelines",
        "analytics-visualization",
        "ml-ops",
    ],
    "design": [
        "ui-design",
        "ux-research",
        "product-design",
    ],
    "content": [
        "technical-writing",
        "market-research",
        "scientific-writing",
    ],
    "business": [
        "sales-outreach",
        "operations-process",
        "financial-analysis",
        "growth-marketing",
    ],
}

# Display labels for tier-2 capabilities
TIER2_LABELS: dict[str, str] = {
    "frontend-development": "Frontend Development",
    "backend-apis": "Backend / APIs",
    "mobile-development": "Mobile Development",
    "devops-infrastructure": "DevOps / Infrastructure",
    "systems-programming": "Systems Programming",
    "deep-learning": "Deep Learning / Neural Networks",
    "nlp-language-models": "NLP / Language Models",
    "computer-vision": "Computer Vision",
    "data-pipelines": "Data Pipelines / Engineering",
    "analytics-visualization": "Analytics / Visualization",
    "ml-ops": "ML Ops / Model Deployment",
    "ui-design": "UI Design",
    "ux-research": "UX Research",
    "product-design": "Product Design",
    "technical-writing": "Technical Writing",
    "market-research": "Market Research",
    "scientific-writing": "Scientific Writing",
    "sales-outreach": "Sales / Outreach",
    "operations-process": "Operations / Process",
    "financial-analysis": "Financial Analysis",
    "growth-marketing": "Growth / Marketing",
}

ALL_TIER2 = [cap for caps in TIER2_CAPABILITIES.values() for cap in caps]

MAX_TIER1 = 2
MAX_TIER2 = 3
```

- [ ] **Step 2: Create frontend capability definitions**

```typescript
// frontend/lib/capabilities.ts
export const TIER1_CATEGORIES = {
  engineering: "Engineering (Software)",
  "data-ml": "Data & ML",
  design: "Design & UX",
  content: "Content & Research",
  business: "Business & Ops",
} as const;

export type Tier1Key = keyof typeof TIER1_CATEGORIES;

export const TIER2_CAPABILITIES: Record<Tier1Key, string[]> = {
  engineering: [
    "frontend-development",
    "backend-apis",
    "mobile-development",
    "devops-infrastructure",
    "systems-programming",
  ],
  "data-ml": [
    "deep-learning",
    "nlp-language-models",
    "computer-vision",
    "data-pipelines",
    "analytics-visualization",
    "ml-ops",
  ],
  design: [
    "ui-design",
    "ux-research",
    "product-design",
  ],
  content: [
    "technical-writing",
    "market-research",
    "scientific-writing",
  ],
  business: [
    "sales-outreach",
    "operations-process",
    "financial-analysis",
    "growth-marketing",
  ],
};

export const TIER2_LABELS: Record<string, string> = {
  "frontend-development": "Frontend Development",
  "backend-apis": "Backend / APIs",
  "mobile-development": "Mobile Development",
  "devops-infrastructure": "DevOps / Infrastructure",
  "systems-programming": "Systems Programming",
  "deep-learning": "Deep Learning / Neural Networks",
  "nlp-language-models": "NLP / Language Models",
  "computer-vision": "Computer Vision",
  "data-pipelines": "Data Pipelines / Engineering",
  "analytics-visualization": "Analytics / Visualization",
  "ml-ops": "ML Ops / Model Deployment",
  "ui-design": "UI Design",
  "ux-research": "UX Research",
  "product-design": "Product Design",
  "technical-writing": "Technical Writing",
  "market-research": "Market Research",
  "scientific-writing": "Scientific Writing",
  "sales-outreach": "Sales / Outreach",
  "operations-process": "Operations / Process",
  "financial-analysis": "Financial Analysis",
  "growth-marketing": "Growth / Marketing",
};

export const MAX_TIER1 = 2;
export const MAX_TIER2 = 3;
```

- [ ] **Step 3: Commit**

```bash
git add backend/capabilities.py frontend/lib/capabilities.ts
git commit -m "feat: define two-tier capability vocabulary"
```

---

### Task 2: Rule-Based Reachability Scorer

**Files:**
- Create: `backend/scoring/__init__.py`
- Create: `backend/scoring/reachability.py`
- Create: `tests/scoring/__init__.py`
- Create: `tests/scoring/test_reachability.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/scoring/__init__.py
# (empty)

# tests/scoring/test_reachability.py
from backend.scoring.reachability import compute_reachability


def test_small_team_building_mvp_hiring_nearby_contactable():
    """Perfect reachability: all factors present."""
    company = {
        "team_size": 3,
        "stage_detail": "building-mvp",
        "is_hiring": True,
        "founder_linkedin": "https://linkedin.com/in/founder",
        "founder_twitter": None,
        "all_locations": "San Francisco, CA",
    }
    score, factors = compute_reachability(company, student_location="San Francisco")
    assert score >= 0.9
    assert "Small team" in factors
    assert "Building MVP" in factors
    assert "Hiring" in factors
    assert "Near you" in factors
    assert "LinkedIn" in factors or "Twitter" in factors


def test_large_team_scaling_no_contact():
    """Worst reachability: no factors present."""
    company = {
        "team_size": 50,
        "stage_detail": "scaling",
        "is_hiring": False,
        "founder_linkedin": None,
        "founder_twitter": None,
        "all_locations": "London, UK",
    }
    score, factors = compute_reachability(company, student_location="San Francisco")
    assert score == 0.0
    assert factors == []


def test_missing_team_size_no_penalty():
    """None team_size should not contribute but not crash."""
    company = {
        "team_size": None,
        "stage_detail": "building-mvp",
        "is_hiring": True,
        "founder_linkedin": "https://linkedin.com/in/x",
        "founder_twitter": None,
        "all_locations": None,
    }
    score, factors = compute_reachability(company)
    assert score > 0.0
    assert "Small team" not in factors


def test_no_student_location_skips_proximity():
    """Without student location, proximity factor is skipped."""
    company = {
        "team_size": 2,
        "stage_detail": "launched",
        "is_hiring": False,
        "founder_linkedin": None,
        "founder_twitter": "https://twitter.com/founder",
        "all_locations": "San Francisco, CA",
    }
    score, factors = compute_reachability(company, student_location=None)
    assert "Near you" not in factors


def test_score_bucketing():
    """Score converts to high/medium/low labels correctly."""
    from backend.scoring.reachability import bucket_score
    assert bucket_score(0.75) == "high"
    assert bucket_score(0.5) == "medium"
    assert bucket_score(0.3) == "low"
    assert bucket_score(0.7) == "high"
    assert bucket_score(0.4) == "medium"
    assert bucket_score(0.39) == "low"


def test_location_match_case_insensitive():
    """Location matching should be case-insensitive substring."""
    company = {
        "team_size": 3,
        "stage_detail": "building-mvp",
        "is_hiring": False,
        "founder_linkedin": None,
        "founder_twitter": None,
        "all_locations": "San Francisco, CA",
    }
    score_match, factors_match = compute_reachability(company, student_location="san francisco")
    score_no, factors_no = compute_reachability(company, student_location="New York")
    assert "Near you" in factors_match
    assert "Near you" not in factors_no
    assert score_match > score_no
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/scoring/test_reachability.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.scoring'`

- [ ] **Step 3: Write implementation**

```python
# backend/scoring/__init__.py
# (empty)

# backend/scoring/reachability.py
"""Rule-based reachability scoring for companies."""

# Weights must sum to 1.0
TEAM_SIZE_WEIGHT = 0.30
STAGE_WEIGHT = 0.25
HIRING_WEIGHT = 0.20
LOCATION_WEIGHT = 0.15
CONTACT_WEIGHT = 0.10

SMALL_TEAM_MAX = 5
HIGH_THRESHOLD = 0.70
LOW_THRESHOLD = 0.40


def compute_reachability(
    company: dict,
    student_location: str | None = None,
) -> tuple[float, list[str]]:
    """Compute rule-based reachability score.

    Returns (score 0.0-1.0, list of contributing factor labels).
    """
    score = 0.0
    factors: list[str] = []

    # Factor 1: Team size
    team_size = company.get("team_size")
    if team_size is not None and 1 <= team_size <= SMALL_TEAM_MAX:
        score += TEAM_SIZE_WEIGHT
        factors.append(f"Small team ({team_size} people)")

    # Factor 2: Stage
    stage = company.get("stage_detail")
    if stage == "building-mvp":
        score += STAGE_WEIGHT
        factors.append("Building MVP")
    elif stage == "launched":
        score += STAGE_WEIGHT * 0.6
        factors.append("Recently launched")

    # Factor 3: Hiring
    if company.get("is_hiring"):
        score += HIRING_WEIGHT
        factors.append("Hiring")

    # Factor 4: Location proximity
    company_location = company.get("all_locations") or ""
    if student_location and company_location:
        if student_location.lower() in company_location.lower():
            score += LOCATION_WEIGHT
            factors.append("Near you")

    # Factor 5: Contactable
    has_linkedin = bool(company.get("founder_linkedin"))
    has_twitter = bool(company.get("founder_twitter"))
    if has_linkedin or has_twitter:
        score += CONTACT_WEIGHT
        if has_linkedin:
            factors.append("LinkedIn")
        if has_twitter:
            factors.append("Twitter")

    return round(score, 4), factors


def bucket_score(score: float) -> str:
    """Convert 0-1 score to high/medium/low label."""
    if score >= HIGH_THRESHOLD:
        return "high"
    elif score >= LOW_THRESHOLD:
        return "medium"
    return "low"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/scoring/test_reachability.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/scoring/ tests/scoring/
git commit -m "feat: add rule-based reachability scorer"
```

---

### Task 3: Update Backend Schemas and Database

**Files:**
- Modify: `backend/schemas.py`
- Modify: `backend/db/schema.sql`

- [ ] **Step 1: Add fields to schemas.py**

Add `location` to `UserProfile` and `UserUpdate`. Add `capability_tags` and `reachability_factors` to company schemas.

In `backend/schemas.py`, add `location` field to `UserProfile`:
```python
class UserProfile(BaseModel):
    id: str
    email: str
    school: str | None = None
    grad_year: int | None = None
    skills: list[str] = []
    location: str | None = None
    bio: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    tier: str = "free"
```

Add `location` to `UserUpdate`:
```python
class UserUpdate(BaseModel):
    school: str | None = None
    grad_year: int | None = None
    skills: list[str] | None = None
    location: str | None = None
    bio: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
```

Add `capability_tags` to `CompanyCard`:
```python
class CompanyCard(BaseModel):
    id: int
    name: str
    yc_batch: str | None = None
    one_liner: str | None = None
    industry: str | None = None
    stage_detail: str | None = None
    technical_level: str | None = None
    team_size: int | None = None
    reachability_score: str | None = None
    small_logo_url: str | None = None
    founder_name: str | None = None
    founder_title: str | None = None
    founder_avatar_url: str | None = None
    need_tags: list[str] = []
    capability_tags: list[str] = []
    match_score: int = 0
    rank_score: float = 0.0
```

Add `capability_tags` and `reachability_factors` to `CompanyBrief`:
```python
class CompanyBrief(BaseModel):
    id: int
    name: str
    yc_batch: str | None = None
    description: str | None = None
    summary: str | None = None
    one_liner: str | None = None
    website: str | None = None
    industry: str | None = None
    stage: str | None = None
    stage_detail: str | None = None
    technical_level: str | None = None
    team_size: int | None = None
    need_tags: list[str] = []
    capability_tags: list[str] = []
    specific_projects: list[str] = []
    reachability_score: str | None = None
    reachability_probability: float | None = None
    reachability_factors: list[str] = []
    founder_name: str | None = None
    founder_title: str | None = None
    founder_linkedin: str | None = None
    founder_twitter: str | None = None
    founder_avatar_url: str | None = None
    founder_email: str | None = None
    small_logo_url: str | None = None
    slug: str | None = None
    all_locations: str | None = None
    tags: list[str] = []
    industries: list[str] = []
    match_score: int = 0
    guidance: Guidance | None = None
```

- [ ] **Step 2: Update schema.sql with new columns**

Add to the users table definition:
```sql
-- Add after 'skills TEXT[] DEFAULT '{}'':
location TEXT,
```

Add to the companies table definition:
```sql
-- Add after 'need_tags TEXT[] DEFAULT '{}'':
capability_tags TEXT[] DEFAULT '{}',
```

- [ ] **Step 3: Run the SQL migration on Supabase**

Run these via Supabase dashboard SQL editor or CLI:
```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS location TEXT;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS capability_tags TEXT[] DEFAULT '{}';
```

- [ ] **Step 4: Commit**

```bash
git add backend/schemas.py backend/db/schema.sql
git commit -m "feat: add location and capability_tags to schemas"
```

---

### Task 4: Update Frontend Types

**Files:**
- Modify: `frontend/lib/types.ts`

- [ ] **Step 1: Add location to UserProfile and capability_tags to company types**

In `frontend/lib/types.ts`, add `location` to `UserProfile`:
```typescript
export interface UserProfile {
  id: string;
  email: string;
  school: string | null;
  grad_year: number | null;
  skills: string[];
  location: string | null;
  bio: string | null;
  github_url: string | null;
  portfolio_url: string | null;
  tier: string;
}
```

Add `capability_tags` to `CompanyCard`:
```typescript
export interface CompanyCard {
  id: number;
  name: string;
  yc_batch: string | null;
  one_liner: string | null;
  industry: string | null;
  stage_detail: string | null;
  technical_level: string | null;
  team_size: number | null;
  reachability_score: string | null;
  small_logo_url: string | null;
  founder_name: string | null;
  founder_title: string | null;
  founder_avatar_url: string | null;
  need_tags: string[];
  capability_tags: string[];
  match_score: number;
  rank_score: number;
}
```

Add `capability_tags` and `reachability_factors` to `CompanyBrief`:
```typescript
export interface CompanyBrief {
  id: number;
  name: string;
  yc_batch: string | null;
  description: string | null;
  summary: string | null;
  one_liner: string | null;
  website: string | null;
  industry: string | null;
  stage: string | null;
  stage_detail: string | null;
  technical_level: string | null;
  team_size: number | null;
  need_tags: string[];
  capability_tags: string[];
  specific_projects: string[];
  reachability_score: string | null;
  reachability_probability: number | null;
  reachability_factors: string[];
  founder_name: string | null;
  founder_title: string | null;
  founder_linkedin: string | null;
  founder_twitter: string | null;
  founder_avatar_url: string | null;
  founder_email: string | null;
  small_logo_url: string | null;
  slug: string | null;
  all_locations: string | null;
  tags: string[];
  industries: string[];
  match_score: number;
  guidance: Guidance | null;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/lib/types.ts
git commit -m "feat: add capability_tags and location to frontend types"
```

---

### Task 5: Update Matching Scorer

**Files:**
- Modify: `backend/matching/scorer.py`
- Modify: `tests/matching/test_scorer.py`

- [ ] **Step 1: Write failing tests for new matching logic**

Replace the contents of `tests/matching/test_scorer.py`:

```python
from backend.matching.scorer import match_score, rank_companies


def test_match_score_full_overlap():
    user_caps = ["frontend-development", "backend-apis", "data-pipelines"]
    company_caps = ["frontend-development", "backend-apis", "data-pipelines"]
    assert match_score(user_caps, company_caps) == 3


def test_match_score_partial_overlap():
    user_caps = ["frontend-development", "backend-apis"]
    company_caps = ["frontend-development", "deep-learning", "ui-design"]
    assert match_score(user_caps, company_caps) == 1


def test_match_score_no_overlap():
    user_caps = ["ui-design", "ux-research"]
    company_caps = ["frontend-development", "data-pipelines"]
    assert match_score(user_caps, company_caps) == 0


def test_match_score_empty():
    assert match_score([], ["frontend-development"]) == 0
    assert match_score(["frontend-development"], []) == 0
    assert match_score([], []) == 0


def test_rank_uses_capability_tags():
    companies = [
        {"id": 1, "name": "NoMatch", "capability_tags": ["ui-design"], "reachability_probability": 0.9},
        {"id": 2, "name": "FullMatch", "capability_tags": ["frontend-development", "backend-apis"], "reachability_probability": 0.5},
        {"id": 3, "name": "PartialMatch", "capability_tags": ["frontend-development"], "reachability_probability": 0.7},
    ]
    user_caps = ["frontend-development", "backend-apis"]
    ranked = rank_companies(companies, user_caps)

    assert ranked[0]["name"] == "FullMatch"
    assert ranked[0]["match_score"] == 2


def test_rank_no_caps_uses_reachability_only():
    companies = [
        {"id": 1, "name": "Low", "capability_tags": ["x"], "reachability_probability": 0.3},
        {"id": 2, "name": "High", "capability_tags": ["y"], "reachability_probability": 0.9},
    ]
    ranked = rank_companies(companies, user_capabilities=None)

    assert ranked[0]["name"] == "High"
    assert ranked[1]["name"] == "Low"


def test_rank_falls_back_to_need_tags():
    """Companies without capability_tags yet should fall back to need_tags."""
    companies = [
        {"id": 1, "name": "OldData", "need_tags": ["frontend-development"], "reachability_probability": 0.5},
    ]
    ranked = rank_companies(companies, ["frontend-development"])
    assert ranked[0]["match_score"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/matching/test_scorer.py -v`
Expected: FAIL — `rank_companies() got an unexpected keyword argument 'user_capabilities'`

- [ ] **Step 3: Update scorer implementation**

Replace the contents of `backend/matching/scorer.py`:

```python
"""Match scoring: rank companies by capability overlap + reachability."""

REACHABILITY_WEIGHT = 0.4
MATCH_WEIGHT = 0.6
MAX_MATCH_SCORE = 3  # Students pick up to 3 tier-2 capabilities


def match_score(user_capabilities: list[str], company_capabilities: list[str]) -> int:
    """Count overlapping capabilities between user and company."""
    if not user_capabilities or not company_capabilities:
        return 0
    return len(set(user_capabilities) & set(company_capabilities))


def rank_companies(
    companies: list[dict],
    user_capabilities: list[str] | None = None,
) -> list[dict]:
    """Rank companies by combined match + reachability score.

    Uses capability_tags for matching, falls back to need_tags if
    capability_tags is empty (for companies not yet re-enriched).
    """
    scored = []
    for company in companies:
        company_caps = company.get("capability_tags") or []
        if not company_caps:
            company_caps = company.get("need_tags") or []
        reachability = company.get("reachability_probability", 0.0) or 0.0

        if user_capabilities:
            ms = match_score(user_capabilities, company_caps)
            normalized_match = min(ms / MAX_MATCH_SCORE, 1.0)
            rank = (REACHABILITY_WEIGHT * reachability) + (MATCH_WEIGHT * normalized_match)
        else:
            ms = 0
            rank = reachability

        scored.append({**company, "match_score": ms, "rank_score": round(rank, 4)})

    scored.sort(key=lambda c: c["rank_score"], reverse=True)
    return scored
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/matching/test_scorer.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/matching/scorer.py tests/matching/test_scorer.py
git commit -m "feat: update matcher to use capability_tags with 0-3 range"
```

---

### Task 6: Wire Reachability Into Companies Router

**Files:**
- Modify: `backend/routers/companies.py`
- Modify: `tests/api/test_companies.py`

- [ ] **Step 1: Read current test file to understand mocking patterns**

Run: `cat tests/api/test_companies.py` to see existing patterns.

- [ ] **Step 2: Update companies router**

Replace the contents of `backend/routers/companies.py`:

```python
"""Company browsing and brief endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from backend.auth import get_current_user, get_optional_user
from backend.db import get_db
from backend.matching.scorer import rank_companies, match_score
from backend.guidance.rules import generate_guidance
from backend.scoring.reachability import compute_reachability, bucket_score
from backend.schemas import CompanyCard, CompanyBrief

router = APIRouter()


@router.get("/companies", response_model=list[CompanyCard])
def list_companies(
    request: Request,
    industry: str | None = Query(None),
    reachability: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
):
    """Browse company cards. Ranked by match score if authenticated."""
    db = get_db()
    user_id = get_optional_user(request)

    query = db.table("companies").select("*").eq("status", "Active")

    if industry:
        query = query.eq("industry", industry)
    if reachability:
        query = query.eq("reachability_score", reachability)

    result = query.execute()
    companies = result.data

    # Get user capabilities and location if authenticated
    user_capabilities = None
    student_location = None
    if user_id:
        user_result = db.table("users").select("skills, location").eq("id", user_id).execute()
        if user_result.data:
            user_capabilities = user_result.data[0].get("skills")
            student_location = user_result.data[0].get("location")

    # Compute reachability scores on the fly
    for company in companies:
        score, factors = compute_reachability(company, student_location)
        company["reachability_probability"] = score
        company["reachability_score"] = bucket_score(score)

    ranked = rank_companies(companies, user_capabilities)
    start = (page - 1) * limit
    return ranked[start:start + limit]


@router.get("/companies/{company_id}", response_model=CompanyBrief)
def get_brief(
    company_id: int,
    request: Request,
    user_id: str = Depends(get_current_user),
):
    """Get full company brief."""
    db = get_db()

    result = db.table("companies").select("*").eq("id", company_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Company not found")
    company = result.data[0]

    # Get user for matching and location
    user_result = db.table("users").select("skills, location").eq("id", user_id).execute()
    user = user_result.data[0] if user_result.data else {"skills": [], "location": None}

    # Record the view
    try:
        db.table("brief_views").insert({"user_id": user_id, "company_id": company_id}).execute()
    except Exception:
        pass

    # Compute reachability
    user_skills = user.get("skills", []) or []
    student_location = user.get("location")
    score, factors = compute_reachability(company, student_location)
    company["reachability_probability"] = score
    company["reachability_score"] = bucket_score(score)
    company["reachability_factors"] = factors

    # Match score and guidance
    ms = match_score(user_skills, company.get("capability_tags") or company.get("need_tags") or [])
    company["match_score"] = ms
    company["guidance"] = generate_guidance(user_skills, company)

    return company
```

- [ ] **Step 3: Run existing API tests to check nothing broke**

Run: `pytest tests/api/test_companies.py -v`
Expected: All existing tests PASS (they mock the database, so reachability just adds fields)

- [ ] **Step 4: Commit**

```bash
git add backend/routers/companies.py
git commit -m "feat: wire rule-based reachability into companies router"
```

---

### Task 7: Re-Enrichment Script for Capability Tags

**Files:**
- Create: `backend/pipeline/enrich_capabilities.py`

- [ ] **Step 1: Write the re-enrichment script**

```python
# backend/pipeline/enrich_capabilities.py
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/pipeline/enrich_capabilities.py
git commit -m "feat: add constrained-vocabulary capability re-enrichment script"
```

---

### Task 8: Upload Capability Tags to Supabase

**Files:**
- Create: `backend/pipeline/upload_capabilities.py`

- [ ] **Step 1: Write upload script**

```python
# backend/pipeline/upload_capabilities.py
"""Upload capability_tags from enrichment output to Supabase."""

import json
from backend.db import get_db

BATCH_SIZE = 500


def upload(tags_path: str = "data/capability_tags.json"):
    with open(tags_path) as f:
        results = json.load(f)

    db = get_db()
    updates = [{"name": name, "capability_tags": tags} for name, tags in results.items() if tags]

    for i in range(0, len(updates), BATCH_SIZE):
        batch = updates[i:i + BATCH_SIZE]
        db.table("companies").upsert(batch, on_conflict="name").execute()
        print(f"  Uploaded {min(i + BATCH_SIZE, len(updates))}/{len(updates)}")

    print(f"Done. Updated {len(updates)} companies.")


if __name__ == "__main__":
    upload()
```

- [ ] **Step 2: Commit**

```bash
git add backend/pipeline/upload_capabilities.py
git commit -m "feat: add capability_tags upload script"
```

---

### Task 9: CapabilityPicker Component

**Files:**
- Create: `frontend/components/CapabilityPicker.tsx`

- [ ] **Step 1: Build the two-tier picker**

```tsx
// frontend/components/CapabilityPicker.tsx
"use client";

import { useState } from "react";
import {
  TIER1_CATEGORIES,
  TIER2_CAPABILITIES,
  TIER2_LABELS,
  MAX_TIER1,
  MAX_TIER2,
  type Tier1Key,
} from "@/lib/capabilities";

interface CapabilityPickerProps {
  selectedTier1: Tier1Key[];
  selectedTier2: string[];
  onChangeTier1: (categories: Tier1Key[]) => void;
  onChangeTier2: (capabilities: string[]) => void;
}

export default function CapabilityPicker({
  selectedTier1,
  selectedTier2,
  onChangeTier1,
  onChangeTier2,
}: CapabilityPickerProps) {
  const [expanded, setExpanded] = useState<Tier1Key | null>(
    selectedTier1[0] ?? null,
  );

  function toggleTier1(key: Tier1Key) {
    if (selectedTier1.includes(key)) {
      // Deselect category and remove its tier-2 picks
      const nextTier1 = selectedTier1.filter((k) => k !== key);
      const removable = new Set(TIER2_CAPABILITIES[key]);
      const nextTier2 = selectedTier2.filter((c) => !removable.has(c));
      onChangeTier1(nextTier1);
      onChangeTier2(nextTier2);
      if (expanded === key) {
        setExpanded(nextTier1[0] ?? null);
      }
    } else if (selectedTier1.length < MAX_TIER1) {
      onChangeTier1([...selectedTier1, key]);
      setExpanded(key);
    }
  }

  function toggleTier2(cap: string) {
    if (selectedTier2.includes(cap)) {
      onChangeTier2(selectedTier2.filter((c) => c !== cap));
    } else if (selectedTier2.length < MAX_TIER2) {
      onChangeTier2([...selectedTier2, cap]);
    }
  }

  const tier1Keys = Object.keys(TIER1_CATEGORIES) as Tier1Key[];

  return (
    <div className="flex flex-col gap-5">
      {/* Tier 1: Broad categories */}
      <div>
        <p className="mb-2 text-sm font-medium text-secondary">
          What kind of work do you do? Pick up to {MAX_TIER1}.
        </p>
        <div className="flex flex-wrap gap-2">
          {tier1Keys.map((key) => {
            const isSelected = selectedTier1.includes(key);
            return (
              <button
                key={key}
                type="button"
                onClick={() => toggleTier1(key)}
                className={`rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors ${
                  isSelected
                    ? "border-accent bg-accent/10 text-accent"
                    : selectedTier1.length >= MAX_TIER1
                      ? "border-card-border bg-card text-tertiary opacity-50"
                      : "border-card-border bg-card text-secondary hover:border-accent/50 hover:text-primary"
                }`}
              >
                {TIER1_CATEGORIES[key]}
              </button>
            );
          })}
        </div>
      </div>

      {/* Tier 2: Specific capabilities */}
      {selectedTier1.length > 0 && (
        <div>
          <div className="mb-2 flex items-center justify-between">
            <p className="text-sm font-medium text-secondary">
              What specifically? Pick up to {MAX_TIER2}.
            </p>
            <p
              className={`text-sm font-medium ${
                selectedTier2.length >= MAX_TIER2
                  ? "text-accent"
                  : "text-tertiary"
              }`}
            >
              {selectedTier2.length} of {MAX_TIER2}
            </p>
          </div>

          {/* Category tabs if 2 selected */}
          {selectedTier1.length > 1 && (
            <div className="mb-3 flex gap-1 rounded-lg bg-background p-1">
              {selectedTier1.map((key) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setExpanded(key)}
                  className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                    expanded === key
                      ? "bg-card text-primary shadow-sm"
                      : "text-secondary hover:text-primary"
                  }`}
                >
                  {TIER1_CATEGORIES[key]}
                </button>
              ))}
            </div>
          )}

          {/* Capability buttons for expanded category */}
          {expanded && selectedTier1.includes(expanded) && (
            <div className="flex flex-wrap gap-2">
              {TIER2_CAPABILITIES[expanded].map((cap) => {
                const isSelected = selectedTier2.includes(cap);
                const isDisabled =
                  !isSelected && selectedTier2.length >= MAX_TIER2;
                return (
                  <button
                    key={cap}
                    type="button"
                    onClick={() => toggleTier2(cap)}
                    disabled={isDisabled}
                    className={`rounded-full border px-3.5 py-1.5 text-sm transition-colors ${
                      isSelected
                        ? "border-accent bg-accent text-white"
                        : isDisabled
                          ? "border-card-border bg-card text-tertiary opacity-50"
                          : "border-card-border bg-card text-secondary hover:border-accent/50 hover:text-primary"
                    }`}
                  >
                    {TIER2_LABELS[cap]}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Selected summary */}
      {selectedTier2.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {selectedTier2.map((cap) => (
            <span
              key={cap}
              className="flex items-center gap-1.5 rounded-full bg-accent px-2.5 py-1 text-sm text-white"
            >
              {TIER2_LABELS[cap]}
              <button
                type="button"
                onClick={() => toggleTier2(cap)}
                className="flex h-4 w-4 items-center justify-center rounded-full text-xs leading-none transition-opacity hover:opacity-75"
                aria-label={`Remove ${TIER2_LABELS[cap]}`}
              >
                x
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify it compiles**

Run: `cd frontend && npx next build 2>&1 | tail -5`
Expected: Build succeeds (component not imported anywhere yet, but no syntax errors)

- [ ] **Step 3: Commit**

```bash
git add frontend/components/CapabilityPicker.tsx
git commit -m "feat: add two-tier CapabilityPicker component"
```

---

### Task 10: Update Onboarding Flow

**Files:**
- Modify: `frontend/app/onboard/page.tsx`

- [ ] **Step 1: Rewrite onboarding with capability picker + location**

```tsx
// frontend/app/onboard/page.tsx
"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useRequireAuth } from "@/lib/useAuth";
import { fetchProfile, updateProfile } from "@/lib/api";
import CapabilityPicker from "@/components/CapabilityPicker";
import type { Tier1Key } from "@/lib/capabilities";

export default function OnboardPage() {
  const { authenticated, loading: authLoading } = useRequireAuth();
  const router = useRouter();

  const [profileLoading, setProfileLoading] = useState(true);
  const [step, setStep] = useState<"capabilities" | "location">("capabilities");
  const [selectedTier1, setSelectedTier1] = useState<Tier1Key[]>([]);
  const [selectedTier2, setSelectedTier2] = useState<string[]>([]);
  const [location, setLocation] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!authenticated) return;

    fetchProfile()
      .then((profile) => {
        if (profile.skills && profile.skills.length > 0) {
          router.replace("/feed");
        } else {
          setProfileLoading(false);
        }
      })
      .catch(() => {
        setProfileLoading(false);
      });
  }, [authenticated, router]);

  async function handleFinish() {
    setSaving(true);
    try {
      await updateProfile({
        skills: selectedTier2,
        location: location.trim() || null,
      });
    } catch {
      // proceed to feed even if save fails
    } finally {
      setSaving(false);
      router.push("/feed");
    }
  }

  if (authLoading || profileLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-secondary">Loading...</p>
      </div>
    );
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-20">
      <div className="flex flex-col gap-6">
        {step === "capabilities" && (
          <>
            <div className="flex flex-col gap-2">
              <h1 className="font-display text-4xl text-primary">
                What are you good at?
              </h1>
              <p className="text-secondary">
                Pick your focus areas so we can match you with the right
                founders.
              </p>
            </div>

            <CapabilityPicker
              selectedTier1={selectedTier1}
              selectedTier2={selectedTier2}
              onChangeTier1={setSelectedTier1}
              onChangeTier2={setSelectedTier2}
            />

            <div className="flex flex-col items-start gap-3 pt-2">
              <button
                type="button"
                onClick={() => setStep("location")}
                disabled={selectedTier2.length === 0}
                className="rounded-lg bg-accent px-6 py-2.5 text-sm font-medium text-white transition-opacity disabled:opacity-40"
              >
                Continue
              </button>

              <button
                type="button"
                onClick={() => router.push("/feed")}
                className="text-sm text-tertiary underline-offset-2 hover:underline"
              >
                Skip for now
              </button>
            </div>
          </>
        )}

        {step === "location" && (
          <>
            <div className="flex flex-col gap-2">
              <h1 className="font-display text-4xl text-primary">
                Where are you based?
              </h1>
              <p className="text-secondary">
                Founders near you are more likely to meet in person.
              </p>
            </div>

            <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="e.g. San Francisco, New York, Austin..."
              className="rounded-lg border border-card-border bg-card px-3 py-2.5 text-sm text-primary placeholder:text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
            />

            <div className="flex flex-col items-start gap-3 pt-2">
              <button
                type="button"
                onClick={handleFinish}
                disabled={saving}
                className="rounded-lg bg-accent px-6 py-2.5 text-sm font-medium text-white transition-opacity disabled:opacity-40"
              >
                {saving ? "Saving..." : "Finish"}
              </button>

              <button
                type="button"
                onClick={handleFinish}
                className="text-sm text-tertiary underline-offset-2 hover:underline"
              >
                Skip location
              </button>
            </div>
          </>
        )}
      </div>
    </main>
  );
}
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npx next build 2>&1 | tail -5`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add frontend/app/onboard/page.tsx
git commit -m "feat: update onboarding with capability picker and location step"
```

---

### Task 11: Update Profile Page

**Files:**
- Modify: `frontend/app/profile/page.tsx`

- [ ] **Step 1: Replace SkillPicker with CapabilityPicker + add location field**

In `frontend/app/profile/page.tsx`, make the following changes:

Replace the import:
```tsx
// old
import SkillPicker from "@/components/SkillPicker";
// new
import CapabilityPicker from "@/components/CapabilityPicker";
import { TIER2_CAPABILITIES, type Tier1Key } from "@/lib/capabilities";
```

Add a helper function to derive tier-1 from tier-2 selections (above the component):
```tsx
function deriveTier1(tier2: string[]): Tier1Key[] {
  const categories = new Set<Tier1Key>();
  for (const [cat, caps] of Object.entries(TIER2_CAPABILITIES)) {
    if (tier2.some((t) => (caps as string[]).includes(t))) {
      categories.add(cat as Tier1Key);
    }
  }
  return Array.from(categories);
}
```

Add state for tier1, location, and initialize from profile:
```tsx
const [selectedTier1, setSelectedTier1] = useState<Tier1Key[]>([]);
const [location, setLocation] = useState("");
```

In the `fetchProfile().then()` callback, add:
```tsx
setSelectedTier1(deriveTier1(p.skills ?? []));
setLocation(p.location ?? "");
```

Replace the `handleSkillsChange` function:
```tsx
function handleTier1Change(newTier1: Tier1Key[]) {
  setSelectedTier1(newTier1);
}

function handleTier2Change(newTier2: string[]) {
  setSkills(newTier2);

  if (skillsDebounceRef.current !== undefined) {
    clearTimeout(skillsDebounceRef.current);
  }

  skillsDebounceRef.current = setTimeout(() => {
    updateProfile({ skills: newTier2 }).catch(() => {});
  }, 500);
}
```

Replace the Skills section JSX:
```tsx
<section className="flex flex-col gap-3">
  <h2 className="font-display text-2xl text-primary">Capabilities</h2>
  <CapabilityPicker
    selectedTier1={selectedTier1}
    selectedTier2={skills}
    onChangeTier1={handleTier1Change}
    onChangeTier2={handleTier2Change}
  />
</section>
```

Add location field to the form (after the School field):
```tsx
<div className="flex flex-col gap-1.5">
  <label htmlFor="location" className="text-sm font-medium text-secondary">
    Location
  </label>
  <input
    id="location"
    type="text"
    value={location}
    onChange={(e) => setLocation(e.target.value)}
    placeholder="e.g. San Francisco, New York, Austin..."
    className="rounded-lg border border-card-border bg-card px-3 py-2 text-sm text-primary placeholder:text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
  />
</div>
```

Add `location` to the `handleSave` call:
```tsx
await updateProfile({
  school: school || null,
  grad_year: gradYear ? Number(gradYear) : null,
  bio: bio || null,
  github_url: githubUrl || null,
  portfolio_url: portfolioUrl || null,
  location: location || null,
});
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npx next build 2>&1 | tail -5`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add frontend/app/profile/page.tsx
git commit -m "feat: update profile with capability picker and location"
```

---

### Task 12: Show Reachability Explanation on Brief Page

**Files:**
- Modify: `frontend/app/founder/[id]/page.tsx`

- [ ] **Step 1: Add reachability factors display**

In `frontend/app/founder/[id]/page.tsx`, the brief page already renders `<FounderBrief brief={brief} />`. The `CompanyBrief` type now includes `reachability_factors: string[]`.

Add a reachability explanation section after `<FounderBrief>` and before `<GuidanceCard>`:

```tsx
{brief.reachability_factors && brief.reachability_factors.length > 0 && (
  <div className="my-4 rounded-lg border border-card-border bg-card p-4">
    <p className="text-sm font-medium text-primary">
      Why this founder is{" "}
      <span
        className={
          brief.reachability_score === "high"
            ? "text-reach-high"
            : brief.reachability_score === "medium"
              ? "text-reach-med"
              : "text-reach-low"
        }
      >
        {brief.reachability_score} reachability
      </span>
    </p>
    <div className="mt-2 flex flex-wrap gap-2">
      {brief.reachability_factors.map((factor) => (
        <span
          key={factor}
          className="rounded-full bg-background px-2.5 py-0.5 text-xs text-secondary"
        >
          {factor}
        </span>
      ))}
    </div>
  </div>
)}
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npx next build 2>&1 | tail -5`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add frontend/app/founder/[id]/page.tsx
git commit -m "feat: show reachability explanation on brief page"
```

---

### Task 13: Run Full Test Suite

- [ ] **Step 1: Run all backend tests**

Run: `pytest tests/ -v --tb=short`
Expected: All tests pass. Some guidance tests may need minor updates if they reference `need_tags` in their fixtures — fix inline if needed.

- [ ] **Step 2: Run frontend build**

Run: `cd frontend && npx next build 2>&1 | tail -10`
Expected: Build succeeds with no errors.

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "chore: verify all tests pass after reachability + matching overhaul"
```
