"""JWT verification for Supabase Auth tokens."""

import os
from fastapi import Request, HTTPException
from jose import jwt


JWT_ALGORITHM = "HS256"


def _get_jwt_secret() -> str:
    """Read JWT secret from environment. Raises if missing or empty."""
    secret = os.environ.get("SUPABASE_JWT_SECRET", "")
    if not secret:
        raise HTTPException(status_code=500, detail="Server misconfiguration: JWT secret not set")
    return secret


def get_current_user(request: Request) -> str:
    """Extract and verify JWT from Authorization header. Returns user ID.

    Raises HTTPException 401 if token is missing or invalid.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = auth_header.split(" ", 1)[1]

    try:
        payload = jwt.decode(token, _get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return user_id
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_optional_user(request: Request) -> str | None:
    """Extract user ID from JWT if present. Returns None if no valid token.

    Does not raise — used for endpoints with optional auth (e.g., /companies browse).
    """
    try:
        return get_current_user(request)
    except HTTPException:
        return None
