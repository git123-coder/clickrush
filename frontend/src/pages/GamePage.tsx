import { useCallback, useEffect, useRef, useState } from 'react';
import * as api from '../services/api';
import type { FinishGameResponse, StartGameResponse } from '../types';

// ── Types ─────────────────────────────────────────────────────────────────────
type GameState = 'idle' | 'active' | 'submitting' | 'done' | 'error';

const CIRCUMFERENCE = 2 * Math.PI * 60; // radius = 60

// ── Countdown ring helper ──────────────────────────────────────────────────────
function CountdownRing({ secondsLeft, total }: { secondsLeft: number; total: number }) {
  const progress = secondsLeft / total;
  const offset = CIRCUMFERENCE * (1 - progress);
  const urgent = secondsLeft <= 10;

  return (
    <div className="countdown-ring">
      <svg className="countdown-svg" viewBox="0 0 140 140">
        <circle className="countdown-bg" cx="70" cy="70" r="60" />
        <circle
          className={`countdown-arc${urgent ? ' urgent' : ''}`}
          cx="70" cy="70" r="60"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={offset}
        />
      </svg>
      <div className={`countdown-number${urgent ? ' urgent' : ''}`}>
        {secondsLeft}
      </div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────
interface Props {
  username: string;
}

export default function GamePage({ username }: Props) {
  const [gameState, setGameState] = useState<GameState>('idle');
  const [clicks, setClicks] = useState(0);
  const [secondsLeft, setSecondsLeft] = useState(60);
  const [session, setSession] = useState<StartGameResponse | null>(null);
  const [result, setResult] = useState<FinishGameResponse | null>(null);
  const [error, setError] = useState('');

  // Refs to avoid stale closure issues in intervals
  const sessionRef = useRef<StartGameResponse | null>(null);
  const clicksRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const gameEndedRef = useRef(false);

  // ── Sync clicksRef with clicks state ──────────────────────────────────────
  useEffect(() => {
    clicksRef.current = clicks;
  }, [clicks]);

  // ── Timer logic: derive remaining time from server timestamps ──────────────
  // We do NOT rely on setTimeout(60000) alone. The countdown derives from
  // server-provided expires_at so it's immune to tab suspension / drift.
  const startTimer = useCallback((expiresAt: string) => {
    gameEndedRef.current = false;

    const tick = () => {
      const remaining = Math.max(
        0,
        Math.floor((new Date(expiresAt).getTime() - Date.now()) / 1000),
      );
      setSecondsLeft(remaining);

      if (remaining <= 0 && !gameEndedRef.current) {
        gameEndedRef.current = true;
        clearInterval(timerRef.current!);
        submitScore();
      }
    };

    tick(); // immediate tick to avoid 1-second blank
    timerRef.current = setInterval(tick, 500);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Cleanup timer on unmount
  useEffect(() => () => {
    if (timerRef.current) clearInterval(timerRef.current);
  }, []);

  // ── Start game ────────────────────────────────────────────────────────────
  async function handleStart() {
    setError('');
    setGameState('active');
    setClicks(0);
    clicksRef.current = 0;
    setResult(null);

    try {
      const s = await api.startGame();
      setSession(s);
      sessionRef.current = s;
      setSecondsLeft(s.duration_seconds);
      startTimer(s.expires_at);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start game.');
      setGameState('idle');
    }
  }

  // ── Register a click ──────────────────────────────────────────────────────
  function handleClick() {
    if (gameState !== 'active' || secondsLeft <= 0) return;
    setClicks(c => c + 1);
  }

  // ── Submit score ──────────────────────────────────────────────────────────
  async function submitScore() {
    const s = sessionRef.current;
    if (!s) return;
    setGameState('submitting');

    try {
      const r = await api.finishGame(s.game_id, clicksRef.current);
      setResult(r);
      setGameState('done');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit score.');
      setGameState('error');
    }
  }

  // ── State labels ──────────────────────────────────────────────────────────
  const isUrgent = gameState === 'active' && secondsLeft <= 10;
  const statusLabel =
    gameState === 'idle'      ? 'Ready to play'
    : gameState === 'active'  ? (isUrgent ? '⚡ Last 10 seconds!' : '🟢 Game running')
    : gameState === 'submitting' ? 'Submitting…'
    : gameState === 'done'    ? 'Game over!'
    : 'Something went wrong';

  const cps = result
    ? (result.clicks / 60).toFixed(1)
    : null;

  // ── Render: result screen ─────────────────────────────────────────────────
  if (gameState === 'done' && result) {
    return (
      <div className="game-arena">
        <div className="result-card">
          <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>🎉</div>
          <h2 style={{ margin: '0 0 0.5rem', fontSize: '1.3rem', fontWeight: 700 }}>
            Game Complete!
          </h2>
          <div className="result-label">Your Score</div>
          <div className="result-score">{result.clicks}</div>
          <div className="result-cps">{cps} clicks/second</div>
          <button
            id="play-again-btn"
            className="start-btn"
            onClick={handleStart}
          >
            Play Again
          </button>
        </div>
      </div>
    );
  }

  // ── Render: game / idle screen ─────────────────────────────────────────────
  return (
    <div className="game-arena">
      {/* Status */}
      <div className={`game-status-label${isUrgent ? ' urgent' : gameState === 'active' ? ' active' : ''}`}>
        {statusLabel}
      </div>

      {/* Countdown */}
      <CountdownRing
        secondsLeft={gameState === 'active' || gameState === 'submitting' ? secondsLeft : 60}
        total={60}
      />

      {/* Click counter */}
      <div>
        <div className="click-count-label">Clicks</div>
        <div className="click-count">{clicks}</div>
      </div>

      {/* Main click button */}
      <button
        id="click-btn"
        className="click-btn"
        onClick={handleClick}
        disabled={gameState !== 'active' || secondsLeft <= 0}
        aria-label="Click to score"
      >
        <span className="click-btn-icon">⚡</span>
        <span>CLICK!</span>
      </button>

      {/* Error display */}
      {error && (
        <div className="error-banner" style={{ maxWidth: 360 }}>{error}</div>
      )}

      {/* Start / submitting */}
      {gameState === 'idle' || gameState === 'error' ? (
        <div>
          <div style={{ fontSize: '0.85rem', color: 'var(--clr-muted)', marginBottom: '1rem' }}>
            Hi <strong>@{username}</strong> — click as fast as you can for 60 seconds!
          </div>
          <button
            id="start-game-btn"
            className="start-btn"
            onClick={handleStart}
          >
            🚀 Start Game
          </button>
        </div>
      ) : gameState === 'submitting' ? (
        <div style={{ fontSize: '0.9rem', color: 'var(--clr-muted)' }}>
          Saving your score…
        </div>
      ) : null}
    </div>
  );
}
