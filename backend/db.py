"""Supabase client setup."""

import os
from supabase import create_client, Client


def get_supabase_client() -> Client:
    """Create and return a Supabase client using environment variables."""
    url = os.environ["SUPABASE_URL"]
    key = os.environ.get("SUPABASE_KEY", os.environ.get("SUPABASE_ANON_KEY", ""))
    return create_client(url, key)


# Singleton client — initialized on first import
_client: Client | None = None


def get_db() -> Client:
    """Get the shared Supabase client instance."""
    global _client
    if _client is None:
        _client = get_supabase_client()
    return _client
