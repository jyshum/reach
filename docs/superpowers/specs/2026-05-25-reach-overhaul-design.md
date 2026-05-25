# REACH Overhaul — Design Spec

Three interconnected redesigns: reachability scoring, capability matching, and email pipeline.

---

## 1. Reachability — Rule-Based Scoring

### Problem

The current XGBoost model learns "small team + recent batch = reachable," which is a heuristic, not ML. 92% of companies are "technical," batch recency is unreliable, and the model gives most similar-looking startups a "high" score — which means the label differentiates nothing.

### Design

Replace ML with a transparent, weighted rule-based score. Five factors:

| Factor | Weight | Logic |
|--------|--------|-------|
| Team size (1-5) | 0.30 | Founder is hands-on, needs help directly |
| Stage = building-mvp | 0.25 | Early-stage founders are desperate for contributors |
| Is hiring | 0.20 | Actively seeking people signals openness |
| Location proximity | 0.15 | Same city/region as student, boost score |
| Has LinkedIn or Twitter | 0.10 | Contactable via public channels |

Score computed as a 0-1 float, bucketed into high/medium/low for display. Weights are starting values — can be tuned later based on real outcome data from the email pipeline (Section 3).

### Location

- Student sets their city/region during onboarding (dropdown or free text, geocoded to a region)
- Founder locations come from `all_locations` field in companies table (already scraped)
- Proximity = same metro area or state. Binary match, not distance-based. Keep it simple.

### What to remove

- `backend/ml/` directory: `features.py`, `train.py`, `predict.py`, `labeling.py`, `config.py`, artifacts
- `reachability_probability` field becomes the rule-based float score
- `reachability_score` remains as the high/medium/low bucket
- Thresholds: high >= 0.70, medium >= 0.40, low < 0.40 (adjusted from ML thresholds since rule-based scores distribute differently)

### What to add

- `backend/scoring/reachability.py` — computes the rule-based score per company, given student location
- Location field on user profile: `city` or `region` (string)
- Onboarding step for location selection

### Explainability

The brief page should show *why* a founder is rated high. Example: "Small team (3 people), building MVP, in San Francisco." This replaces the opaque ML score. Implementation detail: the scoring function returns both the score and a list of contributing factor labels.

---

## 2. Capability Matching — Two-Tier System

### Problem

Current `need_tags` have 3,128 unique values. 92% appear 1-3 times (noise). "Python scripting" appears on 63% of companies (meaningless). The LLM enrichment produced over-specific one-off tags ("Lunar regolith processing") alongside generic fillers. Match scores are effectively random.

### Design

Replace free-form tags with a fixed two-tier capability vocabulary.

**Tier 1 — Broad categories (student picks 1-2):**

1. Engineering (Software)
2. Data & ML
3. Design & UX
4. Content & Research
5. Business & Ops

**Tier 2 — Specific capabilities (student picks up to 3 total across selected categories):**

Engineering:
- Frontend development
- Backend / APIs
- Mobile development
- DevOps / Infrastructure
- Systems programming

Data & ML:
- Deep learning / neural networks
- NLP / language models
- Computer vision
- Data pipelines / engineering
- Analytics / visualization
- ML ops / model deployment

Design & UX:
- UI design
- UX research
- Product design

Content & Research:
- Technical writing
- Market research
- Scientific writing

Business & Ops:
- Sales / outreach
- Operations / process
- Financial analysis
- Growth / marketing

Total: 5 tier-1 categories, 20 tier-2 capabilities.

### Student profile

- Pick 1-2 tier-1 categories (hard limit)
- Pick up to 3 tier-2 capabilities within selected categories (hard limit)
- Can change anytime from profile page
- Onboarding flow: big buttons for tier-1, then sub-options appear for selected categories with a "2 of 3 selected" counter

### Company re-enrichment

Re-run the LLM enrichment pipeline with a constrained vocabulary. The prompt tells the LLM: "Given this company's description and projects, select 2-4 capabilities from this exact list: [the 20 tier-2 options]." No free-form generation.

