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
