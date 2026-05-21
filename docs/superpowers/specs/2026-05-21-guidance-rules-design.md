# Outreach Guidance Rules Engine — Design Spec

*2026-05-21*

---

## Overview

A rule-based guidance system that generates personalized outreach advice for each company brief. No AI, no API cost. Assembles 4 guidance fields from composable rule layers (skill-type × stage × industry cluster) with template slot-filling from enriched company data.

---

## Output: 4 Guidance Fields

| Field | Purpose |
|---|---|
| **your_angle** | What to lead with given the student's skill + company context |
| **reference_this** | One specific thing to mention from the company's background |
| **dont_say** | The most common mistake for this company type |
| **your_ask** | What to actually request — a specific deliverable, never "internship" |

---

## Architecture

### Files

- `backend/guidance/rules.py` — rule dictionaries, classifier, mapper, generator
- `tests/guidance/test_rules.py` — unit + integration tests

### Schema Changes

Add to `backend/schemas.py`:

```python
class Guidance(BaseModel):
    your_angle: str
    reference_this: str
    dont_say: str
    your_ask: str
```

Add `guidance: Guidance | None` to `CompanyBrief`.

### Wiring

In `backend/routers/companies.py`, the `GET /companies/{id}` brief endpoint calls `generate_guidance(user_skills, company)` and attaches the result to the response. Returns `guidance: None` if user has no skills set.

No new endpoints, no new DB tables, no external calls.

---

## Composable Rule Layers

### Layer 1: Skill-Type Rules (6 buckets)

Classify the student's skills into one primary type:

| Bucket | Example skills |
|---|---|
| **developer** | Python, React, API integration, mobile dev |
| **designer** | UI/UX, Figma, graphic design |
| **data** | data analysis, visualization, ML |
| **writer** | content writing, scientific writing, copywriting |
| **business** | marketing, sales, social media, market research |
| **operations** | project management, customer support, QA testing |

**Classification logic:** Count how many of the user's selected skills fall into each bucket. Winner takes it. Ties broken by which bucket has more overlap with the company's `need_tags`.

**Primary contribution:** `your_angle` templates.

### Layer 2: Stage Rules (4 stages)

From enriched `stage_detail`: `building-mvp`, `launched`, `growing`, `scaling`.

**Primary contribution:** `dont_say` and `your_ask` templates.

### Layer 3: Industry Cluster Rules (8 clusters)

Map 30 enrichment industries → 8 clusters:

| Cluster | Enrichment industries |
|---|---|
| **software** | saas, developer-tools, productivity |
| **ai-ml** | ai-ml, data-science |
| **fintech** | fintech, crypto |
| **health-bio** | healthcare, biotech, mental-health |
| **commerce** | e-commerce, marketplace, consumer |
| **infrastructure** | cloud, security, devops |
| **impact** | climate, education, govtech, nonprofit |
| **general** | real-estate, logistics, legal, media, gaming, and any unmapped |

**Primary contribution:** `reference_this` templates.

---

## Field Assembly

| Field | Primary source | Slot-filled from |
|---|---|---|
| **your_angle** | Skill-type rules | `{matched_skill}`, `{specific_project}` |
| **reference_this** | Industry rules | `{company_name}`, `{summary_snippet}`, `{specific_project}` |
| **dont_say** | Stage rules | `{company_name}` |
| **your_ask** | Stage rules | `{matched_skill}`, `{specific_project}` |

### Slot Values

- `{matched_skill}` — the user skill that overlaps with the company's `need_tags` (first match)
- `{specific_project}` — the company's `specific_projects` entry most relevant to the student's skill-type (selected by keyword matching against skill-type bucket terms; defaults to first entry if no clear match)
- `{company_name}` — from company data
- `{summary_snippet}` — first sentence of the company's `summary` field

### Specific Project Selection

Each company has 2 `specific_projects` from LLM enrichment. The system picks the one most relevant to the student's skill-type by checking which project contains keywords related to their bucket. If neither is a clear match, use the first one.

---

## Fallback Behavior

| Condition | Behavior |
|---|---|
| User has no skills set | Return `guidance: None` |
| Company has empty `need_tags` | Generate from stage + industry layers only, skip skill-specific slots |
| Company industry not in any cluster | Map to "general" cluster |
| Company missing `specific_projects` | Degrade templates to generic versions without project references |
| Company missing `summary` | Use `description` field instead for `{summary_snippet}` |
| No skill overlap with company | Still classify by user's overall skill-type, note no direct overlap |

---

## Testing

File: `tests/guidance/test_rules.py`

### Unit Tests
- **Skill classification** — various skill lists map to correct bucket
- **Tie-breaking** — equal skills across buckets resolved by company overlap
- **Industry mapping** — all 30 enrichment industries map to a cluster
- **Unmapped industry** — falls back to "general"
- **Slot filling** — templates produce strings with no leftover `{placeholder}` markers
- **Specific project selection** — correct project chosen per skill-type

### Fallback Tests
- User with no skills → `None`
- Company with no `need_tags` → still valid guidance
- Company with no `specific_projects` → generic fallback text
- Company with no `summary` → uses `description`

### Integration Test
- Mock a brief request with auth, verify `guidance` object in response with all 4 string fields populated

---

## Rule Count Estimate

- 6 skill-type rules (angle templates)
- 4 stage rules (dont_say + your_ask templates)
- 8 industry cluster rules (reference_this templates)
- ~18-22 total rule entries, composing into guidance for any company

---

## What This Does NOT Include

- No AI generation of guidance text
- No new database tables or stored guidance
- No user-facing configuration of guidance
- No A/B testing or variation — deterministic output from rules
- No changes to the matching/scoring system (already complete)
