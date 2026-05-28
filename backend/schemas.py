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
    interests: list[str] = []
    location: str | None = None
    bio: str | None = None
    projects: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    resume_url: str | None = None
    tier: str = "free"


class UserUpdate(BaseModel):
    school: str | None = None
    grad_year: int | None = None
    skills: list[str] | None = None
    interests: list[str] | None = None
    location: str | None = None
    bio: str | None = None
    projects: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    resume_url: str | None = None


# --- Guidance ---

class Guidance(BaseModel):
    your_angle: str
    reference_this: str
    dont_say: str
    your_ask: str


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
    small_logo_url: str | None = None
    founder_name: str | None = None
    founder_title: str | None = None
    founder_avatar_url: str | None = None
    founder_email: str | None = None
    email_confidence: str | None = None
    has_email: bool = False
    need_tags: list[str] = []
    capability_tags: list[str] = []
    yc_tags: list[str] = []
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
    capability_tags: list[str] = []
    yc_tags: list[str] = []
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
    founder_bio: str | None = None
    email_confidence: str | None = None
    has_email: bool = False
    small_logo_url: str | None = None
    slug: str | None = None
    all_locations: str | None = None
    tags: list[str] = []
    industries: list[str] = []
    match_score: int = 0
    guidance: Guidance | None = None


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


# --- Email ---

class EmailGenerate(BaseModel):
    company_id: int
    tone: Literal["curious", "friendly"] = "curious"


class EmailDraft(BaseModel):
    draft: str
    tone: str
    company_id: int
    company_name: str
    founder_name: str | None = None


class EmailSend(BaseModel):
    company_id: int
    subject_line: str
    final_text: str
    original_draft: str
    tone: str = "curious"


class EmailLogEntry(BaseModel):
    id: int
    company_id: int
    original_draft: str
    final_text: str | None = None
    subject_line: str | None = None
    tone: str
    status: str
    sent_at: str | None = None
    reply_detected_at: str | None = None
    created_at: str | None = None


class GmailStatus(BaseModel):
    connected: bool
    gmail_email: str | None = None
