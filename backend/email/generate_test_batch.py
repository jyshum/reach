"""Generate a batch of test emails for the validation experiment.

Usage:
    python -m backend.email.generate_test_batch --model ollama
    python -m backend.email.generate_test_batch --model claude
"""

import argparse
import json
import requests

from backend.email.prompt import build_email_prompt
from backend.pipeline.enrich_config import OLLAMA_MODEL

OLLAMA_BASE_URL = "http://localhost:11434"

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
        f"{OLLAMA_BASE_URL}/api/generate",
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
