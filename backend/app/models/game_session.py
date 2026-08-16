"""
app/models/game_session.py
──────────────────────────
SQLAlchemy ORM model for the `game_sessions` table.

Design decisions:
  - A GameSession represents one 60-second attempt by a user.
  - Separating sessions from users means the same user can play many games
    over time without a cluttered users table (extensible for Day 3 history).
  - status enum: active → completed (success path) or expired (cleanup path).
  - started_at / expires_at are set by the SERVER, not the client.
    This is the core of server-authoritative timing.
  - finished_at is NULL until the game is completed.
  - Index on (user_id, status) allows fast lookup of a user's active session.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

GAME_DURATION_SECONDS = 60
# Small server-side grace period to handle reasonable network delay.
# A submission arriving up to this many seconds after expires_at is still accepted.
# Documented assumption: legitimate clients submit near expiry; a 10-second
# grace covers normal network latency without meaningfully compromising integrity.
GRACE_PERIOD_SECONDS = 10


class GameStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    expired = "expired"


class GameSession(Base):
    __tablename__ = "game_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    status: Mapped[GameStatus] = mapped_column(
        Enum(GameStatus, name="gamestatus"),
        nullable=False,
        default=GameStatus.active,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    # back_populates links to User.game_sessions (added to user.py)
    user: Mapped["User"] = relationship("User", back_populates="game_sessions")  # type: ignore[name-defined]
    score: Mapped["Score | None"] = relationship("Score", back_populates="game_session", uselist=False)  # type: ignore[name-defined]

    # ── Composite indexes ─────────────────────────────────────────────────────
    __table_args__ = (
        # Fast lookup: "does this user have an active game?"
        Index("ix_game_sessions_user_status", "user_id", "status"),
        # Prevent TOCTOU race: only one active session per user allowed
        Index("uq_one_active_session_per_user", "user_id", unique=True, postgresql_where=text("status = 'active'")),
    )

    def __repr__(self) -> str:
        return f"<GameSession id={self.id} user_id={self.user_id} status={self.status}>"
