import { useCallback, useEffect, useState } from 'react';
import * as api from '../services/api';
import type { LeaderboardEntry, LeaderboardType } from '../types';

// ── Types ──────────────────────────────────────────────────────────────────────
interface Props {
  currentUsername?: string; // logged-in user's username to highlight their row
  onBack: () => void;
}

const TABS: { key: LeaderboardType; label: string; desc: string }[] = [
  { key: 'global', label: 'All-Time',  desc: 'Best score ever recorded' },
  { key: 'weekly', label: 'This Week', desc: 'Best score in the last 7 days' },
  { key: 'daily',  label: 'Today',     desc: 'Best score since midnight UTC' },
];

// ── Helpers ────────────────────────────────────────────────────────────────────
function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
  });
}

function RankBadge({ rank }: { rank: number }) {
  const medals = ['🥇', '🥈', '🥉'];
  if (rank <= 3) return <span className="lb-medal">{medals[rank - 1]}</span>;
  return <span className="lb-rank">#{rank}</span>;
}

// ── Main component ─────────────────────────────────────────────────────────────
export default function LeaderboardPage({ currentUsername, onBack }: Props) {
  const [activeTab, setActiveTab] = useState<LeaderboardType>('global');
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchLeaderboard = useCallback(async (type: LeaderboardType) => {
    setLoading(true);
    setError('');
    try {
      const data = await api.getLeaderboard(type, 50);
      setEntries(data.entries);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load leaderboard.');
      setEntries([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLeaderboard(activeTab);
  }, [activeTab, fetchLeaderboard]);

  function handleTab(type: LeaderboardType) {
    setActiveTab(type);
  }

  const activeTabDef = TABS.find(t => t.key === activeTab)!;

  return (
    <div className="lb-page">
      {/* Header */}
      <div className="lb-header">
        <button className="lb-back-btn" onClick={onBack} aria-label="Back to game">
          ← Back
        </button>
        <div>
          <h1 className="lb-title">⚡ Leaderboard</h1>
          <p className="lb-subtitle">{activeTabDef.desc}</p>
        </div>
        <button
          className="lb-refresh-btn"
          onClick={() => fetchLeaderboard(activeTab)}
          disabled={loading}
          aria-label="Refresh leaderboard"
          title="Refresh"
        >
          {loading ? '⏳' : '🔄'}
        </button>
      </div>

      {/* Tab bar */}
      <div className="lb-tabs" role="tablist">
        {TABS.map(tab => (
          <button
            key={tab.key}
            id={`lb-tab-${tab.key}`}
            role="tab"
            aria-selected={activeTab === tab.key}
            className={`lb-tab${activeTab === tab.key ? ' active' : ''}`}
            onClick={() => handleTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Body */}
      <div className="lb-body">
        {loading ? (
          <div className="lb-placeholder">
            <div className="lb-spinner" aria-label="Loading" />
            <p>Loading rankings…</p>
          </div>
        ) : error ? (
          <div className="lb-placeholder">
            <p className="lb-error">{error}</p>
            <button className="start-btn" onClick={() => fetchLeaderboard(activeTab)}>
              Try Again
            </button>
          </div>
        ) : entries.length === 0 ? (
          <div className="lb-placeholder">
            <div style={{ fontSize: '3rem' }}>🏆</div>
            <p className="lb-empty-msg">No scores yet for this period.</p>
            <p style={{ fontSize: '0.85rem', color: 'var(--clr-muted)' }}>
              Be the first — go play a game!
            </p>
          </div>
        ) : (
          <div className="table-container">
            <table className="lb-table" role="table" aria-label={`${activeTabDef.label} leaderboard`}>
              <thead>
                <tr>
                  <th className="lb-th lb-th-rank">Rank</th>
                  <th className="lb-th lb-th-user">Player</th>
                  <th className="lb-th lb-th-clicks">Clicks</th>
                  <th className="lb-th lb-th-date">Achieved</th>
                </tr>
              </thead>
              <tbody>
                {entries.map(entry => {
                  const isMe = !!currentUsername &&
                    entry.username.toLowerCase() === currentUsername.toLowerCase();
                  return (
                    <tr
                      key={`${entry.rank}-${entry.username}`}
                      className={`lb-row${isMe ? ' lb-row-mine' : ''}`}
                      aria-label={isMe ? 'Your entry' : undefined}
                    >
                      <td className="lb-td lb-td-rank">
                        <RankBadge rank={entry.rank} />
                      </td>
                      <td className="lb-td lb-td-user">
                        <span className="lb-username">
                          {isMe ? '⚡ ' : ''}{entry.username}
                        </span>
                        {isMe && <span className="lb-you-badge">You</span>}
                      </td>
                      <td className="lb-td lb-td-clicks">
                        <span className="lb-clicks">{entry.clicks.toLocaleString()}</span>
                      </td>
                      <td className="lb-td lb-td-date">
                        <span className="lb-date">{formatDate(entry.achieved_at)}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
