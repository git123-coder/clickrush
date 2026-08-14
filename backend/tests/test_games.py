"""
tests/test_games.py
────────────────────
Automated tests for Day 2 game session and score functionality.

Covers all 15 test cases from the spec:
  1.  Authenticated user can start a game.
  2.  Unauthenticated user cannot start a game.
  3.  Game session is persisted.
  4.  started_at and expires_at are populated correctly.
  5.  User cannot start another active game.
  6.  Valid game can be finished.
  7.  Score is persisted.
  8.  Game session becomes completed.
  9.  Negative clicks are rejected.
  10. Excessively large click count is rejected.
  11. Another user cannot finish someone else's game.
  12. Completed game cannot be finished twice.
  13. Missing/invalid game ID is rejected.
  14. Expired game cannot be submitted as valid.
  15. End-to-end game flow works.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models.game_session import GAME_DURATION_SECONDS, GRACE_PERIOD_SECONDS, GameSession, GameStatus
from app.models.score import MAX_CLICKS_PER_GAME, Score


# ── Helpers ───────────────────────────────────────────────────────────────────

def start_game(client, headers):
    return client.post("/api/games/start", headers=headers)


def finish_game(client, game_id, clicks, headers):
    return client.post(f"/api/games/{game_id}/finish", json={"clicks": clicks}, headers=headers)


# ── 1. Authenticated user can start a game ────────────────────────────────────

def test_start_game_authenticated(client, auth_headers):
    resp = start_game(client, auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert "game_id" in data
    assert "started_at" in data
    assert "expires_at" in data
    assert data["duration_seconds"] == 60


# ── 2. Unauthenticated user cannot start a game ───────────────────────────────

def test_start_game_unauthenticated(client):
    resp = client.post("/api/games/start")
    assert resp.status_code == 403  # HTTPBearer returns 403 when no token


# ── 3. Game session is persisted ──────────────────────────────────────────────

def test_game_session_persisted_in_db(client, auth_headers, db_session, registered_user):
    resp = start_game(client, auth_headers)
    assert resp.status_code == 201
    game_id = uuid.UUID(resp.json()["game_id"])
    session = db_session.get(GameSession, game_id)
    assert session is not None
    assert str(session.user_id) == registered_user["id"]
    assert session.status == GameStatus.active


# ── 4. started_at and expires_at are populated correctly ─────────────────────

def test_game_timestamps(client, auth_headers):
    before = datetime.now(timezone.utc)
    resp = start_game(client, auth_headers)
    after = datetime.now(timezone.utc)

    assert resp.status_code == 201
    data = resp.json()

    started_at = datetime.fromisoformat(data["started_at"])
    expires_at = datetime.fromisoformat(data["expires_at"])

    # started_at should be within the test window
    assert before <= started_at <= after

    # expires_at should be exactly GAME_DURATION_SECONDS after started_at
    expected_duration = timedelta(seconds=GAME_DURATION_SECONDS)
    actual_duration = expires_at - started_at
    # Allow 2-second tolerance for slow systems
    assert abs(actual_duration - expected_duration).total_seconds() < 2


# ── 5. User cannot start another active game ──────────────────────────────────

def test_cannot_start_duplicate_active_game(client, auth_headers):
    r1 = start_game(client, auth_headers)
    assert r1.status_code == 201

    r2 = start_game(client, auth_headers)
    assert r2.status_code == 409
    assert "active" in r2.json()["detail"].lower()


# ── 6. Valid game can be finished ─────────────────────────────────────────────

def test_finish_game_valid(client, auth_headers):
    game_id = start_game(client, auth_headers).json()["game_id"]
    resp = finish_game(client, game_id, 42, auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["clicks"] == 42
    assert data["game_id"] == game_id
    assert data["status"] == "completed"
    assert data["finished_at"] is not None


# ── 7. Score is persisted in DB ───────────────────────────────────────────────

def test_score_persisted_in_db(client, auth_headers, db_session, registered_user):
    game_id = uuid.UUID(start_game(client, auth_headers).json()["game_id"])
    finish_game(client, str(game_id), 100, auth_headers)

    score = db_session.query(Score).filter_by(game_session_id=game_id).first()
    assert score is not None
    assert score.clicks == 100
    assert str(score.user_id) == registered_user["id"]


# ── 8. Game session becomes completed ─────────────────────────────────────────

def test_session_status_completed(client, auth_headers, db_session):
    game_id = uuid.UUID(start_game(client, auth_headers).json()["game_id"])
    finish_game(client, str(game_id), 55, auth_headers)

    session = db_session.get(GameSession, game_id)
    db_session.refresh(session)
    assert session.status == GameStatus.completed
    assert session.finished_at is not None


# ── 9. Negative clicks are rejected ──────────────────────────────────────────

def test_negative_clicks_rejected(client, auth_headers):
    game_id = start_game(client, auth_headers).json()["game_id"]
    resp = finish_game(client, game_id, -1, auth_headers)
    assert resp.status_code == 422


# ── 10. Excessively large click count is rejected ────────────────────────────

def test_max_clicks_exceeded(client, auth_headers):
    game_id = start_game(client, auth_headers).json()["game_id"]
    resp = finish_game(client, game_id, MAX_CLICKS_PER_GAME + 1, auth_headers)
    assert resp.status_code == 422


# ── 11. Another user cannot finish someone else's game ────────────────────────

def test_cannot_finish_another_users_game(client, auth_headers, second_user_headers):
    game_id = start_game(client, auth_headers).json()["game_id"]
    resp = finish_game(client, game_id, 50, second_user_headers)
    assert resp.status_code == 403


# ── 12. Completed game cannot be finished twice ───────────────────────────────

def test_cannot_finish_completed_game_twice(client, auth_headers):
    game_id = start_game(client, auth_headers).json()["game_id"]
    finish_game(client, game_id, 30, auth_headers)
    resp = finish_game(client, game_id, 30, auth_headers)
    assert resp.status_code == 409


# ── 13. Missing/invalid game ID is rejected ───────────────────────────────────

def test_invalid_game_id_rejected(client, auth_headers):
    fake_id = str(uuid.uuid4())
    resp = finish_game(client, fake_id, 10, auth_headers)
    assert resp.status_code == 404


def test_malformed_game_id_rejected(client, auth_headers):
    resp = finish_game(client, "not-a-uuid", 10, auth_headers)
    assert resp.status_code == 422


# ── 14. Expired game cannot be submitted ─────────────────────────────────────

def test_expired_game_rejected(client, auth_headers, db_session):
    """Manually backdate the session so it appears expired."""
    game_id = uuid.UUID(start_game(client, auth_headers).json()["game_id"])

    # Force the session into the past beyond grace period
    session = db_session.get(GameSession, game_id)
    past = datetime.now(timezone.utc) - timedelta(
        seconds=GAME_DURATION_SECONDS + GRACE_PERIOD_SECONDS + 5
    )
    session.started_at = past
    session.expires_at = past + timedelta(seconds=GAME_DURATION_SECONDS)
    db_session.commit()

    resp = finish_game(client, str(game_id), 20, auth_headers)
    assert resp.status_code == 410  # Gone


# ── 15. End-to-end game flow ─────────────────────────────────────────────────

def test_end_to_end_game_flow(client):
    """Full flow: signup → login → start → finish → new game."""
    # Signup
    client.post("/api/auth/signup", json={
        "username": "e2e_player",
        "email": "e2e@clickrush.dev",
        "password": "e2epassword",
    })

    # Login
    token = client.post("/api/auth/login", json={
        "email": "e2e@clickrush.dev",
        "password": "e2epassword",
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Start game
    start_resp = client.post("/api/games/start", headers=headers)
    assert start_resp.status_code == 201
    game_id = start_resp.json()["game_id"]

    # Cannot start another while active
    dup = client.post("/api/games/start", headers=headers)
    assert dup.status_code == 409

    # Finish the game
    finish_resp = client.post(
        f"/api/games/{game_id}/finish",
        json={"clicks": 150},
        headers=headers,
    )
    assert finish_resp.status_code == 200
    data = finish_resp.json()
    assert data["clicks"] == 150
    assert data["status"] == "completed"

    # Can start a fresh game after completing
    new_resp = client.post("/api/games/start", headers=headers)
    assert new_resp.status_code == 201
    assert new_resp.json()["game_id"] != game_id


# ── Day 1 auth regression (ensure nothing is broken) ─────────────────────────

def test_day1_signup_still_works(client):
    resp = client.post("/api/auth/signup", json={
        "username": "regression_user",
        "email": "regression@clickrush.dev",
        "password": "regpassword",
    })
    assert resp.status_code == 201
    assert "password_hash" not in resp.json()


def test_day1_login_still_works(client):
    client.post("/api/auth/signup", json={
        "username": "logintest",
        "email": "logintest@clickrush.dev",
        "password": "loginpass",
    })
    resp = client.post("/api/auth/login", json={
        "email": "logintest@clickrush.dev",
        "password": "loginpass",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_day1_protected_endpoint_still_works(client, auth_headers, registered_user):
    resp = client.get("/api/users/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == registered_user["username"]
    assert "password_hash" not in data
