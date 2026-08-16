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


# ── 5. User can start a new game which abandons previous active ones ────────

def test_repeated_new_game_behavior(client, auth_headers, db_session):
    # Start Game 1
    r1 = start_game(client, auth_headers)
    assert r1.status_code == 201
    g1_id = uuid.UUID(r1.json()["game_id"])

    # Start Game 2
    r2 = start_game(client, auth_headers)
    assert r2.status_code == 201
    g2_id = uuid.UUID(r2.json()["game_id"])
    assert g1_id != g2_id

    # Start Game 3
    r3 = start_game(client, auth_headers)
    assert r3.status_code == 201
    g3_id = uuid.UUID(r3.json()["game_id"])
    assert g2_id != g3_id

    # Verify state: 1 and 2 expired, 3 active
    g1 = db_session.get(GameSession, g1_id)
    g2 = db_session.get(GameSession, g2_id)
    g3 = db_session.get(GameSession, g3_id)
    
    db_session.refresh(g1)
    db_session.refresh(g2)
    db_session.refresh(g3)

    assert g1.status == GameStatus.expired
    assert g2.status == GameStatus.expired
    assert g3.status == GameStatus.active
    
    # Verify DB only has 1 active session for user
    active_count = db_session.query(GameSession).filter_by(
        user_id=g1.user_id, status=GameStatus.active
    ).count()
    assert active_count == 1


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

    # Starting another abandons the previous and succeeds
    dup = client.post("/api/games/start", headers=headers)
    assert dup.status_code == 201
    game_id = dup.json()["game_id"]

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


# ── Dangling Active Sessions bug-fix regression tests ──────────────────────────

def test_abandoned_session_does_not_block_new_game(client, auth_headers, db_session):
    """Test 1: Existing active session is abandoned."""
    start_resp = start_game(client, auth_headers)
    assert start_resp.status_code == 201
    game_id = uuid.UUID(start_resp.json()["game_id"])

    # User starts a new game
    new_resp = start_game(client, auth_headers)
    assert new_resp.status_code == 201
    new_game_id = uuid.UUID(new_resp.json()["game_id"])
    assert game_id != new_game_id

    # The old session must have been flipped to expired
    session = db_session.get(GameSession, game_id)
    new_session = db_session.get(GameSession, new_game_id)
    db_session.refresh(session)
    db_session.refresh(new_session)
    
    assert session.status == GameStatus.expired
    assert new_session.status == GameStatus.active

def test_still_active_session_still_abandoned(client, auth_headers, db_session):
    """
    Test 2: Active session that has not expired yet is abandoned.
    """
    r1 = start_game(client, auth_headers)
    assert r1.status_code == 201
    g1_id = uuid.UUID(r1.json()["game_id"])

    # Verify it is still far in the future
    session = db_session.get(GameSession, g1_id)
    assert session.expires_at > datetime.now(timezone.utc)

    # Calling start again must immediately abandon it, not block
    r2 = start_game(client, auth_headers)
    assert r2.status_code == 201
    
    db_session.refresh(session)
    assert session.status == GameStatus.expired

def test_abandoned_session_cannot_receive_score(client, auth_headers, db_session):
    """
    Test 3: Old session cannot receive a score.
    """
    r1 = start_game(client, auth_headers)
    assert r1.status_code == 201
    g1_id = uuid.UUID(r1.json()["game_id"])

    # Start new game abandons the first
    start_game(client, auth_headers)
    
    session = db_session.get(GameSession, g1_id)
    db_session.refresh(session)
    assert session.status == GameStatus.expired

    # Attempt to finish old session
    resp = finish_game(client, str(g1_id), 30, auth_headers)
    assert resp.status_code == 410
    
    # Verify no score was saved
    score = db_session.query(Score).filter_by(game_session_id=g1_id).first()
    assert score is None
    
    # Remains expired
    db_session.refresh(session)
    assert session.status == GameStatus.expired


# ── TOCTOU Concurrency Test ───────────────────────────────────────────────────

def test_start_game_concurrency_race(engine):
    """
    Simulates a true TOCTOU race condition using two separate threads and DB sessions,
    synchronized so both pass the application-level 'is there an active game' check 
    before either commits. The database unique partial index must block the second one.
    """
    import threading
    import uuid
    from unittest.mock import patch
    from sqlalchemy.orm import sessionmaker
    from fastapi import HTTPException
    from app.services.game_service import start_game, _get_existing_active_session
    from app.models.user import User

    SessionLocal = sessionmaker(bind=engine)
    
    # 1. Setup a real user in the DB outside the nested transaction fixture
    setup_db = SessionLocal()
    user = User(
        username=f"racer_{uuid.uuid4().hex[:8]}", 
        email=f"racer_{uuid.uuid4().hex[:8]}@clickrush.dev", 
        password_hash="hash"
    )
    setup_db.add(user)
    setup_db.commit()
    user_id = user.id
    setup_db.close()

    barrier = threading.Barrier(2)
    results = []

    real_get_existing_active = _get_existing_active_session

    def synchronized_get_existing_active(db, uid):
        # Perform the actual check (will return None for both threads)
        res = real_get_existing_active(db, uid)
        # Synchronize both threads right after the check, before they insert
        barrier.wait(timeout=5)
        return res

    def racer():
        db = SessionLocal()
        try:
            session = start_game(db, user_id)
            results.append(session.id)
        except HTTPException as e:
            results.append(e.status_code)
        except Exception as e:
            results.append(e)
        finally:
            db.close()

    with patch("app.services.game_service._get_existing_active_session", side_effect=synchronized_get_existing_active):
        t1 = threading.Thread(target=racer)
        t2 = threading.Thread(target=racer)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

    # 2. Verify results: exactly one 201 (UUID) and one 409
    successes = [r for r in results if isinstance(r, uuid.UUID)]
    conflicts = [r for r in results if r == 409]

    # 3. Cleanup DB before asserting so we don't leave garbage if assert fails
    cleanup_db = SessionLocal()
    active_count = cleanup_db.query(GameSession).filter_by(user_id=user_id, status=GameStatus.active).count()
    cleanup_db.query(GameSession).filter_by(user_id=user_id).delete()
    cleanup_db.query(User).filter_by(id=user_id).delete()
    cleanup_db.commit()
    cleanup_db.close()

    # Assertions
    assert len(successes) == 1, f"Exactly one game should be created. Results: {results}"
    assert len(conflicts) == 1, f"The other concurrent request should hit the DB unique constraint and return 409. Results: {results}"
    assert active_count == 1, "Only one active session should exist in the database for the user."
