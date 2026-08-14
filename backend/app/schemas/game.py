"""
app/schemas/game.py
───────────────────
Pydantic schemas for the game session and score API.

Separate from ORM models so:
  - The API contract is explicit and documented in Swagger.
  - SQLAlchemy internals (relationships, lazy loading) never leak.
  - Response shapes can evolve independently from the DB schema.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.game_session import GameStatus


class StartGameResponse(BaseModel):
    """Response for POST /api/games/start."""

    game_id: uuid.UUID
    started_at: datetime
    expires_at: datetime
    duration_seconds: int = 60

    model_config = ConfigDict(from_attributes=True)


class FinishGameRequest(BaseModel):
    """Request body for POST /api/games/{game_id}/finish."""

    clicks: int = Field(
        ...,
        ge=0,
        description="Total clicks recorded during the game. Must be >= 0.",
    )


class FinishGameResponse(BaseModel):
    """Response for POST /api/games/{game_id}/finish."""

    game_id: uuid.UUID
    clicks: int
    started_at: datetime
    finished_at: datetime
    status: GameStatus

    model_config = ConfigDict(from_attributes=True)
