"""
alembic/env.py
──────────────
Alembic migration environment.

Key design decisions:
  - We import `Base` and all models so autogenerate can detect schema changes.
  - DATABASE_URL comes from the same .env the application uses — single source
    of truth, no separate alembic database config to drift out of sync.
  - run_migrations_online() is the only mode we need for a hosted DB.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make sure 'app' package is importable from the backend root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import Base and all models so Alembic's autogenerate can see the full schema
from app.db.base import Base  # noqa: E402
import app.models  # noqa: E402, F401  — registers all models on Base.metadata

from app.core.config import settings  # noqa: E402

# ── Alembic Config ────────────────────────────────────────────────────────────
config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# ── Migration helpers ─────────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """Emit SQL to stdout without a live DB connection (for review/preview)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against the live PostgreSQL database."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
