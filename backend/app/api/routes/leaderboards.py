"""
app/api/routes/leaderboards.py
───────────────────────────────
Public leaderboard endpoints.

All three endpoints are unauthenticated — leaderboard data is public
information.  No sensitive user data (email, password) is exposed; only
username and click count appear in responses.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.leaderboard import LeaderboardResponse
from app.services.leaderboard_service import (
    MAX_LIMIT,
    get_daily_leaderboard,
    get_global_leaderboard,
    get_weekly_leaderboard,
)

router = APIRouter(prefix="/leaderboards", tags=["leaderboards"])

_LIMIT_PARAM = Query(
    default=50,
    ge=1,
    le=MAX_LIMIT,
    description=f"Number of entries to return (1–{MAX_LIMIT}).",
)


@router.get(
    "/global",
    response_model=LeaderboardResponse,
    summary="Global all-time leaderboard",
)
def global_leaderboard(
    limit: int = _LIMIT_PARAM,
    db: Session = Depends(get_db),
) -> LeaderboardResponse:
    """
    Returns the top users ranked by their all-time highest single score.

    Each user appears at most once (their personal best). Ties broken by
    `achieved_at ASC` (earlier achievement wins the better rank).
    """
    entries = get_global_leaderboard(db, limit)
    return LeaderboardResponse(entries=entries)


@router.get(
    "/daily",
    response_model=LeaderboardResponse,
    summary="Today's leaderboard (UTC calendar day)",
)
def daily_leaderboard(
    limit: int = _LIMIT_PARAM,
    db: Session = Depends(get_db),
) -> LeaderboardResponse:
    """
    Returns the top users ranked by their highest score posted today (UTC).

    Window: from 00:00:00 UTC today to now.
    Returns 200 with an empty list if no scores have been posted today.
    """
    entries = get_daily_leaderboard(db, limit)
    return LeaderboardResponse(entries=entries)


@router.get(
    "/weekly",
    response_model=LeaderboardResponse,
    summary="Last-7-days rolling leaderboard",
)
def weekly_leaderboard(
    limit: int = _LIMIT_PARAM,
    db: Session = Depends(get_db),
) -> LeaderboardResponse:
    """
    Returns the top users ranked by their highest score in the last 7 days.

    Window: rolling 7 calendar days (now − 7 days to now).
    Returns 200 with an empty list if no scores fall in the window.
    """
    entries = get_weekly_leaderboard(db, limit)
    return LeaderboardResponse(entries=entries)
