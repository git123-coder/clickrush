"""
tests/conftest.py
─────────────────
Pytest fixtures for the ClickRush test suite.

Test database strategy:
  - Uses the same DATABASE_URL as development but wraps EVERY test in a
    transaction that is rolled back after the test completes.
  - This means tests never persist data and never interfere with each other
    or the development database.
  - The approach uses SQLAlchemy's connection-level transaction rollback:
    1. Open a connection and BEGIN a transaction.
    2. Override the get_db dependency to use that connection's savepoint.
    3. After each test, ROLLBACK the outer transaction → all changes vanish.

This is faster than truncating tables and avoids needing a separate test DB.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app


# ── Database fixture ─────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def engine():
    """One engine for the whole test session."""
    return create_engine(settings.DATABASE_URL, pool_pre_ping=True)


@pytest.fixture()
def db_session(engine):
    """
    Yield a database session whose transaction is rolled back after each test.
    Uses nested transactions (SAVEPOINTs) so application code can still
    call commit() without permanently persisting data.
    """
    connection = engine.connect()
    transaction = connection.begin()

    # Bind a session to this specific connection
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = TestingSession()

    # Intercept session.commit() calls and replace them with SAVEPOINTs
    # so application code can still call commit() but nothing is truly committed.
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    """
    FastAPI TestClient with the get_db dependency overridden to use
    the test session (so all requests share the rolled-back transaction).
    """
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Auth helper fixtures ──────────────────────────────────────────────────────

@pytest.fixture()
def registered_user(client):
    """Create and return a test user via the signup endpoint."""
    resp = client.post("/api/auth/signup", json={
        "username": "testplayer",
        "email": "testplayer@clickrush.dev",
        "password": "testpass123",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture()
def auth_token(client, registered_user):
    """Log in the test user and return the Bearer token."""
    resp = client.post("/api/auth/login", json={
        "email": "testplayer@clickrush.dev",
        "password": "testpass123",
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture()
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture()
def second_user_headers(client):
    """A second user's auth headers — used to test cross-user access."""
    client.post("/api/auth/signup", json={
        "username": "otherplayer",
        "email": "other@clickrush.dev",
        "password": "otherpass123",
    })
    resp = client.post("/api/auth/login", json={
        "email": "other@clickrush.dev",
        "password": "otherpass123",
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
