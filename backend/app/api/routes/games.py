"""
app/api/routes/games.py
────────────────────────
Game session routes.

All endpoints require a valid Bearer JWT (via get_current_user dependency).
Business logic is delegated to game_service — route handlers only handle
HTTP concerns (parsing, response mapping, status codes).
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.game import FinishGameRequest, FinishGameResponse, StartGameResponse
from app.services.game_service import finish_game, start_game

router = APIRouter(prefix="/games", tags=["games"])


@router.post(
    "/start",
    response_model=StartGameResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new 60-second game",
)
def start(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StartGameResponse:
    """
    Create a new game session for the authenticated user.

    - Rejects the request if the user already has an active session (409).
    - Sets `started_at` and `expires_at` from server time.
    - Returns game timing so the frontend can derive the countdown.
    """
    session = start_game(db, current_user.id)
    return StartGameResponse(
        game_id=session.id,
        started_at=session.started_at,
        expires_at=session.expires_at,
        duration_seconds=60,
    )


@router.post(
    "/{game_id}/finish",
    response_model=FinishGameResponse,
    summary="Submit the final score for a game",
)
def finish(
    game_id: uuid.UUID,
    payload: FinishGameRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FinishGameResponse:
    """
    Finalise a game session and persist the score.

    The backend validates:
    - The session exists and belongs to the requesting user.
    - The session is still active.
    - The session has not already been scored.
    - The click count is within valid bounds.
    - The submission arrives within the allowed time window.
    """
    session, score = finish_game(db, game_id, current_user.id, payload.clicks)
    return FinishGameResponse(
        game_id=session.id,
        clicks=score.clicks,
        started_at=session.started_at,
        finished_at=session.finished_at,
        status=session.status,
    )
