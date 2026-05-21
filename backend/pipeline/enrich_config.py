"""LLM enrichment configuration — prompts, model settings, constants."""

import os

_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")

RAW_DATA_PATH = os.path.join(_ROOT, "data", "raw_companies.json")
ENRICHED_OUTPUT_PATH = os.path.join(_ROOT, "data", "enriched_companies.json")
FAILURES_OUTPUT_PATH = os.path.join(_ROOT, "data", "enrichment_failures.json")
VOCAB_OUTPUT_PATH = os.path.join(_ROOT, "data", "skill_vocabulary.json")

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3:4b"
OLLAMA_TEMPERATURE = 0.3
OLLAMA_NUM_PREDICT = 512

MAX_RETRIES = 2
SAVE_EVERY = 50

INDUSTRY_LIST = [
    "fintech", "healthcare", "biotech", "developer-tools", "ai-ml",
    "education", "e-commerce", "logistics", "real-estate", "legal",
    "security", "enterprise-saas", "consumer", "media", "hardware",
    "climate", "aerospace", "gaming", "food-beverage", "manufacturing",
    "travel", "hr-recruiting", "insurance", "construction", "agriculture",
    "transportation", "government", "social-impact", "energy", "other",
]

VALID_TECHNICAL_LEVELS = ["technical", "mixed", "non-technical"]
VALID_STAGE_DETAILS = ["building-mvp", "launched", "growing", "scaling"]

SYSTEM_PROMPT = (
    "You are a startup analyst. Given a YC startup's data, extract structured information.\n"
    "You MUST respond with valid JSON only. No commentary, no markdown, no explanation."
)

_FEW_SHOT_EXAMPLES = """
Example 1:
Company: Pando Bioscience
Batch: Winter 2023
Short description: Gen-AI Designed Enzymes for Pharmaceutical Innovation
Full description: Pando is an AI-driven synthetic biology company revolutionizing enzyme engineering for the pharmaceutical industry. Our ultra-high-throughput screening platform screens 1000-fold more enzymes 75% faster and 80% cheaper than traditional methods.
Tags: ['Generative AI', 'Synthetic Biology', 'Biotech', 'Diagnostics']
Industries: ['Healthcare', 'Industrial Bio']
Team size: 5
Stage: Early

Response:
{"summary": "Pando uses AI to design custom enzymes for pharmaceutical companies. Their screening platform tests thousands of enzyme variants faster and cheaper than traditional methods.", "one_liner": "AI enzyme design for pharma", "need_tags": ["Python scripting", "data visualization", "scientific writing", "web design", "lab data analysis"], "industry": "biotech", "technical_level": "technical", "stage_detail": "growing", "specific_projects": ["Build a dashboard to visualize enzyme screening results across experiments", "Write case studies explaining how their platform reduces drug manufacturing costs"]}

Example 2:
Company: BrightPath
Batch: Summer 2024
Short description: College admissions counseling for first-gen students
Full description: BrightPath provides affordable, AI-assisted college counseling to first-generation college students. We pair students with mentors and use AI to help them craft compelling applications.
Tags: ['Education', 'Consumer', 'AI']
Industries: ['Education']
Team size: 3
Stage: Early

Response:
{"summary": "BrightPath offers affordable college counseling for first-generation students. They combine AI-assisted application tools with human mentors to help students craft strong applications.", "one_liner": "College counseling for first-gen students", "need_tags": ["React frontend", "content writing", "social media marketing", "UX research", "graphic design"], "industry": "education", "technical_level": "mixed", "stage_detail": "building-mvp", "specific_projects": ["Design and build a student onboarding flow that collects academic background and goals", "Create social media content showcasing first-gen student success stories"]}
"""

_PROMPT_TEMPLATE = """{few_shot}

Now analyze this company:
Company: {name}
Batch: {batch}
Short description: {description}
Full description: {long_description}
Tags: {tags}
Industries: {industries}
Team size: {team_size}
Stage: {stage}

Return this exact JSON structure:
{{"summary": "2 sentences. What they build and why it matters. Plain English, no jargon.", "one_liner": "10 words max. Format: '[thing] for [audience]'", "need_tags": ["3-5 specific skills a student intern could help with. Be specific — not 'coding' but 'Python scripting' or 'React frontend'. Base this ONLY on what the descriptions tell you about the product."], "industry": "one of: {industry_list}", "technical_level": "technical | mixed | non-technical", "stage_detail": "building-mvp | launched | growing | scaling", "specific_projects": ["exactly 2 concrete tasks a student could offer to do for this company. Be specific to what this company builds — not generic. Each should be one sentence."]}}"""


def build_prompt(company: dict) -> str:
    """Build the user prompt for a single company."""
    def safe(val):
        """Escape braces in company data to prevent str.format() errors."""
        return str(val).replace("{", "{{").replace("}", "}}")

    return _PROMPT_TEMPLATE.format(
        few_shot=_FEW_SHOT_EXAMPLES,
        name=safe(company.get("name", "")),
        batch=safe(company.get("batch", "")),
        description=safe(company.get("description", "")),
        long_description=safe(company.get("long_description", "")),
        tags=safe(company.get("tags", [])),
        industries=safe(company.get("industries", [])),
        team_size=safe(company.get("team_size", "Unknown")),
        stage=safe(company.get("stage", "")),
        industry_list=", ".join(INDUSTRY_LIST),
    )
