import { useCallback, useEffect, useState } from 'react';
import * as api from '../services/api';
import type { GameHistoryEntry, UserRankingsResponse } from '../types';

// ── Types ──────────────────────────────────────────────────────────────────────
interface Props {
  username: string;
  onBack: () => void;
}

// ── Helpers ────────────────────────────────────────────────────────────────────
function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function rankLabel(rank: number | null): string {
  if (rank === null) return 'Unranked';
  return `#${rank}`;
}

function RankCard({
  label, rank, accent = false,
}: { label: string; rank: number | null; accent?: boolean }) {
  const isRanked = rank !== null;
  return (
    <div className={`prof-rank-card${accent ? ' prof-rank-card--accent' : ''}`}>
      <span className="prof-rank-label">{label}</span>
      <span className={`prof-rank-value${isRanked ? ' ranked' : ' unranked'}`}>
        {rankLabel(rank)}
      </span>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────
const PAGE_SIZE = 20;

export default function ProfilePage({ username, onBack }: Props) {
  const [rankings, setRankings] = useState<UserRankingsResponse | null>(null);
  const [games, setGames] = useState<GameHistoryEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loadingRankings, setLoadingRankings] = useState(true);
  const [loadingGames, setLoadingGames] = useState(true);
  const [rankingsError, setRankingsError] = useState('');
  const [gamesError, setGamesError] = useState('');

  // Fetch rankings on mount
  useEffect(() => {
    setLoadingRankings(true);
    api.getMyRankings()
      .then(setRankings)
      .catch(err => setRankingsError(err instanceof Error ? err.message : 'Failed to load rankings.'))
      .finally(() => setLoadingRankings(false));
  }, []);

  // Fetch game history whenever offset changes
  const fetchGames = useCallback(async (nextOffset: number) => {
    setLoadingGames(true);
    setGamesError('');
    try {
      const data = await api.getMyGames(PAGE_SIZE, nextOffset);
      if (nextOffset === 0) {
        setGames(data.games);
      } else {
        setGames(prev => [...prev, ...data.games]);
      }
      setTotal(data.total);
      setOffset(nextOffset);
    } catch (err) {
      setGamesError(err instanceof Error ? err.message : 'Failed to load game history.');
    } finally {
      setLoadingGames(false);
    }
  }, []);

  useEffect(() => {
    fetchGames(0);
  }, [fetchGames]);

  const hasMore = games.length < total;

  return (
    <div className="prof-page">
      {/* Header */}
      <div className="prof-header">
        <button className="lb-back-btn" onClick={onBack} aria-label="Back">
          ← Back
        </button>
        <div className="prof-identity">
          <div className="prof-avatar" aria-hidden="true">
            {username.charAt(0).toUpperCase()}
          </div>
          <div>
            <h1 className="prof-username">@{username}</h1>
            <p className="prof-subtitle">Your stats &amp; game history</p>
          </div>
        </div>
      </div>

      {/* Personal best banner */}
      {!loadingRankings && rankings && (
        <div className="prof-pb-banner" aria-label="Personal best score">
          <span className="prof-pb-label">Personal Best</span>
          <span className="prof-pb-value">
            {rankings.personal_best !== null
              ? `${rankings.personal_best.toLocaleString()} clicks`
              : 'No games yet'}
          </span>
        </div>
      )}

      {/* Rank cards */}
      <section className="prof-rankings" aria-label="Your leaderboard rankings">
        <h2 className="prof-section-title">Current Rankings</h2>
        {loadingRankings ? (
          <div className="lb-placeholder" style={{ padding: '1.5rem' }}>
            <div className="lb-spinner" />
          </div>
        ) : rankingsError ? (
          <p className="lb-error">{rankingsError}</p>
        ) : rankings ? (
          <div className="prof-rank-grid">
            <RankCard label="🌍 Global (All-Time)" rank={rankings.global_rank} accent />
            <RankCard label="📅 This Week"          rank={rankings.weekly_rank} />
            <RankCard label="☀️ Today"              rank={rankings.daily_rank} />
          </div>
        ) : null}
      </section>

      {/* Game history */}
      <section className="prof-history" aria-label="Game history">
        <h2 className="prof-section-title">
          Game History
          {total > 0 && (
            <span className="prof-total-badge">{total} games</span>
          )}
        </h2>

        {loadingGames && games.length === 0 ? (
          <div className="lb-placeholder" style={{ padding: '2rem' }}>
            <div className="lb-spinner" />
            <p>Loading history…</p>
          </div>
        ) : gamesError ? (
          <div className="lb-placeholder">
            <p className="lb-error">{gamesError}</p>
            <button className="start-btn" onClick={() => fetchGames(0)}>
              Try Again
            </button>
          </div>
        ) : games.length === 0 ? (
          <div className="lb-placeholder" style={{ padding: '3rem' }}>
            <div style={{ fontSize: '3rem' }}>🎮</div>
            <p className="lb-empty-msg">No games played yet.</p>
            <p style={{ fontSize: '0.85rem', color: 'var(--clr-muted)' }}>
              Go back and play your first game!
            </p>
          </div>
        ) : (
          <>
            <div className="table-container">
              <table
                className="lb-table prof-history-table"
                role="table"
                aria-label="Game history"
              >
                <thead>
                  <tr>
                    <th className="lb-th">#</th>
                    <th className="lb-th">Clicks</th>
                    <th className="lb-th" style={{ textAlign: 'right' }}>Date &amp; Time</th>
                  </tr>
                </thead>
                <tbody>
                  {games.map((game, i) => (
                    <tr key={game.game_id} className="lb-row">
                      <td className="lb-td" style={{ color: 'var(--clr-muted)', fontSize: '0.8rem' }}>
                        {i + 1}
                      </td>
                      <td className="lb-td">
                        <span className="lb-clicks">{game.clicks.toLocaleString()}</span>
                      </td>
                      <td className="lb-td lb-td-date">
                        <span className="lb-date">{formatDateTime(game.finished_at)}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Load more */}
            {hasMore && (
              <div className="prof-load-more">
                <button
                  id="load-more-btn"
                  className="btn btn-ghost"
                  onClick={() => fetchGames(offset + PAGE_SIZE)}
                  disabled={loadingGames}
                  style={{ width: 'auto', padding: '0.5rem 1.5rem' }}
                >
                  {loadingGames ? 'Loading…' : `Load more (${total - games.length} remaining)`}
                </button>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}
