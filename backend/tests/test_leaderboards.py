"""
tests/test_leaderboards.py
───────────────────────────
Automated tests for Day 3 leaderboard endpoints.

Test coverage:
  1. Global leaderboard returns correct ranking order (highest clicks first).
  2. A user's multiple scores produce only their single best entry.
  3. Daily leaderboard excludes scores from yesterday (older than today).
  4. Weekly leaderboard excludes scores older than 7 days.
  5. Daily leaderboard correctly includes scores from earlier today.
  6. Weekly leaderboard correctly includes scores from 6 days ago.
  7. Empty leaderboard returns 200 with an empty list.
  8. limit parameter is respected.
  9. limit above cap (> 100) returns 422.
  10. Day 1 + Day 2 regression: existing tests still pass (run separately).
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.db.session import SessionLocal
from app.models.game_session import GAME_DURATION_SECONDS, GameSession, GameStatus
from app.models.score import Score


# ── Helpers ───────────────────────────────────────────────────────────────────

def _register_and_login(client, username: str, email: str, password: str) -> dict:
    """Sign up + log in a user, return auth headers."""
    client.post("/api/auth/signup", json={
        "username": username,
        "email": email,
        "password": password,
    })
    token = client.post("/api/auth/login", json={
        "email": email,
        "password": password,
    }).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _insert_score(db, user_id: uuid.UUID, clicks: int, created_at: datetime) -> Score:
    """
    Insert a pre-built completed game session + score with an explicit
    created_at timestamp so tests can simulate past/present scores.
    """
    now = datetime.now(timezone.utc)
    session = GameSession(
        user_id=user_id,
        started_at=created_at - timedelta(seconds=GAME_DURATION_SECONDS),
        expires_at=created_at,
        finished_at=created_at,
        status=GameStatus.completed,
    )
    db.add(session)
    db.flush()

    score = Score(
        game_session_id=session.id,
        user_id=user_id,
        clicks=clicks,
        created_at=created_at,
    )
    db.add(score)
    db.commit()
    return score


def _user_id(client, auth_headers) -> uuid.UUID:
    """Fetch the UUID of the currently authenticated user."""
    me = client.get("/api/users/me", headers=auth_headers).json()
    return uuid.UUID(me["id"])


# ── 1. Global ranking order ───────────────────────────────────────────────────

def test_global_leaderboard_ranking_order(client, db_session):
    """Users are ordered by clicks DESC, earlier score wins ties."""
    h1 = _register_and_login(client, "lb_alice", "lb_alice@test.dev", "pass1234")
    h2 = _register_and_login(client, "lb_bob",   "lb_bob@test.dev",   "pass1234")
    h3 = _register_and_login(client, "lb_carol", "lb_carol@test.dev", "pass1234")

    now = datetime.now(timezone.utc)
    uid1 = _user_id(client, h1)
    uid2 = _user_id(client, h2)
    uid3 = _user_id(client, h3)

    _insert_score(db_session, uid1, 300, now - timedelta(minutes=5))
    _insert_score(db_session, uid2, 500, now - timedelta(minutes=4))
    _insert_score(db_session, uid3, 200, now - timedelta(minutes=3))

    resp = client.get("/api/leaderboards/global")
    assert resp.status_code == 200
    entries = resp.json()["entries"]

    # Find ranks for our three users
    by_user = {e["username"]: e for e in entries}
    assert "lb_alice" in by_user
    assert "lb_bob"   in by_user
    assert "lb_carol" in by_user

    assert by_user["lb_bob"]["clicks"]   == 500
    assert by_user["lb_alice"]["clicks"] == 300
    assert by_user["lb_carol"]["clicks"] == 200

    assert by_user["lb_bob"]["rank"]   < by_user["lb_alice"]["rank"]
    assert by_user["lb_alice"]["rank"] < by_user["lb_carol"]["rank"]


# ── 2. Best-per-user (multiple games → single leaderboard entry) ──────────────

def test_global_leaderboard_best_per_user(client, db_session):
    """User with multiple scores appears only once (their best score)."""
    h = _register_and_login(client, "lb_multi", "lb_multi@test.dev", "pass1234")
    uid = _user_id(client, h)
    now = datetime.now(timezone.utc)

    _insert_score(db_session, uid, 100, now - timedelta(hours=2))
    _insert_score(db_session, uid, 400, now - timedelta(hours=1))  # personal best
    _insert_score(db_session, uid, 200, now - timedelta(minutes=30))

    resp = client.get("/api/leaderboards/global")
    assert resp.status_code == 200
    entries = resp.json()["entries"]

    user_entries = [e for e in entries if e["username"] == "lb_multi"]
    assert len(user_entries) == 1, "User must appear exactly once"
    assert user_entries[0]["clicks"] == 400, "Must show personal best"


# ── 3. Daily excludes yesterday's scores ────────────────────────────────────

def test_daily_leaderboard_excludes_yesterday(client, db_session):
    """A score from yesterday must not appear on today's daily leaderboard."""
    h = _register_and_login(client, "lb_yest", "lb_yest@test.dev", "pass1234")
    uid = _user_id(client, h)
    now = datetime.now(timezone.utc)

    # Score from yesterday (> 24 h ago)
    yesterday = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(seconds=1)
    _insert_score(db_session, uid, 999, yesterday)

    resp = client.get("/api/leaderboards/daily")
    assert resp.status_code == 200
    entries = resp.json()["entries"]
    assert not any(e["username"] == "lb_yest" for e in entries), \
        "Yesterday's score must not appear on daily board"


