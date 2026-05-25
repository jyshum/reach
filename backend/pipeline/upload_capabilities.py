"""Upload capability_tags from enrichment output to Supabase."""

import json
from backend.db import get_db

BATCH_SIZE = 500


def upload(tags_path: str = "data/capability_tags.json"):
    with open(tags_path) as f:
        results = json.load(f)

    db = get_db()
    updates = [{"name": name, "capability_tags": tags} for name, tags in results.items() if tags]

    for i in range(0, len(updates), BATCH_SIZE):
        batch = updates[i:i + BATCH_SIZE]
        db.table("companies").upsert(batch, on_conflict="name").execute()
        print(f"  Uploaded {min(i + BATCH_SIZE, len(updates))}/{len(updates)}")

    print(f"Done. Updated {len(updates)} companies.")


if __name__ == "__main__":
    upload()
