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
  need_tags: string[];
  match_score: number;
  rank_score: number;
}

export interface Guidance {
  your_angle: string;
  reference_this: string;
  dont_say: string;
  your_ask: string;
}

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
  specific_projects: string[];
  reachability_score: string | null;
  reachability_probability: number | null;
  founder_name: string | null;
  founder_title: string | null;
  founder_linkedin: string | null;
  founder_twitter: string | null;
  all_locations: string | null;
  tags: string[];
  industries: string[];
  match_score: number;
  guidance: Guidance | null;
}

export interface UserProfile {
  id: string;
  email: string;
  school: string | null;
  grad_year: number | null;
  skills: string[];
  bio: string | null;
  github_url: string | null;
  portfolio_url: string | null;
  tier: string;
}

export interface OutreachEntry {
  id: number;
  company_id: number;
  company_name: string | null;
  status: "sent" | "replied" | "meeting" | "no-response";
  sent_at: string | null;
  followup_date: string | null;
  notes: string | null;
  created_at: string | null;
}

export const INDUSTRIES = [
  "fintech",
  "healthcare",
  "biotech",
  "developer-tools",
  "ai-ml",
  "education",
  "e-commerce",
  "logistics",
  "real-estate",
  "legal",
  "security",
  "enterprise-saas",
  "consumer",
  "media",
  "hardware",
  "climate",
  "aerospace",
  "gaming",
  "food-beverage",
  "manufacturing",
  "travel",
  "hr-recruiting",
  "insurance",
  "construction",
  "agriculture",
  "transportation",
  "government",
  "social-impact",
  "energy",
  "other",
] as const;
