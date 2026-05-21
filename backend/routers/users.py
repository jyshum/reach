"""User profile endpoints."""

from fastapi import APIRouter, Depends, Request
from backend.auth import get_current_user
from backend.db import get_db
from backend.schemas import UserProfile, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserProfile)
def get_me(request: Request, user_id: str = Depends(get_current_user)):
    """Get current user profile. Auto-creates on first call."""
    db = get_db()

    # Check if user exists
    result = db.table("users").select("*").eq("id", user_id).execute()

    if result.data:
        return result.data[0]

    # Auto-create bare profile
    email = ""
    try:
        from jose import jwt
        token = request.headers.get("Authorization", "").split(" ", 1)[1]
        payload = jwt.decode(token, options={"verify_signature": False})
        email = payload.get("email", "")
    except Exception:
        pass

    new_user = {"id": user_id, "email": email, "tier": "free", "skills": []}
    result = db.table("users").insert(new_user).execute()
    return result.data[0]


@router.put("/me", response_model=UserProfile)
def update_me(body: UserUpdate, user_id: str = Depends(get_current_user)):
    """Update user profile fields."""
    db = get_db()

    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        # Nothing to update, return current profile
        result = db.table("users").select("*").eq("id", user_id).execute()
        return result.data[0]

    result = db.table("users").update(update_data).eq("id", user_id).execute()
    return result.data[0]
