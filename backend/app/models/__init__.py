"""
app/models/__init__.py

Import all models here so that Alembic's env.py can discover them
simply by importing this package.

Order matters: User must be imported before models that FK to it.
"""

from app.models.user import User  # noqa: F401
from app.models.game_session import GameSession  # noqa: F401
from app.models.score import Score  # noqa: F401

__all__ = ["User", "GameSession", "Score"]
