"""Shared fixtures for API tests."""

import os
import pytest


@pytest.fixture(autouse=True)
def set_jwt_secret(monkeypatch):
    """Ensure SUPABASE_JWT_SECRET is set for all API tests."""
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-secret-key")
