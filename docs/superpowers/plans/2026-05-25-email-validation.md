# Email Pipeline Phase 0: Validation Experiment

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Before building Gmail integration, validate that LLM-generated email drafts can produce founder replies at a rate comparable to fully human-written emails.

**Architecture:** Create a prompt template, generate 10 AI-assisted emails, write 10 fully human emails, send all 20 from a personal inbox, track results over 7 days.

**Tech Stack:** Claude API or local Ollama (Qwen3:4b) for generation, personal Gmail for sending, spreadsheet for tracking

---

### Task 1: Create the Email Prompt Template

**Files:**
- Create: `backend/email/__init__.py`
- Create: `backend/email/prompt.py`
- Create: `tests/email/__init__.py`
- Create: `tests/email/test_prompt.py`

- [ ] **Step 1: Write failing tests for prompt builder**

```python
# tests/email/__init__.py
# (empty)

# tests/email/test_prompt.py
from backend.email.prompt import build_email_prompt


def test_build_prompt_contains_student_info():
    result = build_email_prompt(
        student_bio="HS junior interested in ML, built a sentiment analysis project",
        student_capabilities=["deep-learning", "data-pipelines"],
        company_name="Pando Bioscience",
        company_summary="Pando uses AI to design custom enzymes for pharma",
        specific_projects=["Analyze enzyme screening data", "Create technical docs"],
        founder_name="Alex Chen",
        guidance_angle="Lead with your ML project experience",
    )
    assert "sentiment analysis" in result
    assert "Pando Bioscience" in result
    assert "Alex Chen" in result
    assert "enzyme" in result.lower()


def test_build_prompt_with_missing_optionals():
    result = build_email_prompt(
        student_bio="CS student",
        student_capabilities=["frontend-development"],
        company_name="Acme Corp",
        company_summary="Building dev tools",
        specific_projects=[],
        founder_name="Jane Doe",
        guidance_angle=None,
    )
    assert "Acme Corp" in result
    assert "Jane Doe" in result


def test_prompt_enforces_constraints():
    result = build_email_prompt(
        student_bio="Student",
        student_capabilities=["backend-apis"],
        company_name="Test Co",
        company_summary="Test summary",
        specific_projects=["Build an API"],
        founder_name="Sam",
        guidance_angle="Lead with API experience",
    )
    # Prompt should instruct short, student-voice email
    assert "4-5 sentences" in result or "short" in result.lower()
    assert "student" in result.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/email/test_prompt.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

```python
# backend/email/__init__.py
# (empty)

# backend/email/prompt.py
"""Prompt template for cold email generation."""


def build_email_prompt(
    student_bio: str,
    student_capabilities: list[str],
    company_name: str,
    company_summary: str,
    specific_projects: list[str],
    founder_name: str,
    guidance_angle: str | None = None,
) -> str:
    """Build a prompt for generating a cold email draft.

    Returns the full prompt string to send to an LLM.
    """
    projects_text = ""
    if specific_projects:
        projects_text = "They need help with: " + "; ".join(specific_projects) + "."

    angle_text = ""
    if guidance_angle:
        angle_text = f"\nAngle to lead with: {guidance_angle}"

    return f"""Write a cold email from a student to a startup founder.

STRICT RULES:
- Maximum 4-5 sentences. Shorter is better.
- Sound like a real student, not a professional. Casual but respectful.
- NO filler enthusiasm ("I'm really excited", "I'd love to", "I'm passionate about")
- NO compliments about the company ("I admire your work", "Your company is amazing")
- Include ONE specific hook showing you actually understand what they build
- End with a concrete, low-commitment ask (e.g. "Could I spend 2 hours this week on X?")
- Do NOT use a formal sign-off. Just the student's first name.

STUDENT CONTEXT:
Bio: {student_bio}
Capabilities: {", ".join(student_capabilities)}
{angle_text}

COMPANY CONTEXT:
Company: {company_name}
Founder: {founder_name}
What they do: {company_summary}
{projects_text}

Write the email body only. No subject line. No "Dear" or "Hi {founder_name}," — start directly with the hook."""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/email/test_prompt.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/email/ tests/email/
git commit -m "feat: add email generation prompt template"
```

---

### Task 2: Create Generation Script for Validation

**Files:**
- Create: `backend/email/generate_test_batch.py`

- [ ] **Step 1: Write the batch generation script**

```python
# backend/email/generate_test_batch.py
"""Generate a batch of test emails for the validation experiment.

Usage:
    python -m backend.email.generate_test_batch --model ollama
    python -m backend.email.generate_test_batch --model claude
"""

import argparse
import json
import requests

from backend.email.prompt import build_email_prompt
from backend.pipeline.enrich_config import OLLAMA_URL, OLLAMA_MODEL


