# Backend API + Auth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a FastAPI backend with Supabase Auth integration, company browsing with match-based ranking, brief access gating, outreach tracking, and a pipeline step to upload data to Supabase.

**Architecture:** FastAPI verifies Supabase-issued JWTs, queries Supabase as a Postgres database via supabase-py, and computes match scores at request time. User profiles are auto-created on first API call. The pipeline uploads enriched company data to Supabase via an upsert step.

**Tech Stack:** FastAPI, uvicorn, supabase-py, python-jose[cryptography], pydantic

**Spec:** `docs/superpowers/specs/2026-05-21-backend-api-design.md`

---

## File Structure

```
backend/
├── main.py                    # FastAPI app, CORS, router includes
├── auth.py                    # JWT verification dependency
├── db.py                      # Supabase client singleton
├── schemas.py                 # Pydantic request/response models
├── routers/
│   ├── __init__.py
│   ├── users.py               # GET /me, PUT /me
│   ├── companies.py           # GET /companies, GET /companies/{id}
│   └── outreach.py            # GET/POST/PUT /outreach
├── matching/
│   ├── __init__.py
│   └── scorer.py              # match_score + rank_companies
├── pipeline/
│   ├── supabase_write.py      # NEW — upsert to Supabase
│   └── (existing files)
└── ml/                        # existing, no changes

tests/
├── api/
│   ├── __init__.py
│   ├── test_auth.py
│   ├── test_users.py
│   ├── test_companies.py
│   └── test_outreach.py
├── matching/
│   ├── __init__.py
│   └── test_scorer.py
└── pipeline/
    ├── test_supabase_write.py
    └── (existing files)

backend/db/
└── schema.sql                 # SQL for Supabase table creation
```

---

### Task 1: Dependencies and Database Schema

**Files:**
- Modify: `requirements.txt`
- Create: `backend/db/schema.sql`

- [ ] **Step 1: Update requirements.txt**

Add to the end of `requirements.txt`:

```
fastapi>=0.115
uvicorn>=0.34
supabase>=2.0
python-jose[cryptography]>=3.3
httpx>=0.27
```

