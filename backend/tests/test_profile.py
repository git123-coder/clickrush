"""
tests/test_profile.py
──────────────────────
Automated tests for Day 4 profile endpoints:
  GET /api/users/me/games
  GET /api/users/me/rankings

Coverage:
  1.  Authenticated user gets only their own game history (not another user's).
  2.  History is ordered most recent first.
  3.  Only completed games appear (abandoned / expired sessions are excluded).
  4.  Pagination: limit and offset work correctly.
  5.  limit above cap (> 50) → 422.
  6.  limit=0 → 422.
  7.  negative offset → 422.
  8.  Rankings: correct personal_best.
  9.  Rankings: global_rank matches the public /api/leaderboards/global endpoint.
  10. Rankings: daily_rank matches the public /api/leaderboards/daily endpoint.
  11. Rankings: weekly_rank matches the public /api/leaderboards/weekly endpoint.
  12. User with no scores → empty history, all rankings null.
  13. Unauthenticated /me/games → 401.
  14. Unauthenticated /me/rankings → 401.
  15. Day 1 + Day 2 + Day 3 tests unaffected (run separately via pytest tests/).
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models.game_session import GAME_DURATION_SECONDS, GameSession, GameStatus
from app.models.score import Score


# ── Helpers ───────────────────────────────────────────────────────────────────

def _signup_login(client, username: str, email: str, password: str = "pass1234") -> dict:
    client.post("/api/auth/signup", json={"username": username, "email": email, "password": password})
    token = client.post("/api/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _user_id(client, headers) -> uuid.UUID:
    return uuid.UUID(client.get("/api/users/me", headers=headers).json()["id"])


def _insert_score(db, user_id: uuid.UUID, clicks: int, created_at: datetime) -> Score:
    """Insert a completed game session + score with an explicit timestamp."""
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


def _insert_expired_session(db, user_id: uuid.UUID) -> GameSession:
    """Insert an expired (abandoned) session with no score."""
    now = datetime.now(timezone.utc)
    session = GameSession(
        user_id=user_id,
        started_at=now - timedelta(seconds=120),
        expires_at=now - timedelta(seconds=60),
        finished_at=None,
        status=GameStatus.expired,
    )
    db.add(session)
    db.commit()
    return session


# ── 1. Own data only ──────────────────────────────────────────────────────────

def test_game_history_own_data_only(client, db_session):
    """User A must not see User B's games."""
    h_a = _signup_login(client, "prof_alice", "prof_alice@t.dev")
    h_b = _signup_login(client, "prof_bob",   "prof_bob@t.dev")
    uid_a = _user_id(client, h_a)
    uid_b = _user_id(client, h_b)
    now = datetime.now(timezone.utc)

    _insert_score(db_session, uid_a, 100, now - timedelta(minutes=10))
    _insert_score(db_session, uid_b, 200, now - timedelta(minutes=5))

    resp_a = client.get("/api/users/me/games", headers=h_a).json()
    resp_b = client.get("/api/users/me/games", headers=h_b).json()

    assert len(resp_a["games"]) == 1
    assert resp_a["games"][0]["clicks"] == 100

    assert len(resp_b["games"]) == 1
    assert resp_b["games"][0]["clicks"] == 200


# ── 2. Most recent first ──────────────────────────────────────────────────────

def test_game_history_most_recent_first(client, db_session):
    """Games are returned ordered by finished_at DESC."""
    h = _signup_login(client, "prof_order", "prof_order@t.dev")
    uid = _user_id(client, h)
    now = datetime.now(timezone.utc)

    _insert_score(db_session, uid, 50,  now - timedelta(hours=3))  # oldest
    _insert_score(db_session, uid, 150, now - timedelta(hours=2))  # middle
    _insert_score(db_session, uid, 100, now - timedelta(hours=1))  # most recent

    games = client.get("/api/users/me/games", headers=h).json()["games"]
    assert len(games) == 3
    assert games[0]["clicks"] == 100  # most recent
    assert games[1]["clicks"] == 150
    assert games[2]["clicks"] == 50   # oldest


# ── 3. Only completed games ───────────────────────────────────────────────────

def test_game_history_excludes_expired_sessions(client, db_session):
    """Abandoned/expired sessions with no score must not appear in history."""
    h = _signup_login(client, "prof_expired", "prof_expired@t.dev")
    uid = _user_id(client, h)
    now = datetime.now(timezone.utc)

    _insert_expired_session(db_session, uid)          # should NOT appear
    _insert_score(db_session, uid, 75, now)            # should appear

    resp = client.get("/api/users/me/games", headers=h).json()
    assert resp["total"] == 1
    assert len(resp["games"]) == 1
    assert resp["games"][0]["clicks"] == 75


# ── 4. Pagination ─────────────────────────────────────────────────────────────

def test_pagination_limit_offset(client, db_session):
    """limit and offset slice the history correctly."""
    h = _signup_login(client, "prof_page", "prof_page@t.dev")
    uid = _user_id(client, h)
    now = datetime.now(timezone.utc)

    # Insert 5 games, oldest first
    for i in range(5):
        _insert_score(db_session, uid, i * 10, now - timedelta(hours=5 - i))

    # First page: limit=2
    page1 = client.get("/api/users/me/games?limit=2&offset=0", headers=h).json()
    assert len(page1["games"]) == 2
    assert page1["total"] == 5

    # Second page: limit=2, offset=2
    page2 = client.get("/api/users/me/games?limit=2&offset=2", headers=h).json()
    assert len(page2["games"]) == 2

    # No overlap between pages
    ids_p1 = {g["game_id"] for g in page1["games"]}
    ids_p2 = {g["game_id"] for g in page2["games"]}
    assert ids_p1.isdisjoint(ids_p2)

    # Last page
    page3 = client.get("/api/users/me/games?limit=2&offset=4", headers=h).json()
    assert len(page3["games"]) == 1


