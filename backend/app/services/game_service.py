"""
app/services/game_service.py
─────────────────────────────
Business logic for game sessions and scores.

Why keep this in a service layer?
  - Route handlers stay thin: they validate HTTP input and delegate here.
  - Business rules (timing, validation, concurrency protection) are
    testable without an HTTP layer.
  - Easy to extend for Day 3 leaderboard queries.

Concurrency / duplicate-start protection:
  - We query for an existing active session before creating a new one.
  - Known limitation: two simultaneous requests could both pass the check
    before either commits (TOCTOU race). In production this would be solved
    with a DB-level unique partial index:
        CREATE UNIQUE INDEX uq_one_active_game_per_user
        ON game_sessions (user_id)
        WHERE status = 'active';
    We document this limitation rather than over-engineer for it here.

Timing design:
  - started_at and expires_at are computed from server time (UTC).
  - finish() checks current server time against expires_at.
  - A GRACE_PERIOD_SECONDS allowance handles legitimate network delay.
"""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.game_session import GAME_DURATION_SECONDS, GRACE_PERIOD_SECONDS, GameSession, GameStatus
from app.models.score import MAX_CLICKS_PER_GAME, Score


# ── Start ─────────────────────────────────────────────────────────────────────

def get_active_session(db: Session, user_id: uuid.UUID) -> GameSession | None:
    """Return the user's currently active GameSession, or None."""
    return db.scalar(
        select(GameSession).where(
            GameSession.user_id == user_id,
            GameSession.status == GameStatus.active,
        )
    )


def start_game(db: Session, user_id: uuid.UUID) -> GameSession:
    """
    Create a new game session for the user.

    Rejects the request if the user already has an active session.
    Timestamps are set from the server clock — never from client input.
    """
    existing = get_active_session(db, user_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an active game. Finish it before starting a new one.",
        )

    now = datetime.now(timezone.utc)
    session = GameSession(
        user_id=user_id,
        started_at=now,
        expires_at=now + timedelta(seconds=GAME_DURATION_SECONDS),
        status=GameStatus.active,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


# ── Finish ────────────────────────────────────────────────────────────────────

def get_session_by_id(db: Session, game_id: uuid.UUID) -> GameSession | None:
    """Return a GameSession by its UUID, or None."""
    return db.get(GameSession, game_id)


def finish_game(
    db: Session,
    game_id: uuid.UUID,
    user_id: uuid.UUID,
    clicks: int,
) -> tuple[GameSession, Score]:
    """
    Validate and finalise a game session, persisting the score.

    Validations (in order):
      1. Session must exist.
      2. Session must belong to the requesting user.
      3. Session must be active (not already completed or expired).
      4. Session must not already have a score (double-submit protection).
      5. Clicks must be within the allowed range [0, MAX_CLICKS_PER_GAME].
      6. Current server time must be within the allowed window
         (started_at … expires_at + GRACE_PERIOD_SECONDS).

    Returns (game_session, score) on success.
    """
    session = get_session_by_id(db, game_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game session not found.",
        )

    if session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This game session does not belong to you.",
        )

    if session.status != GameStatus.active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Game session is already {session.status.value}.",
        )

    # Double-submit guard: check for existing score
    existing_score = db.scalar(
        select(Score).where(Score.game_session_id == game_id)
    )
    if existing_score:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A score for this game session already exists.",
        )

    # Click range validation
    if clicks < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="clicks must be >= 0.",
        )
    if clicks > MAX_CLICKS_PER_GAME:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"clicks exceeds the maximum allowed ({MAX_CLICKS_PER_GAME}).",
        )

    # Timing validation — server is authoritative
    now = datetime.now(timezone.utc)
    deadline = session.expires_at + timedelta(seconds=GRACE_PERIOD_SECONDS)

    if now < session.started_at:
        # Should never happen, but guard against clock skew
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submission received before game started.",
        )

    if now > deadline:
        # Mark as expired so the user can start a new game
        session.status = GameStatus.expired
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Game session has expired. Start a new game.",
        )

    # ── Persist ───────────────────────────────────────────────────────────────
    finished_at = now
    session.finished_at = finished_at
    session.status = GameStatus.completed

    score = Score(
        game_session_id=game_id,
        user_id=user_id,
        clicks=clicks,
    )
    db.add(score)
    db.commit()
    db.refresh(session)
    db.refresh(score)

    return session, score
