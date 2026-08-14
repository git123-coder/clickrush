"""
app/db/session.py
─────────────────
Database engine, session factory, and FastAPI dependency.

Why SQLAlchemy?
  - Abstracts raw SQL behind a Pythonic ORM while still letting us write
    efficient queries when needed.
  - SQLAlchemy 2.x style uses explicit typing and the new Session API.
  - Connection pooling is handled automatically by the engine.

Why a get_db() dependency?
  - FastAPI's dependency injection system calls get_db() for every request
    and ensures the session is always closed, even on exceptions.
  - This "session-per-request" pattern prevents connection leaks and keeps
    transactions scoped correctly.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# ── Engine ───────────────────────────────────────────────────────────────────
# pool_pre_ping=True makes SQLAlchemy test connections before using them,
# which handles stale connections from idle pools gracefully.
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# ── Session factory ───────────────────────────────────────────────────────────
# autocommit=False → we manage transactions explicitly (commit / rollback).
# autoflush=False  → we flush manually before queries when needed.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Dependency ────────────────────────────────────────────────────────────────

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session.

    Usage in route:
        def my_endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