- New field: `capability_tags: text[]` (replaces `need_tags` for matching purposes)
- Keep `need_tags` in the database for reference but stop using them in ranking
- Each company gets 2-4 tier-2 tags from the fixed set

### Matching

Match score = count of overlapping tier-2 capabilities between student (max 3) and company (2-4).

Range: 0-3. Four meaningful tiers of relevance:
- 3/3: strong match, top of feed
- 2/3: good match
- 1/3: partial match
- 0/3: no capability overlap, ranked by reachability only

Updated ranking formula:
```
rank_score = 0.4 * reachability_float + 0.6 * (match_count / 3)
```

Where `reachability_float` is the 0-1 rule-based score (stored as `reachability_probability`), not the high/medium/low label. Same weights as current system, but match_count is now 0-3 instead of 0-5.

### Guidance system impact

`rules.py` already classifies students into 6 types (developer, designer, data, writer, business, operations). This maps directly to tier-1 categories. The guidance system can use tier-2 picks for more specific angle generation. No major rewrite needed — the guidance inputs get better for free.

---

## 3. Email Pipeline — Phased Build

### Problem

REACH has an EmailWorkspace and guidance system but no actual email sending, no outcome tracking, and no data to train on. The guidance is template-level advice ("Lead with something you've built"), not a generated email. Naive LLM email generation produces robotic, obviously-AI text that founders discard instantly.

### Phase 0 — Validation ($0.50, 1 week)

Before building anything, validate that LLM-generated drafts produce replies.

**Experiment:**
1. Pick 10 companies from the database — mix of stages, industries, sizes
2. Create 2-3 student profiles matching real backgrounds
3. Write the prompt template intended for production
4. Generate 10 AI-assisted emails (generate draft, edit by hand, send from personal inbox)
5. Write 10 fully human-written emails to 10 *different* founders (same profile types, same company types)
6. Send all 20. Wait 7 days. Count replies.

**Decision gate:**
- AI replies >= human replies → proceed to Phase 1
- AI replies significantly worse → rework prompt engineering, re-test
- Zero replies on both → the problem might not be generation quality (could be targeting, subject lines, etc.)

Can also test with local Ollama (Qwen3:4b, free) vs Claude API to compare quality tiers.

### Phase 1 — Gmail Integration + Generation

**Gmail OAuth:**
- OAuth scopes: `gmail.send`, `gmail.readonly`
- Student connects during onboarding or on first "Write email" click
- Tokens stored server-side (encrypted), refreshed automatically
- Submit Google verification request immediately — while unverified, limited to 100 manually-added test users (sufficient for early launch)
- Required: privacy policy page, terms of service page on the REACH domain

**Email generation:**
- Prompt-engineered, not fine-tuned. Uses Claude API (or local Ollama as fallback).
- Inputs: student bio, tier-2 capability picks, student's listed projects, company specific_projects, guidance rules (your_angle, reference_this, dont_say, your_ask), company summary
- Prompt constraints: max 4-5 sentences, sound like a student not a professional, include one specific hook about the company, end with a concrete low-commitment ask, no filler enthusiasm ("I'm excited about...")
- Output: draft displayed in EmailWorkspace

**Student edit + send flow:**
1. Student clicks "Generate draft" on a founder brief
2. Draft appears in EmailWorkspace (editable textarea)
3. Student modifies the draft (required — cannot send unedited)
4. Student clicks "Send" → Gmail API sends from their account
5. Confirmation shown, outreach tracker updated automatically

**Data stored at send time:**
- `email_text` (final version, post-edit)
- `original_draft` (pre-edit, for computing edit distance)
- `student_id`, `company_id`
- `subject_line`
- `sent_at` timestamp
- `gmail_thread_id` (for monitoring)

**Thread monitoring:**
- Background job polls Gmail API every 4 hours per active thread
- Checks for new messages in the thread (gmail.readonly)
- If reply detected: update outreach entry status to "replied", store `reply_at` timestamp
- 7-day timeout: if no reply after 7 days, label as "no_response" and stop monitoring
- Auto-updates the outreach tracker — student sees reply status without manual logging

