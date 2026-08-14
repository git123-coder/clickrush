"""
app/api/routes/users.py
────────────────────────
User routes — currently just the authenticated "me" endpoint.

This proves JWT authentication works end-to-end and provides the
foundation for Day 2+ profile, history, and score endpoints.
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the currently authenticated user",
)
def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """
    Protected endpoint.

    Requires a valid Bearer JWT in the Authorization header.
    Returns the authenticated user's public profile.
    """
    return current_user  # type: ignore[return-value]
