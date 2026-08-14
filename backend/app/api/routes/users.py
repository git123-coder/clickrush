"""
app/api/routes/users.py
────────────────────────
User routes — profile, game history, and personal rankings.

All /me/* endpoints are protected and always operate on the current
authenticated user. There is no way to fetch another user's private history
through this router.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.profile import GameHistoryResponse, UserRankingsResponse
from app.schemas.user import UserResponse
from app.services.profile_service import (
    MAX_HISTORY_LIMIT,
    get_game_history,
    get_user_rankings,
)

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


@router.get(
    "/me/games",
    response_model=GameHistoryResponse,
    summary="Get the current user's completed game history",
)
def get_my_games(
    limit: int = Query(
        default=20,
        ge=1,
        le=MAX_HISTORY_LIMIT,
        description=f"Number of games per page (1–{MAX_HISTORY_LIMIT}).",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of games to skip (for pagination).",
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GameHistoryResponse:
    """
    Protected endpoint. Returns only the authenticated user's own games.

    - Only completed games are included (no abandoned / expired sessions).
    - Ordered most recent first (by finished_at DESC).
    - `total` in the response is the user's all-time completed-game count,
      useful for building a "load more" or pagination control in the UI.
    """
    return get_game_history(db, current_user.id, limit, offset)


@router.get(
    "/me/rankings",
    response_model=UserRankingsResponse,
    summary="Get the current user's leaderboard rankings",
)
def get_my_rankings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserRankingsResponse:
    """
    Protected endpoint.

    Returns the authenticated user's position on each leaderboard:
      - personal_best: all-time highest click count (null if no games played)
      - global_rank: position on the all-time leaderboard (null if unranked)
      - daily_rank: position on today's leaderboard (null if unranked)
      - weekly_rank: position on the last-7-day leaderboard (null if unranked)

    Ranking logic is identical to the public leaderboard endpoints (same CTE,
    same DISTINCT ON, same tie-breaking) so rank numbers always agree.
    """
    return get_user_rankings(db, current_user.id, current_user.username)