# ── 4. Weekly excludes scores older than 7 days ──────────────────────────────

def test_weekly_leaderboard_excludes_old_scores(client, db_session):
    """A score from 8 days ago must not appear on the weekly leaderboard."""
    h = _register_and_login(client, "lb_old", "lb_old@test.dev", "pass1234")
    uid = _user_id(client, h)
    now = datetime.now(timezone.utc)

    _insert_score(db_session, uid, 777, now - timedelta(days=8))

    resp = client.get("/api/leaderboards/weekly")
    assert resp.status_code == 200
    entries = resp.json()["entries"]
    assert not any(e["username"] == "lb_old" for e in entries), \
        "Score older than 7 days must not appear on weekly board"


# ── 5. Daily includes scores from earlier today ──────────────────────────────

def test_daily_leaderboard_includes_today(client, db_session):
    """A score from 1 hour ago (same UTC day) must appear on today's board."""
    h = _register_and_login(client, "lb_today", "lb_today@test.dev", "pass1234")
    uid = _user_id(client, h)
    now = datetime.now(timezone.utc)

    # Only insert if 1 hour ago is still the same UTC day
    score_time = now - timedelta(hours=1)
    if score_time.date() == now.date():
        _insert_score(db_session, uid, 350, score_time)

        resp = client.get("/api/leaderboards/daily")
        assert resp.status_code == 200
        entries = resp.json()["entries"]
        assert any(e["username"] == "lb_today" for e in entries), \
            "Score from 1 hour ago must appear on daily board"


# ── 6. Weekly includes scores from 6 days ago ────────────────────────────────

def test_weekly_leaderboard_includes_recent(client, db_session):
    """A score from 6 days ago must appear on the weekly leaderboard."""
    h = _register_and_login(client, "lb_recent", "lb_recent@test.dev", "pass1234")
    uid = _user_id(client, h)
    now = datetime.now(timezone.utc)

    _insert_score(db_session, uid, 600, now - timedelta(days=6))

    resp = client.get("/api/leaderboards/weekly")
    assert resp.status_code == 200
    entries = resp.json()["entries"]
    assert any(e["username"] == "lb_recent" for e in entries), \
        "Score from 6 days ago must appear on weekly board"


# ── 7. Empty leaderboard → 200 with empty list ───────────────────────────────

def test_empty_daily_leaderboard_returns_200(client):
    """Daily board with no scores returns 200 + empty list, not an error."""
    # Rely on the fact that this test DB starts fresh for each test function
    resp = client.get("/api/leaderboards/daily")
    assert resp.status_code == 200
    data = resp.json()
    assert "entries" in data
    assert isinstance(data["entries"], list)


def test_empty_global_leaderboard_returns_200(client):
    resp = client.get("/api/leaderboards/global")
    assert resp.status_code == 200
    assert isinstance(resp.json()["entries"], list)


def test_empty_weekly_leaderboard_returns_200(client):
    resp = client.get("/api/leaderboards/weekly")
    assert resp.status_code == 200
    assert isinstance(resp.json()["entries"], list)


# ── 8. limit parameter is respected ─────────────────────────────────────────

def test_limit_is_respected(client, db_session):
    """Requesting limit=2 returns at most 2 entries."""
    for i in range(5):
        h = _register_and_login(
            client,
            f"lb_lim{i}", f"lb_lim{i}@test.dev", "pass1234",
        )
        uid = _user_id(client, h)
        _insert_score(db_session, uid, 100 + i * 50, datetime.now(timezone.utc))

    resp = client.get("/api/leaderboards/global?limit=2")
    assert resp.status_code == 200
    assert len(resp.json()["entries"]) <= 2


# ── 9. limit above cap (> 100) → 422 ─────────────────────────────────────────

def test_limit_above_cap_is_rejected(client):
    """limit=101 must be rejected with 422 Unprocessable Entity."""
    resp = client.get("/api/leaderboards/global?limit=101")
    assert resp.status_code == 422


def test_limit_zero_is_rejected(client):
    """limit=0 must be rejected with 422 Unprocessable Entity."""
    resp = client.get("/api/leaderboards/global?limit=0")
    assert resp.status_code == 422


# ── 10. Tie-breaking: earlier score wins better rank ────────────────────────

def test_tie_breaking_earlier_wins(client, db_session):
    """Two users with the same clicks: earlier created_at gets rank 1."""
    h1 = _register_and_login(client, "lb_tie1", "lb_tie1@test.dev", "pass1234")
    h2 = _register_and_login(client, "lb_tie2", "lb_tie2@test.dev", "pass1234")
    uid1 = _user_id(client, h1)
    uid2 = _user_id(client, h2)
    now = datetime.now(timezone.utc)

    _insert_score(db_session, uid1, 250, now - timedelta(hours=2))  # earlier
    _insert_score(db_session, uid2, 250, now - timedelta(hours=1))  # later

    resp = client.get("/api/leaderboards/global")
    assert resp.status_code == 200
    entries = resp.json()["entries"]
    by_user = {e["username"]: e for e in entries}

    assert by_user["lb_tie1"]["rank"] < by_user["lb_tie2"]["rank"], \
        "Earlier identical score must rank higher"
