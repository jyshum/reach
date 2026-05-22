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
