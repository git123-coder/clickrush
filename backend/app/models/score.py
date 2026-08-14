"""
app/models/score.py
───────────────────
SQLAlchemy ORM model for the `scores` table.

Design decisions:
  - One score per game session (enforced by UNIQUE constraint on game_session_id).
    A session has exactly one outcome — there is no concept of partial scores.
  - user_id is denormalized here (it's also on game_sessions) to allow
    efficient leaderboard queries in Day 3 without JOINs:
      SELECT user_id, clicks FROM scores ORDER BY clicks DESC
  - The composite index (user_id, created_at DESC, clicks DESC) supports
    future queries like "this user's personal best" and "best scores by date".
  - Clicks is stored as INTEGER; PostgreSQL INTEGER handles up to ~2.1 billion,
    far beyond any realistic game score.

MAX_CLICKS_PER_GAME assumption:
  10,000 clicks in 60 seconds = ~167 clicks/second sustained.
  Professional speed-clickers top out around 14–16 CPS (clicks/second).
  10,000 provides a generous ceiling that stops automated cheating while
  never triggering for any human player. This is NOT meant to be airtight
  anti-cheat; it demonstrates server-side validation.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

MAX_CLICKS_PER_GAME = 10_000


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    game_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("game_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    clicks: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    game_session: Mapped["GameSession"] = relationship("GameSession", back_populates="score")  # type: ignore[name-defined]
    user: Mapped["User"] = relationship("User", back_populates="scores")  # type: ignore[name-defined]

    # ── Constraints & indexes ─────────────────────────────────────────────────
    __table_args__ = (
        # One score per game session — enforced at DB level
        UniqueConstraint("game_session_id", name="uq_scores_game_session_id"),
        # Efficient leaderboard + personal-best queries (Day 3)
        Index("ix_scores_user_created_clicks", "user_id", "created_at", "clicks"),
    )

    def __repr__(self) -> str:
        return f"<Score game={self.game_session_id} clicks={self.clicks}>"
