import asyncio
from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
with engine.begin() as conn:
    conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE;"))
    conn.execute(text("DROP TABLE IF EXISTS scores CASCADE;"))
    conn.execute(text("DROP TABLE IF EXISTS game_sessions CASCADE;"))
    conn.execute(text("DROP TABLE IF EXISTS users CASCADE;"))
    conn.execute(text("DROP TYPE IF EXISTS gamestatus CASCADE;"))