(`httpx` is needed for FastAPI's `TestClient`.)

- [ ] **Step 2: Install dependencies**

Run: `pip install -r requirements.txt`

- [ ] **Step 3: Create SQL schema file**

```sql
-- backend/db/schema.sql
-- Run this in Supabase SQL Editor to create tables.

-- Users table (profile data, linked to Supabase Auth)
create table if not exists users (
  id uuid primary key,  -- matches auth.users.id
  email text not null,
  school text,
  grad_year int,
  skills text[] default '{}',
  bio text,
  github_url text,
  portfolio_url text,
  tier text not null default 'free' check (tier in ('free', 'unlocked', 'paid')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Companies table (populated by pipeline)
create table if not exists companies (
  id serial primary key,
  name text unique not null,
  yc_batch text,
  description text,
  long_description text,
  summary text,
  one_liner text,
  website text,
  industry text,
  stage text,
  stage_detail text,
  technical_level text,
  team_size int,
  need_tags text[] default '{}',
  specific_projects text[] default '{}',
  is_hiring boolean default false,
  status text,
  reachability_score text,
  reachability_probability float,
  founder_name text,
  founder_title text,
  founder_linkedin text,
  founder_twitter text,
  all_locations text,
  tags text[] default '{}',
  industries text[] default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Brief views (tracks which briefs a user has seen, enforces free tier limit)
create table if not exists brief_views (
  id serial primary key,
  user_id uuid not null references users(id) on delete cascade,
  company_id int not null references companies(id) on delete cascade,
  viewed_at timestamptz not null default now(),
  unique(user_id, company_id)
);

-- Outreach log (tracks emails sent and outcomes)
create table if not exists outreach_log (
  id serial primary key,
  user_id uuid not null references users(id) on delete cascade,
  company_id int not null references companies(id) on delete cascade,
  status text not null check (status in ('sent', 'replied', 'meeting', 'no-response')),
  sent_at timestamptz,
  followup_date timestamptz,
  notes text,
  created_at timestamptz not null default now()
);

-- Indexes for common queries
create index if not exists idx_companies_reachability on companies(reachability_probability desc);
create index if not exists idx_companies_industry on companies(industry);
create index if not exists idx_brief_views_user on brief_views(user_id);
create index if not exists idx_outreach_user on outreach_log(user_id);

-- Auto-update updated_at on users
create or replace function update_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create or replace trigger users_updated_at
  before update on users
  for each row execute function update_updated_at();

create or replace trigger companies_updated_at
  before update on companies
  for each row execute function update_updated_at();

-- Enable Row Level Security
alter table users enable row level security;
alter table brief_views enable row level security;
alter table outreach_log enable row level security;

-- RLS policies: users can only read/write their own data
create policy "Users can view own profile" on users for select using (auth.uid() = id);
create policy "Users can update own profile" on users for update using (auth.uid() = id);
create policy "Users can insert own profile" on users for insert with check (auth.uid() = id);

-- Companies are readable by everyone (no auth needed for browsing)
-- No RLS on companies — they're public data

create policy "Users can view own brief_views" on brief_views for select using (auth.uid() = user_id);
create policy "Users can insert own brief_views" on brief_views for insert with check (auth.uid() = user_id);

create policy "Users can view own outreach" on outreach_log for select using (auth.uid() = user_id);
create policy "Users can insert own outreach" on outreach_log for insert with check (auth.uid() = user_id);
create policy "Users can update own outreach" on outreach_log for update using (auth.uid() = user_id);
```

- [ ] **Step 4: Commit**

```bash
git add requirements.txt backend/db/schema.sql
git commit -m "feat: add backend dependencies and Supabase schema"
```

**Note:** The SQL must be run manually in the Supabase SQL Editor before the API can work. This is a one-time setup step.

---

### Task 2: Database Client and Auth Middleware

**Files:**
- Create: `backend/db.py`
- Create: `backend/auth.py`
- Create: `tests/api/__init__.py`
- Create: `tests/api/test_auth.py`

- [ ] **Step 1: Write auth tests**

```python
# tests/api/__init__.py
# (empty)
```

```python
# tests/api/test_auth.py
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from backend.auth import get_current_user, get_optional_user


def test_get_current_user_valid_token():
    mock_request = MagicMock()
    mock_request.headers.get.return_value = "Bearer valid.jwt.token"

    with patch("backend.auth.jwt.decode") as mock_decode:
        mock_decode.return_value = {"sub": "user-uuid-123", "email": "test@example.com"}
        user_id = get_current_user(mock_request)

    assert user_id == "user-uuid-123"
    mock_decode.assert_called_once()


def test_get_current_user_missing_header():
    mock_request = MagicMock()
    mock_request.headers.get.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(mock_request)
    assert exc_info.value.status_code == 401


def test_get_current_user_invalid_token():
    mock_request = MagicMock()
    mock_request.headers.get.return_value = "Bearer bad.token"

    with patch("backend.auth.jwt.decode") as mock_decode:
        mock_decode.side_effect = Exception("Invalid token")
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_request)
    assert exc_info.value.status_code == 401


def test_get_current_user_no_bearer_prefix():
    mock_request = MagicMock()
    mock_request.headers.get.return_value = "just.a.token"

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(mock_request)
    assert exc_info.value.status_code == 401


def test_get_optional_user_valid_token():
    mock_request = MagicMock()
    mock_request.headers.get.return_value = "Bearer valid.jwt.token"

    with patch("backend.auth.jwt.decode") as mock_decode:
        mock_decode.return_value = {"sub": "user-uuid-123", "email": "test@example.com"}
        user_id = get_optional_user(mock_request)

    assert user_id == "user-uuid-123"


def test_get_optional_user_no_token():
    mock_request = MagicMock()
    mock_request.headers.get.return_value = None

    user_id = get_optional_user(mock_request)
    assert user_id is None


def test_get_optional_user_invalid_token():
    mock_request = MagicMock()
    mock_request.headers.get.return_value = "Bearer bad.token"

    with patch("backend.auth.jwt.decode") as mock_decode:
        mock_decode.side_effect = Exception("Invalid token")
        user_id = get_optional_user(mock_request)

    assert user_id is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/api/test_auth.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement db.py**

```python
# backend/db.py
"""Supabase client setup."""

import os
from supabase import create_client, Client


def get_supabase_client() -> Client:
    """Create and return a Supabase client using environment variables."""
    url = os.environ["SUPABASE_URL"]
    key = os.environ.get("SUPABASE_KEY", os.environ.get("SUPABASE_ANON_KEY", ""))
    return create_client(url, key)


# Singleton client — initialized on first import
_client: Client | None = None


def get_db() -> Client:
    """Get the shared Supabase client instance."""
    global _client
    if _client is None:
        _client = get_supabase_client()
    return _client
```

- [ ] **Step 4: Implement auth.py**

```python
# backend/auth.py
"""JWT verification for Supabase Auth tokens."""

import os
from fastapi import Request, HTTPException
from jose import jwt


SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")
JWT_ALGORITHM = "HS256"


def get_current_user(request: Request) -> str:
    """Extract and verify JWT from Authorization header. Returns user ID.

    Raises HTTPException 401 if token is missing or invalid.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = auth_header.split(" ", 1)[1]

    try:
        payload = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return user_id
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_optional_user(request: Request) -> str | None:
    """Extract user ID from JWT if present. Returns None if no valid token.

    Does not raise — used for endpoints with optional auth (e.g., /companies browse).
    """
    try:
        return get_current_user(request)
    except HTTPException:
        return None
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/api/test_auth.py -v`
Expected: 7 passed

- [ ] **Step 6: Commit**

```bash
git add backend/db.py backend/auth.py tests/api/__init__.py tests/api/test_auth.py
git commit -m "feat: add Supabase client and JWT auth middleware"
```

---

### Task 3: Match Scorer

**Files:**
- Create: `backend/matching/__init__.py`
- Create: `backend/matching/scorer.py`
- Create: `tests/matching/__init__.py`
- Create: `tests/matching/test_scorer.py`

- [ ] **Step 1: Write scorer tests**

```python
# tests/matching/__init__.py
# (empty)
```

```python
# tests/matching/test_scorer.py
from backend.matching.scorer import match_score, rank_companies


def test_match_score_full_overlap():
    user_skills = ["python scripting", "react frontend", "data analysis"]
    company_tags = ["python scripting", "react frontend", "data analysis"]
    assert match_score(user_skills, company_tags) == 3


def test_match_score_partial_overlap():
    user_skills = ["python scripting", "react frontend"]
    company_tags = ["python scripting", "data analysis", "graphic design"]
    assert match_score(user_skills, company_tags) == 1


def test_match_score_no_overlap():
    user_skills = ["video editing", "photography"]
    company_tags = ["python scripting", "data analysis"]
    assert match_score(user_skills, company_tags) == 0


def test_match_score_empty_skills():
    assert match_score([], ["python scripting"]) == 0
    assert match_score(["python scripting"], []) == 0
    assert match_score([], []) == 0


def test_rank_companies_with_skills():
    companies = [
        {"id": 1, "name": "LowMatch", "need_tags": ["video editing"], "reachability_probability": 0.9},
        {"id": 2, "name": "HighMatch", "need_tags": ["python scripting", "react frontend"], "reachability_probability": 0.5},
        {"id": 3, "name": "MedMatch", "need_tags": ["python scripting"], "reachability_probability": 0.7},
    ]
    user_skills = ["python scripting", "react frontend"]
    ranked = rank_companies(companies, user_skills)

    # HighMatch has best combined score (2 skill matches + 0.5 reachability)
    assert ranked[0]["name"] == "HighMatch"
    assert "match_score" in ranked[0]


def test_rank_companies_no_skills():
    companies = [
        {"id": 1, "name": "Low", "need_tags": ["x"], "reachability_probability": 0.3},
        {"id": 2, "name": "High", "need_tags": ["y"], "reachability_probability": 0.9},
        {"id": 3, "name": "Med", "need_tags": ["z"], "reachability_probability": 0.6},
    ]
    ranked = rank_companies(companies, user_skills=None)

    # With no skills, rank by reachability only
    assert ranked[0]["name"] == "High"
    assert ranked[1]["name"] == "Med"
    assert ranked[2]["name"] == "Low"


def test_rank_companies_includes_match_score():
    companies = [
        {"id": 1, "name": "Co", "need_tags": ["python scripting", "react frontend"], "reachability_probability": 0.8},
    ]
    ranked = rank_companies(companies, ["python scripting"])

    assert ranked[0]["match_score"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/matching/test_scorer.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement scorer.py**

```python
# backend/matching/__init__.py
# (empty)
```

```python
# backend/matching/scorer.py
"""Match scoring: rank companies by skill overlap + reachability."""

# Weights for combining match score and reachability
REACHABILITY_WEIGHT = 0.4
MATCH_WEIGHT = 0.6
# Max match score for normalization (assumes user picks ~5 skills)
MAX_MATCH_SCORE = 5


def match_score(user_skills: list[str], company_tags: list[str]) -> int:
    """Count overlapping skills between user and company."""
    if not user_skills or not company_tags:
        return 0
    return len(set(user_skills) & set(company_tags))


def rank_companies(
    companies: list[dict],
    user_skills: list[str] | None = None,
) -> list[dict]:
    """Rank companies by combined match + reachability score.

    Each company dict gets a 'match_score' and 'rank_score' field added.
    Returns a new list sorted by rank_score descending.
    """
    scored = []
    for company in companies:
        company_tags = company.get("need_tags", []) or []
        reachability = company.get("reachability_probability", 0.0) or 0.0

        if user_skills:
            ms = match_score(user_skills, company_tags)
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

Run: `python -m pytest tests/matching/test_scorer.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add backend/matching/__init__.py backend/matching/scorer.py tests/matching/__init__.py tests/matching/test_scorer.py
git commit -m "feat: add match scorer — skill overlap + reachability ranking"
```

---

### Task 4: Pydantic Schemas

**Files:**
- Create: `backend/schemas.py`

- [ ] **Step 1: Create schemas**

```python
# backend/schemas.py
"""Pydantic models for API request/response validation."""

from pydantic import BaseModel


# --- Users ---

class UserProfile(BaseModel):
    id: str
    email: str
    school: str | None = None
    grad_year: int | None = None
    skills: list[str] = []
    bio: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    tier: str = "free"


class UserUpdate(BaseModel):
    school: str | None = None
    grad_year: int | None = None
    skills: list[str] | None = None
    bio: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None


# --- Companies ---

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
    need_tags: list[str] = []
    match_score: int = 0
    rank_score: float = 0.0


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
    specific_projects: list[str] = []
    reachability_score: str | None = None
    reachability_probability: float | None = None
    founder_name: str | None = None
    founder_title: str | None = None
    founder_linkedin: str | None = None
    founder_twitter: str | None = None
    all_locations: str | None = None
    tags: list[str] = []
    industries: list[str] = []
    match_score: int = 0


# --- Outreach ---

class OutreachCreate(BaseModel):
    company_id: int
    status: str  # sent, replied, meeting, no-response
    notes: str | None = None
    sent_at: str | None = None  # ISO datetime string


class OutreachUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None


class OutreachEntry(BaseModel):
    id: int
    company_id: int
    company_name: str | None = None
    status: str
    sent_at: str | None = None
    followup_date: str | None = None
    notes: str | None = None
    created_at: str | None = None
```

- [ ] **Step 2: Verify import works**

Run: `python -c "from backend.schemas import UserProfile, CompanyCard, OutreachCreate; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/schemas.py
git commit -m "feat: add Pydantic schemas for API request/response models"
```

---

### Task 5: Users Router

**Files:**
- Create: `backend/routers/__init__.py`
- Create: `backend/routers/users.py`
- Create: `tests/api/test_users.py`

- [ ] **Step 1: Write user endpoint tests**

```python
# tests/api/test_users.py
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test.jwt.token"}


def _mock_auth(user_id="user-uuid-123"):
    """Patch auth to return a fixed user ID."""
    return patch("backend.auth.jwt.decode", return_value={"sub": user_id, "email": "test@school.edu"})


def test_get_me_creates_new_user(client, auth_headers):
    mock_db = MagicMock()
    # First query returns no existing user
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    # Insert returns the new user
    mock_db.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "user-uuid-123", "email": "test@school.edu", "tier": "free", "skills": []}
    ]

    with _mock_auth(), patch("backend.routers.users.get_db", return_value=mock_db):
        response = client.get("/me", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "user-uuid-123"
    assert data["tier"] == "free"


def test_get_me_returns_existing_user(client, auth_headers):
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "user-uuid-123", "email": "test@school.edu", "tier": "paid", "skills": ["python scripting"],
         "school": "MIT", "grad_year": 2028, "bio": None, "github_url": None, "portfolio_url": None}
    ]

    with _mock_auth(), patch("backend.routers.users.get_db", return_value=mock_db):
        response = client.get("/me", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["tier"] == "paid"


def test_get_me_requires_auth(client):
    response = client.get("/me")
    assert response.status_code == 401


def test_put_me_updates_profile(client, auth_headers):
    mock_db = MagicMock()
    mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        {"id": "user-uuid-123", "email": "test@school.edu", "tier": "free",
         "skills": ["python scripting", "react frontend"], "school": "MIT",
         "grad_year": 2028, "bio": "Hi", "github_url": None, "portfolio_url": None}
    ]

    with _mock_auth(), patch("backend.routers.users.get_db", return_value=mock_db):
        response = client.put("/me", headers=auth_headers, json={
            "skills": ["python scripting", "react frontend"],
            "school": "MIT",
            "grad_year": 2028,
            "bio": "Hi",
        })

    assert response.status_code == 200
    assert response.json()["skills"] == ["python scripting", "react frontend"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/api/test_users.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.main'`

- [ ] **Step 3: Create routers/__init__.py**

```python
# backend/routers/__init__.py
# (empty)
```

- [ ] **Step 4: Implement users.py**

```python
# backend/routers/users.py
"""User profile endpoints."""

from fastapi import APIRouter, Depends, Request
from backend.auth import get_current_user
from backend.db import get_db
from backend.schemas import UserProfile, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserProfile)
def get_me(request: Request, user_id: str = Depends(get_current_user)):
    """Get current user profile. Auto-creates on first call."""
    db = get_db()

    # Check if user exists
    result = db.table("users").select("*").eq("id", user_id).execute()

    if result.data:
        return result.data[0]

    # Auto-create bare profile
    email = ""
    try:
        from jose import jwt
        token = request.headers.get("Authorization", "").split(" ", 1)[1]
        payload = jwt.decode(token, options={"verify_signature": False})
        email = payload.get("email", "")
    except Exception:
        pass

    new_user = {"id": user_id, "email": email, "tier": "free", "skills": []}
    result = db.table("users").insert(new_user).execute()
    return result.data[0]


@router.put("/me", response_model=UserProfile)
def update_me(body: UserUpdate, user_id: str = Depends(get_current_user)):
    """Update user profile fields."""
    db = get_db()

    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        # Nothing to update, return current profile
        result = db.table("users").select("*").eq("id", user_id).execute()
        return result.data[0]

    result = db.table("users").update(update_data).eq("id", user_id).execute()
    return result.data[0]
```

- [ ] **Step 5: Create minimal main.py (needed for TestClient)**

```python
# backend/main.py
"""FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import users, companies, outreach

app = FastAPI(title="REACH API", version="0.1.0")

# CORS — allow frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
```

**Note:** This will fail to import `companies` and `outreach` routers since they don't exist yet. Create stub files:

```python
# backend/routers/companies.py
"""Company endpoints (stub — implemented in Task 6)."""

from fastapi import APIRouter

router = APIRouter()
```

```python
# backend/routers/outreach.py
"""Outreach endpoints (stub — implemented in Task 7)."""

from fastapi import APIRouter

router = APIRouter()
```

- [ ] **Step 6: Update main.py to include all routers**

```python
# backend/main.py
"""FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import users, companies, outreach

app = FastAPI(title="REACH API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(companies.router)
app.include_router(outreach.router)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python -m pytest tests/api/test_users.py -v`
Expected: 4 passed

- [ ] **Step 8: Commit**

```bash
git add backend/routers/__init__.py backend/routers/users.py backend/routers/companies.py backend/routers/outreach.py backend/main.py tests/api/test_users.py
git commit -m "feat: add users router with GET/PUT /me and auto-create on first call"
```

---

### Task 6: Companies Router

**Files:**
- Modify: `backend/routers/companies.py`
- Create: `tests/api/test_companies.py`

- [ ] **Step 1: Write company endpoint tests**

```python
# tests/api/test_companies.py
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test.jwt.token"}


def _mock_auth(user_id="user-uuid-123"):
    return patch("backend.auth.jwt.decode", return_value={"sub": user_id, "email": "test@school.edu"})


def _sample_companies():
    return [
        {"id": 1, "name": "AlphaCo", "yc_batch": "Winter 2024", "one_liner": "AI for alpha",
         "industry": "ai-ml", "stage_detail": "growing", "technical_level": "technical",
         "team_size": 5, "reachability_score": "high", "reachability_probability": 0.98,
         "need_tags": ["python scripting", "data analysis"], "status": "Active",
         "description": "Alpha does alpha.", "summary": "Alpha builds AI tools.",
         "website": "https://alpha.com", "stage": "Early", "specific_projects": ["Build dashboard", "Write docs"],
         "is_hiring": False, "founder_name": None, "founder_title": None,
         "founder_linkedin": None, "founder_twitter": None, "all_locations": "SF",
         "tags": ["AI"], "industries": ["AI"], "long_description": "Full description."},
        {"id": 2, "name": "BetaCo", "yc_batch": "Summer 2024", "one_liner": "Design for beta",
         "industry": "consumer", "stage_detail": "building-mvp", "technical_level": "mixed",
         "team_size": 3, "reachability_score": "medium", "reachability_probability": 0.75,
         "need_tags": ["graphic design", "content writing"], "status": "Active",
         "description": "Beta does beta.", "summary": "Beta builds consumer tools.",
         "website": "https://beta.com", "stage": "Early", "specific_projects": ["Design logo", "Write blog"],
         "is_hiring": True, "founder_name": None, "founder_title": None,
         "founder_linkedin": None, "founder_twitter": None, "all_locations": "NYC",
         "tags": ["Consumer"], "industries": ["Consumer"], "long_description": "Full description."},
    ]


def test_get_companies_anonymous(client):
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = _sample_companies()

    with patch("backend.routers.companies.get_db", return_value=mock_db):
        response = client.get("/companies")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Sorted by reachability when no auth
    assert data[0]["name"] == "AlphaCo"


def test_get_companies_with_auth_ranked(client, auth_headers):
    mock_db = MagicMock()
    # Companies query
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = _sample_companies()

    # User query (has graphic design skill — should boost BetaCo)
    user_data = [{"id": "user-uuid-123", "skills": ["graphic design", "content writing"]}]

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "companies":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = _sample_companies()
        elif table_name == "users":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = user_data
        return mock_table

    mock_db.table.side_effect = table_side_effect

    with _mock_auth(), patch("backend.routers.companies.get_db", return_value=mock_db):
        response = client.get("/companies", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # BetaCo should rank higher due to skill match
    assert data[0]["name"] == "BetaCo"


def test_get_companies_filter_by_industry(client):
    mock_db = MagicMock()
    # Only return ai-ml companies when filtered
    filtered = [c for c in _sample_companies() if c["industry"] == "ai-ml"]
    mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = filtered
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = filtered

    with patch("backend.routers.companies.get_db", return_value=mock_db):
        response = client.get("/companies?industry=ai-ml")

    assert response.status_code == 200


def test_get_company_brief_requires_auth(client):
    response = client.get("/companies/1")
    assert response.status_code == 401


def test_get_company_brief_success(client, auth_headers):
    mock_db = MagicMock()

    company = _sample_companies()[0]
    user_data = [{"id": "user-uuid-123", "skills": ["python scripting"], "tier": "paid"}]
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
    assert response.json()["name"] == "AlphaCo"


def test_get_company_brief_free_tier_limit(client, auth_headers):
    mock_db = MagicMock()

    company = _sample_companies()[0]
    user_data = [{"id": "user-uuid-123", "skills": [], "tier": "free"}]
    # Already viewed 3 different companies
    existing_views = [
        {"user_id": "user-uuid-123", "company_id": 10},
        {"user_id": "user-uuid-123", "company_id": 20},
        {"user_id": "user-uuid-123", "company_id": 30},
    ]

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "companies":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [company]
        elif table_name == "users":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = user_data
        elif table_name == "brief_views":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = existing_views
        return mock_table

    mock_db.table.side_effect = table_side_effect

    with _mock_auth(), patch("backend.routers.companies.get_db", return_value=mock_db):
        response = client.get("/companies/1", headers=auth_headers)

    assert response.status_code == 403
    assert "upgrade" in response.json()["detail"].lower() or "limit" in response.json()["detail"].lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/api/test_companies.py -v`
Expected: FAIL — endpoints return 404 (stub router)

- [ ] **Step 3: Implement companies.py**

```python
# backend/routers/companies.py
"""Company browsing and brief endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from backend.auth import get_current_user, get_optional_user
from backend.db import get_db
from backend.matching.scorer import rank_companies, match_score
from backend.schemas import CompanyCard, CompanyBrief

router = APIRouter()

FREE_BRIEF_LIMIT = 3


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

    # Build query
    query = db.table("companies").select("*").eq("status", "Active")

    if industry:
        query = query.eq("industry", industry)
    if reachability:
        query = query.eq("reachability_score", reachability)

    result = query.execute()
    companies = result.data

    # Get user skills if authenticated
    user_skills = None
    if user_id:
        user_result = db.table("users").select("skills").eq("id", user_id).execute()
        if user_result.data and user_result.data[0].get("skills"):
            user_skills = user_result.data[0]["skills"]

    # Rank and paginate
    ranked = rank_companies(companies, user_skills)
    start = (page - 1) * limit
    return ranked[start:start + limit]


@router.get("/companies/{company_id}", response_model=CompanyBrief)
def get_brief(
    company_id: int,
    request: Request,
    user_id: str = Depends(get_current_user),
):
    """Get full company brief. Gated by tier for free users."""
    db = get_db()

    # Get company
    result = db.table("companies").select("*").eq("id", company_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Company not found")
    company = result.data[0]

    # Get user for tier check
    user_result = db.table("users").select("skills, tier").eq("id", user_id).execute()
    user = user_result.data[0] if user_result.data else {"skills": [], "tier": "free"}

    # Check brief limit for free tier
    if user["tier"] == "free":
        views_result = db.table("brief_views").select("company_id").eq("user_id", user_id).execute()
        viewed_ids = [v["company_id"] for v in views_result.data]

        if company_id not in viewed_ids and len(viewed_ids) >= FREE_BRIEF_LIMIT:
            raise HTTPException(status_code=403, detail="Free tier limit reached. Upgrade to unlock more briefs.")

    # Record the view (ignore if already exists due to unique constraint)
    try:
        db.table("brief_views").insert({"user_id": user_id, "company_id": company_id}).execute()
    except Exception:
        pass  # Already viewed — unique constraint prevents duplicate

    # Add match score
    user_skills = user.get("skills", []) or []
    ms = match_score(user_skills, company.get("need_tags", []) or [])
    company["match_score"] = ms

    return company
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/api/test_companies.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add backend/routers/companies.py tests/api/test_companies.py
git commit -m "feat: add companies router with browse, ranking, and brief gating"
```

---

### Task 7: Outreach Router

**Files:**
- Modify: `backend/routers/outreach.py`
- Create: `tests/api/test_outreach.py`

- [ ] **Step 1: Write outreach endpoint tests**

```python
# tests/api/test_outreach.py
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test.jwt.token"}


def _mock_auth(user_id="user-uuid-123"):
    return patch("backend.auth.jwt.decode", return_value={"sub": user_id, "email": "test@school.edu"})


def test_get_outreach(client, auth_headers):
    mock_db = MagicMock()
    outreach_data = [
        {"id": 1, "user_id": "user-uuid-123", "company_id": 1, "status": "sent",
         "sent_at": "2026-05-20T10:00:00Z", "followup_date": "2026-05-25T10:00:00Z",
         "notes": "Sent cold email", "created_at": "2026-05-20T10:00:00Z"},
    ]
    company_data = [{"id": 1, "name": "AlphaCo"}]

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "outreach_log":
            mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = outreach_data
        elif table_name == "companies":
            mock_table.select.return_value.in_.return_value.execute.return_value.data = company_data
        return mock_table

    mock_db.table.side_effect = table_side_effect

    with _mock_auth(), patch("backend.routers.outreach.get_db", return_value=mock_db):
        response = client.get("/outreach", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "sent"
    assert data[0]["company_name"] == "AlphaCo"


def test_post_outreach(client, auth_headers):
    mock_db = MagicMock()
    mock_db.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": 1, "user_id": "user-uuid-123", "company_id": 1, "status": "sent",
         "sent_at": "2026-05-20T10:00:00Z", "followup_date": "2026-05-25T10:00:00Z",
         "notes": None, "created_at": "2026-05-20T10:00:00Z"}
    ]

    with _mock_auth(), patch("backend.routers.outreach.get_db", return_value=mock_db):
        response = client.post("/outreach", headers=auth_headers, json={
            "company_id": 1,
            "status": "sent",
            "sent_at": "2026-05-20T10:00:00Z",
        })

    assert response.status_code == 201
    assert response.json()["status"] == "sent"


def test_put_outreach(client, auth_headers):
    mock_db = MagicMock()

    # Verify ownership
    mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        {"id": 1, "user_id": "user-uuid-123"}
    ]
    # Update
    mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        {"id": 1, "user_id": "user-uuid-123", "company_id": 1, "status": "replied",
         "sent_at": "2026-05-20T10:00:00Z", "followup_date": "2026-05-25T10:00:00Z",
         "notes": "Got a reply!", "created_at": "2026-05-20T10:00:00Z"}
    ]

    with _mock_auth(), patch("backend.routers.outreach.get_db", return_value=mock_db):
        response = client.put("/outreach/1", headers=auth_headers, json={
            "status": "replied",
            "notes": "Got a reply!",
        })

    assert response.status_code == 200
    assert response.json()["status"] == "replied"


