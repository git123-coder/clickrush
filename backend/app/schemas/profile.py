"""
app/schemas/profile.py
───────────────────────
Pydantic response schemas for the user profile endpoints.

Design:
  - GameHistoryEntry is flat (no nested ORM objects) — consistent with the
    leaderboard schema pattern.
  - UserRankingsResponse uses Optional[int] for all ranks/personal_best:
      None means "no qualifying score in this time window" → frontend shows
      "Unranked" rather than an error or a misleading 0.
  - total in GameHistoryResponse lets the frontend decide whether to show
    a "load more" button without issuing a second COUNT query.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GameHistoryEntry(BaseModel):
    """One row in the user's completed-game history."""

    game_id: uuid.UUID
    clicks: int
    started_at: datetime
    finished_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GameHistoryResponse(BaseModel):
    """Paginated list of the user's completed games."""

    games: list[GameHistoryEntry]
    total: int  # total completed games for this user (for pagination UI)


class UserRankingsResponse(BaseModel):
    """
    Current rankings for the logged-in user across all three leaderboard windows.

    Each field is None when the user has no qualifying score in that window.
    This avoids ambiguity between "rank 0" and "not on the board".
    """

    personal_best: int | None
    global_rank: int | None
    daily_rank: int | None
    weekly_rank: int | None
