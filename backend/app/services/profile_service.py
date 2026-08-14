"""
app/services/profile_service.py
────────────────────────────────
Business logic for the user profile endpoints.

Design decisions
────────────────

1.  Game history — joins scores to game_sessions to get both timing and score
    in a single query.  Only completed sessions (status = completed) are included;
    abandoned/expired sessions with no score are filtered out via INNER JOIN
    on scores (a score only exists for completed sessions).

2.  Rankings reuse the Day 3 leaderboard CTE pattern exactly.  The rank for a
    specific user is extracted by adding a WHERE on username after the ranked CTE.
    This guarantees identical ranking semantics — the same query, the same
    DISTINCT ON, the same tie-breaking — so personal rank always matches what the
    public leaderboard endpoints return for the same user.

    Alternative considered: run the public leaderboard, then search the list in
    Python. Rejected because it pulls up to MAX_LIMIT rows just to find one rank,
    and breaks if the user falls beyond the cap.

3.  Personal best — a simple MAX(clicks) across the scores table for the user.
    Not time-windowed; it represents the true all-time personal best.

4.  Null semantics:
      - personal_best = None → no completed games ever.
      - *_rank = None → no qualifying score in that time window.
    Frontend should render None as "Unranked", not "0".

5.  Pagination — offset/limit on the history query.  total is computed with
    a separate COUNT query (lightweight; the scores table is indexed on user_id).
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.game_session import GameSession, GameStatus
from app.models.score import Score
from app.schemas.profile import GameHistoryEntry, GameHistoryResponse, UserRankingsResponse


MAX_HISTORY_LIMIT = 50


# ── Game history ──────────────────────────────────────────────────────────────

def get_game_history(
    db: Session,
    user_id: uuid.UUID,
    limit: int,
    offset: int,
) -> GameHistoryResponse:
    """
    Return paginated completed games for the user, most recent first.

    Only sessions with status=completed are included.  An INNER JOIN on
    scores guarantees the score exists (completed sessions always have one).
    """
    effective_limit = min(max(limit, 1), MAX_HISTORY_LIMIT)

    # Total count for pagination UI
    total = db.scalar(
        select(func.count())
        .select_from(Score)
        .where(Score.user_id == user_id)
    ) or 0

    # Paginated history: join scores → game_sessions to get timing + clicks
    rows = db.execute(
        select(
            GameSession.id.label("game_id"),
            Score.clicks,
            GameSession.started_at,
            GameSession.finished_at,
        )
        .join(Score, Score.game_session_id == GameSession.id)
        .where(GameSession.user_id == user_id)
        .where(GameSession.status == GameStatus.completed)
        .order_by(GameSession.finished_at.desc())
        .limit(effective_limit)
        .offset(offset)
    ).fetchall()

    games = [
        GameHistoryEntry(
            game_id=row.game_id,
            clicks=row.clicks,
            started_at=row.started_at,
            finished_at=row.finished_at,
        )
        for row in rows
    ]
    return GameHistoryResponse(games=games, total=total)


# ── Rankings ──────────────────────────────────────────────────────────────────

def _get_rank_in_window(
    db: Session,
    username: str,
    where_clause: str,
    bind_params: dict,
) -> int | None:
    """
    Find a user's rank within a leaderboard window using the same CTE pattern
    as the public leaderboard endpoints.

    Returns None if the user has no qualifying score in the window.

    The query is identical to _build_leaderboard in leaderboard_service.py
    (same DISTINCT ON, same ROW_NUMBER, same tie-breaking) — just filtered
    to return a single user's rank instead of the full table.
    """
    sql = text(f"""
        WITH best_per_user AS (
            SELECT DISTINCT ON (s.user_id)
                s.user_id,
                u.username,
                s.clicks,
                s.created_at
            FROM scores s
            JOIN users u ON u.id = s.user_id
            WHERE {where_clause}
            ORDER BY s.user_id, s.clicks DESC, s.created_at ASC
        ),
        ranked AS (
            SELECT
                ROW_NUMBER() OVER (ORDER BY clicks DESC, created_at ASC)::int AS rank,
                username
            FROM best_per_user
        )
        SELECT rank
        FROM ranked
        WHERE username = :username;
    """)

    row = db.execute(sql, {**bind_params, "username": username}).fetchone()
    return row.rank if row else None


def get_user_rankings(db: Session, user_id: uuid.UUID, username: str) -> UserRankingsResponse:
    """
    Compute personal_best and global/daily/weekly ranks for the user.

    personal_best: MAX(clicks) across all time — None if no games played.
    *_rank: position in that leaderboard window — None if no qualifying score.
    """
    # Personal best — simple MAX, no window
    personal_best = db.scalar(
        select(func.max(Score.clicks)).where(Score.user_id == user_id)
    )  # returns None if no rows

    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)

    global_rank = _get_rank_in_window(db, username, "TRUE", {})
    daily_rank  = _get_rank_in_window(db, username, "s.created_at >= :day_start",  {"day_start": day_start})
    weekly_rank = _get_rank_in_window(db, username, "s.created_at >= :week_start", {"week_start": week_start})

    return UserRankingsResponse(
        personal_best=personal_best,
        global_rank=global_rank,
        daily_rank=daily_rank,
        weekly_rank=weekly_rank,
    )
