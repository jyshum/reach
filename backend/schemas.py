"""Pydantic models for API request/response validation."""

from typing import Literal

from pydantic import BaseModel

OUTREACH_STATUSES = Literal["sent", "replied", "meeting", "no-response"]


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
    status: OUTREACH_STATUSES
    notes: str | None = None
    sent_at: str | None = None  # ISO datetime string


class OutreachUpdate(BaseModel):
    status: OUTREACH_STATUSES | None = None
    notes: str | None = None


class OutreachEntry(BaseModel):
    id: int
    company_id: int
    company_name: str | None = None
    status: OUTREACH_STATUSES
    sent_at: str | None = None
    followup_date: str | None = None
    notes: str | None = None
    created_at: str | None = None
