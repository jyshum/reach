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
