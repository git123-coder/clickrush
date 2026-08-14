"""
app/services/leaderboard_service.py
────────────────────────────────────
Query logic for the three leaderboard types.

Design decisions
────────────────

1.  Best-per-user, not best-per-game.
    Each user appears at most once per leaderboard, showing their single
    highest score in the relevant time window.  Showing every individual
    game would make the table dominated by a single prolific player and
    makes ranking meaningless.

2.  Tie-breaking: clicks DESC, created_at ASC.
    When two users have identical click counts, the person who achieved
    it first wins the lower (better) rank.  This is stable and predictable.

3.  Weekly window: rolling 7 calendar days (not ISO week).
    "Last 7 days" is simpler for users to understand ("my score from
    Tuesday still counts today") and avoids Monday-reset surprises.
    Documented here so Day 4+ can switch if needed.

4.  SQL strategy — two-step CTE approach:
    Step A: DISTINCT ON (user_id) ordered by (clicks DESC, created_at ASC)
            gives each user's personal best within the window.
    Step B: ROW_NUMBER() OVER (ORDER BY clicks DESC, created_at ASC)
            assigns the final rank across all users.

    This is a single SQL round-trip per request and uses the existing
    composite index ix_scores_user_created_clicks (user_id, created_at, clicks).
    A new index is NOT added; the existing one covers both the time-filter
    and the ORDER BY inside DISTINCT ON.

5.  No authentication required.  Leaderboards are public information —
    requiring auth would break sharing/embedding links.

6.  limit is capped at 100 server-side regardless of the query param.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.leaderboard import LeaderboardEntry

MAX_LIMIT = 100


def _build_leaderboard(
    db: Session,
    *,
    limit: int,
    where_clause: str,
    bind_params: dict,
) -> list[LeaderboardEntry]:
    """
    Internal helper that runs the two-step CTE leaderboard query.

    The query skeleton:
        WITH best_per_user AS (
            SELECT DISTINCT ON (s.user_id)
                s.user_id,
                u.username,
                s.clicks,
                s.created_at
            FROM scores s
            JOIN users u ON u.id = s.user_id
            WHERE <time filter>
            ORDER BY s.user_id, s.clicks DESC, s.created_at ASC
        ),
        ranked AS (
            SELECT
                ROW_NUMBER() OVER (ORDER BY clicks DESC, created_at ASC) AS rank,
                username,
                clicks,
                created_at AS achieved_at
            FROM best_per_user
        )
        SELECT rank, username, clicks, achieved_at
        FROM ranked
        ORDER BY rank
        LIMIT :limit;
    """
    effective_limit = min(max(limit, 1), MAX_LIMIT)

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
                username,
                clicks,
                created_at AS achieved_at
            FROM best_per_user
        )
        SELECT rank, username, clicks, achieved_at
        FROM ranked
        ORDER BY rank
        LIMIT :limit;
    """)

    rows = db.execute(sql, {**bind_params, "limit": effective_limit}).fetchall()

    return [
        LeaderboardEntry(
            rank=row.rank,
            username=row.username,
            clicks=row.clicks,
            achieved_at=row.achieved_at,
        )
        for row in rows
    ]


def get_global_leaderboard(db: Session, limit: int) -> list[LeaderboardEntry]:
    """Best score of all time, across all users."""
    return _build_leaderboard(
        db,
        limit=limit,
        where_clause="TRUE",
        bind_params={},
    )


def get_daily_leaderboard(db: Session, limit: int) -> list[LeaderboardEntry]:
    """
    Best score for the current UTC calendar day.

    Window: [start of today UTC, now].
    """
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    return _build_leaderboard(
        db,
        limit=limit,
        where_clause="s.created_at >= :day_start",
        bind_params={"day_start": day_start},
    )


def get_weekly_leaderboard(db: Session, limit: int) -> list[LeaderboardEntry]:
    """
    Best score within the last 7 rolling days (not ISO calendar week).

    Window: [now − 7 days, now].

    Choice documented in module docstring.
    """
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=7)

    return _build_leaderboard(
        db,
        limit=limit,
        where_clause="s.created_at >= :week_start",
        bind_params={"week_start": week_start},
    )
