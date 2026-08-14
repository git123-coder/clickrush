"""
app/models/user.py
──────────────────
SQLAlchemy ORM model for the `users` table.

Design decisions:
  - UUID primary key: avoids sequential integer leakage (no "I'm user #42"),
    is safe to expose in URLs, and works well in distributed systems.

  - username & email unique constraints: enforced at DB level, not just app
    level. Even if two concurrent requests slip through Python validation,
    the DB will reject the second insert with an IntegrityError.

  - password_hash: plaintext passwords are NEVER stored. bcrypt hashes are
    stored here. See app/core/security.py.

  - created_at with timezone=True: always store UTC. This makes timezone
    arithmetic unambiguous when Day 2+ adds game sessions with timestamps.

  - Separate ORM model from Pydantic schemas: SQLAlchemy models define the
    DB structure; Pydantic schemas define the API contract. Mixing them
    would expose internal fields (like password_hash) in API responses.

Future extension points (Day 2+):
  - `game_sessions` will have a FK → users.id
  - `scores` will reference both users and game_sessions
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List

from sqlalchemy import DateTime, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.game_session import GameSession
    from app.models.score import Score


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
        nullable=False,
    )

    # ── Relationships (back-refs for Day 2 models) ────────────────────────────
    game_sessions: Mapped[List["GameSession"]] = relationship(
        "GameSession", back_populates="user", cascade="all, delete-orphan"
    )
    scores: Mapped[List["Score"]] = relationship(
        "Score", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r}>"
