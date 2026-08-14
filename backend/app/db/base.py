"""
app/db/base.py
──────────────
SQLAlchemy declarative base.

Why a separate base module?
  - Centralises the ORM base so all models import from one place.
  - Alembic's env.py imports this Base to discover models for autogenerate.
  - Avoids circular imports between models and session code.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Common SQLAlchemy declarative base for all ORM models."""
    pass