### Phase 2 — ML on Real Outcomes

**Trigger:** 100+ labeled email outcomes (replied + no_response).

**Feature engineering:**

| Feature | Source | Type |
|---------|--------|------|
| email_length | Character count of sent email | Numeric |
| subject_line_length | Character count | Numeric |
| reading_level | Flesch-Kincaid score | Numeric |
| has_question | Regex check for "?" | Binary |
| mentions_specific_project | NLP check against company's specific_projects | Binary |
| edit_distance_from_draft | Levenshtein ratio between original_draft and email_text | Numeric |
| match_score | Tier-2 capability overlap (0-3) | Numeric |
| reachability_score | Rule-based score (0-1) | Numeric |
| company_stage | building-mvp / launched / growing / scaling | Categorical |
| company_team_size | Integer | Numeric |
| company_industry | From fixed industry list | Categorical |
| time_of_day_sent | Hour bucket (morning/afternoon/evening) | Categorical |
| day_of_week | Monday-Sunday | Categorical |
| student_tier1_category | Engineering / Data & ML / etc. | Categorical |

**Model:** XGBoost classifier. Binary target: replied (1) vs no_response (0).

**Evaluation:** 5-fold stratified cross-validation. Metrics: accuracy, precision, recall, F1, ROC-AUC. Same methodology as the existing ML pipeline in `backend/ml/train.py`.

**Feedback loop:** Feature importance ranking reveals what predicts replies. This directly informs prompt engineering improvements:
- If `has_question` is highly predictive → update prompt to always end with a question
- If `email_length` shows shorter emails win → enforce length cap in prompt
- If `edit_distance_from_draft` is high for successful emails → the AI drafts need improvement
- If `match_score` strongly predicts replies → the capability matching system is working

**Draft ranking (once model is reliable):** Generate 3-5 draft variants per request, score each with the model, present the highest-scoring draft to the student.

**Scaling to neural approaches:** If XGBoost plateaus in accuracy with 500+ samples, evaluate whether a text-based model (fine-tuned DeBERTa or small LLM with LoRA) improves prediction. Only pursue if the data volume justifies it and the simpler model has clearly saturated. Do not force neural approaches.

---

## 4. Migration Plan (High Level)

### What gets removed
- `backend/ml/` — entire directory (features, train, predict, labeling, config, artifacts)
- `FREE_BRIEF_LIMIT` gate — already removed
- `need_tags` as matching input — kept in DB but replaced by `capability_tags` for ranking

### What gets added
- `backend/scoring/reachability.py` — rule-based scoring
- `backend/email/` — Gmail OAuth, send, thread monitoring
- `capability_tags` field on companies table
- `location` field on users table
- `email_log` table — stores sent emails, drafts, outcomes
- Re-enrichment script for constrained capability tagging
- Updated onboarding flow (location + tier-1/tier-2 picker)
- Updated profile page (capability picker with limits)

### What gets modified
- `backend/matching/scorer.py` — use capability_tags, 0-3 range
- `backend/guidance/rules.py` — consume tier-2 picks instead of free-form skills
- `frontend/components/EmailWorkspace.tsx` — integrate with generation + Gmail send
- `frontend/app/onboard/page.tsx` — add location + capability steps
- `frontend/app/profile/page.tsx` — capability picker replaces skill picker
- `frontend/app/founder/[id]/page.tsx` — show reachability explanation

---

## 5. Open Questions

- **Location granularity:** City-level or state/region-level? City is more precise but many founders list vague locations. Start with state/region.
- **Prompt template:** Exact prompt wording for email generation needs iteration during Phase 0 validation.
- **Thread monitoring frequency:** 4-hour polling is a starting point. May need adjustment based on Gmail API quota limits.
- **Re-enrichment model:** Use same Ollama/Qwen3:4b as original enrichment, or upgrade to a better model for the constrained vocabulary task? The task is simpler (pick from a list) so the small model may suffice.
- **Google verification timeline:** Unpredictable (2-6 weeks). Submit early. Plan to operate in 100-user test mode for initial launch.
