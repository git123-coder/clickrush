"""
app/schemas/leaderboard.py
──────────────────────────
Pydantic response schemas for the leaderboard API.

Design decisions:
  - LeaderboardEntry is intentionally flat (no nested objects) so the
    frontend can render rows without any extra unwrapping.
  - `achieved_at` uses the score's created_at, which is always UTC-aware.
  - `rank` is computed by the database (ROW_NUMBER) — not assigned here —
    so callers never need to enumerate a list themselves.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LeaderboardEntry(BaseModel):
    """One row in a leaderboard response."""

    rank: int
    username: str
    clicks: int
    achieved_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeaderboardResponse(BaseModel):
    """Wrapper returned by every leaderboard endpoint."""

    entries: list[LeaderboardEntry]
