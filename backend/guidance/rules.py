"""Composable outreach guidance rules engine.

Generates personalized guidance by combining three rule layers:
skill-type, stage, and industry cluster. Templates use slot-filling
from enriched company data.
"""

from backend.schemas import Guidance

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
