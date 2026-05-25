"""JWT verification for Supabase Auth tokens."""

import os
import requests as http_requests
from fastapi import Request, HTTPException
from jose import jwt, jwk


# Cache JWKS keys in memory (refreshed on process restart)
_jwks_cache: dict | None = None


def _get_jwks(supabase_url: str) -> dict:
    """Fetch and cache JWKS public keys from Supabase."""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache

    url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
    resp = http_requests.get(url, timeout=10)
    resp.raise_for_status()
    _jwks_cache = resp.json()
    return _jwks_cache


def _get_jwt_secret() -> str:
    """Read JWT secret from environment for HS256 fallback."""
    return os.environ.get("SUPABASE_JWT_SECRET", "")


def _decode_token(token: str) -> dict:
    """Decode a Supabase JWT, supporting both ES256 (ECC) and HS256 (legacy)."""
    # Peek at the token header to determine algorithm
    header = jwt.get_unverified_header(token)
    alg = header.get("alg", "HS256")

    if alg == "ES256":
        supabase_url = os.environ.get("SUPABASE_URL", "")
        if not supabase_url:
            raise ValueError("SUPABASE_URL not set")

        jwks = _get_jwks(supabase_url)
        kid = header.get("kid")

        # Find the matching key
        key_data = None
        for k in jwks.get("keys", []):
            if k.get("kid") == kid:
                key_data = k
                break

        if not key_data:
            raise ValueError(f"No matching JWKS key for kid={kid}")

        public_key = jwk.construct(key_data, algorithm="ES256")
        return jwt.decode(token, public_key, algorithms=["ES256"], audience="authenticated")

    else:
        # HS256 legacy fallback
        secret = _get_jwt_secret()
        if not secret:
            raise ValueError("SUPABASE_JWT_SECRET not set for HS256 token")
        return jwt.decode(token, secret, algorithms=["HS256"])


def get_current_user(request: Request) -> str:
    """Extract and verify JWT from Authorization header. Returns user ID."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = auth_header.split(" ", 1)[1]

    try:
        payload = _decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return user_id
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_optional_user(request: Request) -> str | None:
    """Extract user ID from JWT if present. Returns None if no valid token."""
    try:
        return get_current_user(request)
    except HTTPException:
        return None