# ── 5–7. Validation ───────────────────────────────────────────────────────────

def test_limit_above_cap_rejected(client, auth_headers):
    resp = client.get("/api/users/me/games?limit=51", headers=auth_headers)
    assert resp.status_code == 422


def test_limit_zero_rejected(client, auth_headers):
    resp = client.get("/api/users/me/games?limit=0", headers=auth_headers)
    assert resp.status_code == 422


def test_negative_offset_rejected(client, auth_headers):
    resp = client.get("/api/users/me/games?offset=-1", headers=auth_headers)
    assert resp.status_code == 422


# ── 8. personal_best ─────────────────────────────────────────────────────────

def test_rankings_personal_best(client, db_session):
    """personal_best is the user's all-time highest score."""
    h = _signup_login(client, "prof_pb", "prof_pb@t.dev")
    uid = _user_id(client, h)
    now = datetime.now(timezone.utc)

    _insert_score(db_session, uid, 100, now - timedelta(hours=2))
    _insert_score(db_session, uid, 250, now - timedelta(hours=1))  # personal best
    _insert_score(db_session, uid, 50,  now)

    rankings = client.get("/api/users/me/rankings", headers=h).json()
    assert rankings["personal_best"] == 250


# ── 9. global_rank matches public leaderboard ────────────────────────────────

def test_global_rank_matches_public_leaderboard(client, db_session):
    """
    global_rank from /me/rankings must equal the rank shown on
    GET /api/leaderboards/global for the same user.
    """
    h = _signup_login(client, "prof_gr", "prof_gr@t.dev")
    uid = _user_id(client, h)
    now = datetime.now(timezone.utc)

    _insert_score(db_session, uid, 300, now)

    rankings   = client.get("/api/users/me/rankings", headers=h).json()
    leaderboard = client.get("/api/leaderboards/global").json()["entries"]

    lb_entry = next((e for e in leaderboard if e["username"] == "prof_gr"), None)
    assert lb_entry is not None, "User must appear on global leaderboard"
    assert rankings["global_rank"] == lb_entry["rank"], (
        f"global_rank {rankings['global_rank']} != leaderboard rank {lb_entry['rank']}"
    )


# ── 10. daily_rank matches public leaderboard ────────────────────────────────

def test_daily_rank_matches_public_leaderboard(client, db_session):
    """daily_rank from /me/rankings must match /api/leaderboards/daily."""
    h = _signup_login(client, "prof_dr", "prof_dr@t.dev")
    uid = _user_id(client, h)
    now = datetime.now(timezone.utc)

    _insert_score(db_session, uid, 180, now)

    rankings    = client.get("/api/users/me/rankings", headers=h).json()
    leaderboard = client.get("/api/leaderboards/daily").json()["entries"]

    lb_entry = next((e for e in leaderboard if e["username"] == "prof_dr"), None)
    assert lb_entry is not None
    assert rankings["daily_rank"] == lb_entry["rank"]


# ── 11. weekly_rank matches public leaderboard ───────────────────────────────

def test_weekly_rank_matches_public_leaderboard(client, db_session):
    """weekly_rank from /me/rankings must match /api/leaderboards/weekly."""
    h = _signup_login(client, "prof_wr", "prof_wr@t.dev")
    uid = _user_id(client, h)
    now = datetime.now(timezone.utc)

    _insert_score(db_session, uid, 220, now - timedelta(days=3))

    rankings    = client.get("/api/users/me/rankings", headers=h).json()
    leaderboard = client.get("/api/leaderboards/weekly").json()["entries"]

    lb_entry = next((e for e in leaderboard if e["username"] == "prof_wr"), None)
    assert lb_entry is not None
    assert rankings["weekly_rank"] == lb_entry["rank"]


# ── 12. User with no scores ───────────────────────────────────────────────────

def test_no_scores_returns_empty_history_and_null_rankings(client, db_session):
    """A fresh user with no completed games gets empty history and all nulls."""
    h = _signup_login(client, "prof_fresh", "prof_fresh@t.dev")

    history = client.get("/api/users/me/games", headers=h).json()
    assert history["total"] == 0
    assert history["games"] == []

    rankings = client.get("/api/users/me/rankings", headers=h).json()
    assert rankings["personal_best"] is None
    assert rankings["global_rank"]   is None
    assert rankings["daily_rank"]    is None
    assert rankings["weekly_rank"]   is None


# ── 13–14. Unauthenticated access → 401 ──────────────────────────────────────

def test_games_unauthenticated_returns_401(client):
    # FastAPI HTTPBearer returns 403 when Authorization header is absent entirely.
    resp = client.get("/api/users/me/games")
    assert resp.status_code in (401, 403)


def test_rankings_unauthenticated_returns_401(client):
    # FastAPI HTTPBearer returns 403 when Authorization header is absent entirely.
    resp = client.get("/api/users/me/rankings")
    assert resp.status_code in (401, 403)


# ── 15. daily_rank is None when score is outside today's window ──────────────

def test_daily_rank_null_when_score_is_yesterday(client, db_session):
    """A user whose only score is from yesterday gets daily_rank = None."""
    h = _signup_login(client, "prof_yest", "prof_yest@t.dev")
    uid = _user_id(client, h)
    now = datetime.now(timezone.utc)

    yesterday = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(seconds=1)
    _insert_score(db_session, uid, 400, yesterday)

    rankings = client.get("/api/users/me/rankings", headers=h).json()
    assert rankings["global_rank"]   is not None   # appears on global
    assert rankings["daily_rank"]    is None        # NOT in today's window
    assert rankings["personal_best"] == 400