def test_outreach_requires_auth(client):
    assert client.get("/outreach").status_code == 401
    assert client.post("/outreach", json={"company_id": 1, "status": "sent"}).status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/api/test_outreach.py -v`
Expected: FAIL — endpoints return 404/422 (stub router)

- [ ] **Step 3: Implement outreach.py**

```python
# backend/routers/outreach.py
"""Outreach tracking endpoints."""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from backend.auth import get_current_user
from backend.db import get_db
from backend.schemas import OutreachCreate, OutreachUpdate, OutreachEntry

router = APIRouter()

FOLLOWUP_DAYS = 5


@router.get("/outreach", response_model=list[OutreachEntry])
def list_outreach(user_id: str = Depends(get_current_user)):
    """List user's outreach log with company names."""
    db = get_db()

    result = db.table("outreach_log").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
    entries = result.data

    if not entries:
        return []

    # Fetch company names for display
    company_ids = list({e["company_id"] for e in entries})
    companies_result = db.table("companies").select("id, name").in_("id", company_ids).execute()
    name_map = {c["id"]: c["name"] for c in companies_result.data}

    for entry in entries:
        entry["company_name"] = name_map.get(entry["company_id"])

    return entries


@router.post("/outreach", response_model=OutreachEntry, status_code=201)
def create_outreach(body: OutreachCreate, user_id: str = Depends(get_current_user)):
    """Log a new outreach entry."""
    db = get_db()

    record = {
        "user_id": user_id,
        "company_id": body.company_id,
        "status": body.status,
        "notes": body.notes,
        "sent_at": body.sent_at,
    }

    # Compute followup date if sent_at is provided
    if body.sent_at:
        try:
            sent_dt = datetime.fromisoformat(body.sent_at.replace("Z", "+00:00"))
            record["followup_date"] = (sent_dt + timedelta(days=FOLLOWUP_DAYS)).isoformat()
        except ValueError:
            pass

    result = db.table("outreach_log").insert(record).execute()
    return result.data[0]


