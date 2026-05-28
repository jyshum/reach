"""Upload enriched company data to Supabase."""

import json
import os

from backend.db import get_supabase_client
from backend.pipeline.enrich_config import ENRICHED_OUTPUT_PATH
from backend.ml.config import SCORES_OUTPUT_PATH

# Batch size for upserts (Supabase has a row limit per request)
UPSERT_BATCH_SIZE = 500

# Columns to upload (must match schema.sql)
COMPANY_COLUMNS = [
    "name", "yc_batch", "description", "long_description", "summary", "one_liner",
    "website", "industry", "stage", "stage_detail", "technical_level", "team_size",
    "need_tags", "specific_projects", "is_hiring", "status", "reachability_score",
    "reachability_probability", "all_locations", "tags", "industries",
    "slug", "small_logo_url",
    "founder_name", "founder_title", "founder_avatar_url",
    "founder_linkedin", "founder_twitter", "founder_email",
    "founder_bio", "has_email", "email_source", "email_confidence", "yc_tags",
]

FOUNDERS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "founders.json")
RESOLVED_EMAILS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "resolved_emails.json")
CURATED_TAGS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "curated_tags.json")


def merge_company_data(
    enriched: list[dict],
    scores: list[dict],
    raw: list[dict],
    founders: list[dict],
    emails: list[dict] | None = None,
    tag_mapping_data: dict | None = None,
) -> list[dict]:
    """Merge enriched company data with scores, raw fields, founder data, emails, and tags."""
    score_map = {s["name"]: s for s in scores}
    raw_map = {r["name"]: r for r in raw}
    founder_map = {f["company_name"]: f for f in founders}
    email_map = {e["company_name"]: e for e in (emails or [])}

    merged = []
    for company in enriched:
        name = company["name"]
        score_data = score_map.get(name, {})
        raw_data = raw_map.get(name, {})
        founder_data = founder_map.get(name, {})
        email_data = email_map.get(name, {})

        record = {}
        for col in COMPANY_COLUMNS:
            if col in company:
                record[col] = company[col]
            elif col in score_data:
                record[col] = score_data[col]

        # Map 'batch' field name to 'yc_batch'
        if "yc_batch" not in record and "batch" in company:
            record["yc_batch"] = company["batch"]

        # Default reachability if missing
        record.setdefault("reachability_score", "low")
        record.setdefault("reachability_probability", 0.0)

        # Add slug and logo from raw Algolia data
        record["slug"] = raw_data.get("slug") or None
        record["small_logo_url"] = raw_data.get("small_logo_thumb_url") or None

        # Add founder data
        record["founder_name"] = founder_data.get("founder_name")
        record["founder_title"] = founder_data.get("founder_title")
        record["founder_avatar_url"] = founder_data.get("founder_avatar_url")
        record["founder_linkedin"] = founder_data.get("founder_linkedin")
        record["founder_twitter"] = founder_data.get("founder_twitter")
        record["founder_bio"] = founder_data.get("founder_bio")
        record["has_email"] = founder_data.get("has_email", False)

        # Add resolved email data
        record["founder_email"] = email_data.get("founder_email")
        record["email_source"] = email_data.get("email_source")
        record["email_confidence"] = email_data.get("email_confidence")

        # Map raw YC tags to curated tags
        if tag_mapping_data:
            from backend.pipeline.curate_tags import map_company_tags
            record["yc_tags"] = map_company_tags(
                raw_data, tag_mapping_data["collapse_map"], tag_mapping_data["valid_tags"]
            )
        else:
            record["yc_tags"] = []

        merged.append(record)

    return merged


def upload_to_supabase(companies: list[dict]):
    """Upsert companies to Supabase in batches."""
    db = get_supabase_client()

    for i in range(0, len(companies), UPSERT_BATCH_SIZE):
        batch = companies[i:i + UPSERT_BATCH_SIZE]
        db.table("companies").upsert(batch, on_conflict="name").execute()
        print(f"[INFO] Upserted batch {i // UPSERT_BATCH_SIZE + 1} ({len(batch)} companies)")


def write_to_supabase(
    enriched_path: str = ENRICHED_OUTPUT_PATH,
    scores_path: str = SCORES_OUTPUT_PATH,
    raw_path: str = None,
    founders_path: str = FOUNDERS_PATH,
    emails_path: str = RESOLVED_EMAILS_PATH,
    curated_tags_path: str = CURATED_TAGS_PATH,
):
    """Full pipeline step: read files, merge, upload."""
    if raw_path is None:
        raw_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw_companies.json")

    with open(enriched_path) as f:
        enriched = json.load(f)

    with open(scores_path) as f:
        scores = json.load(f)

    with open(raw_path) as f:
        raw = json.load(f)

    founders = []
    if os.path.exists(founders_path):
        with open(founders_path) as f:
            founders = json.load(f)

    # Load resolved emails if available
    emails = []
    if os.path.exists(emails_path):
        with open(emails_path) as f:
            emails = json.load(f)

    # Load curated tags and build tag mapping data
    tag_mapping_data = None
    if os.path.exists(curated_tags_path):
        with open(curated_tags_path) as f:
            curated = json.load(f)
        from backend.pipeline.curate_tags import COLLAPSE_MAP
        tag_mapping_data = {
            "collapse_map": COLLAPSE_MAP,
            "valid_tags": set(curated.get("valid_tags", [])),
        }

    print(f"[INFO] Loaded {len(enriched)} enriched, {len(scores)} scores, {len(raw)} raw, {len(founders)} founders, {len(emails)} emails")

    merged = merge_company_data(enriched, scores, raw, founders, emails=emails, tag_mapping_data=tag_mapping_data)
    print(f"[INFO] Merged {len(merged)} companies")

    upload_to_supabase(merged)
    print(f"[DONE] Uploaded {len(merged)} companies to Supabase")


if __name__ == "__main__":
    write_to_supabase()