# 10 companies to test with — fill these from your actual database
SAMPLE_COMPANIES = [
    # Replace with real data from data/enriched_companies.json
    # {
    #     "name": "...",
    #     "summary": "...",
    #     "specific_projects": ["...", "..."],
    #     "founder_name": "...",
    # },
]

# Student profiles for testing — fill with real/realistic profiles
STUDENT_PROFILE = {
    "bio": "",  # Fill with your actual bio
    "capabilities": [],  # Fill with your tier-2 picks
}


def generate_ollama(prompt: str) -> str:
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "system": "You are a helpful writing assistant. Follow instructions exactly.",
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 256},
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["response"].strip()


def generate_claude(prompt: str) -> str:
    import anthropic

    client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["ollama", "claude"], default="ollama")
    args = parser.parse_args()

    generate = generate_ollama if args.model == "ollama" else generate_claude

    if not SAMPLE_COMPANIES:
        print("ERROR: Fill in SAMPLE_COMPANIES with real data from your database.")
        print("Run: python -c \"import json; data=json.load(open('data/enriched_companies.json')); ...")
        return

    results = []
    for i, company in enumerate(SAMPLE_COMPANIES):
        prompt = build_email_prompt(
            student_bio=STUDENT_PROFILE["bio"],
            student_capabilities=STUDENT_PROFILE["capabilities"],
            company_name=company["name"],
            company_summary=company.get("summary") or company.get("description", ""),
            specific_projects=company.get("specific_projects", []),
            founder_name=company.get("founder_name", "Founder"),
            guidance_angle=None,
        )

        email = generate(prompt)
        results.append({
            "company": company["name"],
            "founder": company.get("founder_name"),
            "email": email,
            "model": args.model,
        })
        print(f"[{i+1}/{len(SAMPLE_COMPANIES)}] {company['name']}")
        print(f"  {email[:100]}...")
        print()

    output_path = f"data/test_emails_{args.model}.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved {len(results)} emails to {output_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add backend/email/generate_test_batch.py
git commit -m "feat: add validation batch email generation script"
```

---

### Task 3: Create Tracking Spreadsheet Template

**Files:**
- Create: `docs/email-validation-tracker.md`

- [ ] **Step 1: Write the tracking template**

```markdown
# Email Validation Experiment Tracker

## Setup
- Date started: YYYY-MM-DD
- Model used: ollama / claude
- Student profile: [your bio summary]
- Capabilities: [your picks]

## Group A: AI-Generated (edited by you)
| # | Company | Founder | Sent date | Replied? | Reply date | Notes |
|---|---------|---------|-----------|----------|------------|-------|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |
| 4 | | | | | | |
| 5 | | | | | | |
| 6 | | | | | | |
| 7 | | | | | | |
| 8 | | | | | | |
| 9 | | | | | | |
| 10 | | | | | | |

## Group B: Fully Human-Written
| # | Company | Founder | Sent date | Replied? | Reply date | Notes |
|---|---------|---------|-----------|----------|------------|-------|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |
| 4 | | | | | | |
| 5 | | | | | | |
| 6 | | | | | | |
| 7 | | | | | | |
| 8 | | | | | | |
| 9 | | | | | | |
| 10 | | | | | | |

## Results (fill after 7 days)
- Group A replies: ___ / 10
- Group B replies: ___ / 10
- Decision: proceed / rework prompt / abandon
- Notes:
```

- [ ] **Step 2: Commit**

```bash
git add docs/email-validation-tracker.md
git commit -m "docs: add email validation experiment tracker"
```

---

### Task 4: Run the Experiment

This task is manual — no code.

- [ ] **Step 1: Select 20 companies from database**

Run this to get 20 random high-reachability companies with founder info:
```bash
python3 -c "
import json, random
random.seed(42)
with open('data/enriched_companies.json') as f:
    companies = json.load(f)
valid = [c for c in companies if c.get('founder_name') and c.get('summary')]
sample = random.sample(valid, 20)
for i, c in enumerate(sample):
    print(f'{i+1}. {c[\"name\"]} - {c.get(\"founder_name\")} - {c.get(\"summary\",\"\")[:80]}')
"
```

Split into two groups of 10: Group A (AI-assisted) and Group B (human-written).

- [ ] **Step 2: Fill in SAMPLE_COMPANIES in generate_test_batch.py with Group A companies**

- [ ] **Step 3: Generate AI drafts**

Run: `python -m backend.email.generate_test_batch --model ollama`
(or `--model claude` if you have an API key and want to compare)

- [ ] **Step 4: Edit each AI draft to sound like you, then send from your Gmail**

- [ ] **Step 5: Write 10 fully human emails for Group B, send from your Gmail**

- [ ] **Step 6: Fill in the tracker. Wait 7 days. Record results.**

- [ ] **Step 7: Make go/no-go decision on Phase 1**