@router.put("/outreach/{outreach_id}", response_model=OutreachEntry)
def update_outreach(outreach_id: int, body: OutreachUpdate, user_id: str = Depends(get_current_user)):
    """Update an outreach entry's status or notes."""
    db = get_db()

    # Verify ownership
    check = db.table("outreach_log").select("id").eq("id", outreach_id).eq("user_id", user_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Outreach entry not found")

    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Nothing to update")

    result = db.table("outreach_log").update(update_data).eq("id", outreach_id).execute()
    return result.data[0]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/api/test_outreach.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/routers/outreach.py tests/api/test_outreach.py
git commit -m "feat: add outreach router — log, list, and update outreach entries"
```

---

### Task 8: Supabase Write Pipeline Step

**Files:**
- Create: `backend/pipeline/supabase_write.py`
- Create: `tests/pipeline/test_supabase_write.py`

- [ ] **Step 1: Write supabase_write tests**

```python
# tests/pipeline/test_supabase_write.py
import json
import pytest
from unittest.mock import patch, MagicMock

from backend.pipeline.supabase_write import merge_company_data, upload_to_supabase


def test_merge_company_data():
    enriched = [
        {"name": "AlphaCo", "batch": "W24", "summary": "Alpha does things.", "one_liner": "Alpha tools",
         "need_tags": ["python"], "industry": "ai-ml", "technical_level": "technical",
         "stage_detail": "growing", "specific_projects": ["Build dashboard", "Write docs"],
         "description": "Alpha.", "long_description": "Full alpha.", "tags": ["AI"],
         "industries": ["AI"], "website": "https://alpha.com", "team_size": 5,
         "stage": "Early", "status": "Active", "is_hiring": False, "all_locations": "SF"},
    ]
    scores = [
        {"name": "AlphaCo", "reachability_score": "high", "reachability_probability": 0.98},
    ]

    merged = merge_company_data(enriched, scores)

    assert len(merged) == 1
    assert merged[0]["name"] == "AlphaCo"
    assert merged[0]["summary"] == "Alpha does things."
    assert merged[0]["reachability_score"] == "high"
    assert merged[0]["reachability_probability"] == 0.98


def test_merge_company_data_missing_score():
    enriched = [
        {"name": "NoCo", "batch": "W24", "summary": "No score.", "one_liner": "No",
         "need_tags": [], "industry": "other", "technical_level": "mixed",
         "stage_detail": "building-mvp", "specific_projects": ["A", "B"],
         "description": "No.", "long_description": "", "tags": [],
         "industries": [], "website": "", "team_size": None,
         "stage": "", "status": "Active", "is_hiring": False, "all_locations": ""},
    ]
    scores = []

    merged = merge_company_data(enriched, scores)
    assert merged[0]["reachability_score"] == "low"
    assert merged[0]["reachability_probability"] == 0.0


def test_upload_to_supabase():
    companies = [
        {"name": "AlphaCo", "yc_batch": "W24", "summary": "Test.",
         "reachability_score": "high", "reachability_probability": 0.98},
    ]

    mock_db = MagicMock()
    mock_db.table.return_value.upsert.return_value.execute.return_value.data = companies

    with patch("backend.pipeline.supabase_write.get_supabase_client", return_value=mock_db):
        upload_to_supabase(companies)

    mock_db.table.assert_called_with("companies")
    mock_db.table.return_value.upsert.assert_called_once()


def test_full_pipeline_writes(tmp_path):
    from backend.pipeline.supabase_write import write_to_supabase

    enriched = [
        {"name": "TestCo", "batch": "W24", "summary": "Test.", "one_liner": "Test",
         "need_tags": ["python"], "industry": "ai-ml", "technical_level": "technical",
         "stage_detail": "growing", "specific_projects": ["A", "B"],
         "description": "Test.", "long_description": "Full test.", "tags": ["AI"],
         "industries": ["AI"], "website": "https://test.com", "team_size": 3,
         "stage": "Early", "status": "Active", "is_hiring": False, "all_locations": "SF"},
    ]
    scores = [
        {"name": "TestCo", "reachability_score": "high", "reachability_probability": 0.95},
    ]

    enriched_path = tmp_path / "enriched.json"
    enriched_path.write_text(json.dumps(enriched))
    scores_path = tmp_path / "scores.json"
    scores_path.write_text(json.dumps(scores))

    mock_db = MagicMock()
    mock_db.table.return_value.upsert.return_value.execute.return_value.data = []

    with patch("backend.pipeline.supabase_write.get_supabase_client", return_value=mock_db):
        write_to_supabase(
            enriched_path=str(enriched_path),
            scores_path=str(scores_path),
        )

    mock_db.table.return_value.upsert.assert_called_once()
    call_args = mock_db.table.return_value.upsert.call_args[0][0]
    assert len(call_args) == 1
    assert call_args[0]["name"] == "TestCo"
    assert call_args[0]["reachability_score"] == "high"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/pipeline/test_supabase_write.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement supabase_write.py**

```python
# backend/pipeline/supabase_write.py
"""Upload enriched company data to Supabase."""

import json
import os

from backend.db import get_supabase_client
from backend.pipeline.enrich_config import ENRICHED_OUTPUT_PATH
from backend.ml.config import SCORES_OUTPUT_PATH

# Batch size for upserts (Supabase has a row limit per request)
UPSERT_BATCH_SIZE = 500

# Columns to upload (must match schema.sql)
COMPANY_COLUMNS = [
    "name", "yc_batch", "description", "long_description", "summary", "one_liner",
    "website", "industry", "stage", "stage_detail", "technical_level", "team_size",
    "need_tags", "specific_projects", "is_hiring", "status", "reachability_score",
    "reachability_probability", "all_locations", "tags", "industries",
]


def merge_company_data(enriched: list[dict], scores: list[dict]) -> list[dict]:
    """Merge enriched company data with reachability scores."""
    score_map = {s["name"]: s for s in scores}

    merged = []
    for company in enriched:
        score_data = score_map.get(company["name"], {})

        record = {}
        for col in COMPANY_COLUMNS:
            if col in company:
                record[col] = company[col]
            elif col in score_data:
                record[col] = score_data[col]

        # Map 'batch' field name to 'yc_batch'
        if "yc_batch" not in record and "batch" in company:
            record["yc_batch"] = company["batch"]

        # Default reachability if missing
        record.setdefault("reachability_score", "low")
        record.setdefault("reachability_probability", 0.0)

        merged.append(record)

    return merged


def upload_to_supabase(companies: list[dict]):
    """Upsert companies to Supabase in batches."""
    db = get_supabase_client()

    for i in range(0, len(companies), UPSERT_BATCH_SIZE):
        batch = companies[i:i + UPSERT_BATCH_SIZE]
        db.table("companies").upsert(batch, on_conflict="name").execute()
        print(f"[INFO] Upserted batch {i // UPSERT_BATCH_SIZE + 1} ({len(batch)} companies)")


def write_to_supabase(
    enriched_path: str = ENRICHED_OUTPUT_PATH,
    scores_path: str = SCORES_OUTPUT_PATH,
):
    """Full pipeline step: read files, merge, upload."""
    with open(enriched_path) as f:
        enriched = json.load(f)

    with open(scores_path) as f:
        scores = json.load(f)

    print(f"[INFO] Loaded {len(enriched)} enriched, {len(scores)} scores")

    merged = merge_company_data(enriched, scores)
    print(f"[INFO] Merged {len(merged)} companies")

    upload_to_supabase(merged)
    print(f"[DONE] Uploaded {len(merged)} companies to Supabase")


if __name__ == "__main__":
    write_to_supabase()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/pipeline/test_supabase_write.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/supabase_write.py tests/pipeline/test_supabase_write.py
git commit -m "feat: add supabase_write pipeline step — merge and upsert company data"
```

---

### Task 9: Full Test Suite Verification

**Files:**
- No new files

- [ ] **Step 1: Verify all imports work**

Run: `python -c "from backend.main import app; from backend.pipeline.supabase_write import write_to_supabase; print('OK')"`
Expected: `OK`

- [ ] **Step 2: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: All tests pass (existing ML/pipeline tests + new API/matching tests)

- [ ] **Step 3: Test the server starts**

Run: `SUPABASE_URL=http://fake SUPABASE_ANON_KEY=fake SUPABASE_JWT_SECRET=fake uvicorn backend.main:app --host 0.0.0.0 --port 8000 &`
Run: `curl http://localhost:8000/health`
Expected: `{"status":"ok"}`
Run: `kill %1`

- [ ] **Step 4: Commit any remaining changes**

```bash
git add -A
git commit -m "chore: verify full test suite and server startup"
```

---

## Running the Backend

After implementation:

```bash
# Set environment variables
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_ANON_KEY="your-anon-key"
export SUPABASE_KEY="your-service-role-key"
export SUPABASE_JWT_SECRET="your-jwt-secret"

# Run the SQL schema in Supabase SQL Editor (one-time)
# Copy backend/db/schema.sql → paste in Supabase dashboard

# Upload data to Supabase
python -m backend.pipeline.supabase_write

# Start the server
uvicorn backend.main:app --reload --port 8000

# Test it
curl http://localhost:8000/health
curl http://localhost:8000/companies
```
