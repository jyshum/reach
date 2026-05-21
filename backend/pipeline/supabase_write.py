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
]


def merge_company_data(enriched: list[dict], scores: list[dict]) -> list[dict]:
    """Merge enriched company data with reachability scores."""
    score_map = {s["name"]: s for s in scores}

    merged = []
    for company in enriched:
        score_data = score_map.get(company["name"], {})

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
):
    """Full pipeline step: read files, merge, upload."""
    with open(enriched_path) as f:
        enriched = json.load(f)

    with open(scores_path) as f:
        scores = json.load(f)

    print(f"[INFO] Loaded {len(enriched)} enriched, {len(scores)} scores")

    merged = merge_company_data(enriched, scores)
    print(f"[INFO] Merged {len(merged)} companies")

    upload_to_supabase(merged)
    print(f"[DONE] Uploaded {len(merged)} companies to Supabase")


if __name__ == "__main__":
    write_to_supabase()
