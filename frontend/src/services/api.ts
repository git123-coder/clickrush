/**
 * services/api.ts
 * ───────────────
 * Centralised API service layer.
 *
 * Why a service layer instead of scattered fetch() calls?
 *   - Single place to set the base URL, auth headers, and error handling.
 *   - Components stay focused on UI logic, not HTTP mechanics.
 *   - Easy to swap out (e.g., add an interceptor, switch to Axios) later.
 *
 * Token storage strategy:
 *   - localStorage is simple and appropriate for this MVP.
 *   - For Day 2+ we can move to httpOnly cookies for improved XSS resistance.
 */

import type { LoginPayload, SignupPayload, TokenResponse, User, StartGameResponse, FinishGameResponse, LeaderboardResponse, LeaderboardType, GameHistoryResponse, UserRankingsResponse } from '../types';

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

const TOKEN_KEY = 'clickrush_token';

// ── Token helpers ─────────────────────────────────────────────────────────────

export const tokenStorage = {
  get: (): string | null => localStorage.getItem(TOKEN_KEY),
  set: (token: string): void => localStorage.setItem(TOKEN_KEY, token),
  remove: (): void => localStorage.removeItem(TOKEN_KEY),
};

// ── Core fetch wrapper ────────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  authenticated = false,
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (authenticated) {
    const token = tokenStorage.get();
    if (!token) throw new Error('No auth token');
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: 'Unknown error' }));
    const detail = typeof errorBody.detail === 'string'
      ? errorBody.detail
      : errorBody.detail?.map((e: { msg: string }) => e.msg).join(', ') ?? 'Request failed';
    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

// ── Auth endpoints ─────────────────────────────────────────────────────────────

export async function signup(payload: SignupPayload): Promise<User> {
  return apiFetch<User>('/api/auth/signup', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function login(payload: LoginPayload): Promise<TokenResponse> {
  const data = await apiFetch<TokenResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  tokenStorage.set(data.access_token);
  return data;
}

export function logout(): void {
  tokenStorage.remove();
}

// ── User endpoints ─────────────────────────────────────────────────────────────

export async function getMe(): Promise<User> {
  return apiFetch<User>('/api/users/me', {}, true);
}

// ── Auth state helper ─────────────────────────────────────────────────────────

export function isAuthenticated(): boolean {
  return tokenStorage.get() !== null;
}

// ── Game endpoints ────────────────────────────────────────────────────────────

export async function startGame(): Promise<StartGameResponse> {
  return apiFetch<StartGameResponse>('/api/games/start', { method: 'POST' }, true);
}

export async function finishGame(gameId: string, clicks: number): Promise<FinishGameResponse> {
  return apiFetch<FinishGameResponse>(
    `/api/games/${gameId}/finish`,
    { method: 'POST', body: JSON.stringify({ clicks }) },
    true,
  );
}

// ── Leaderboard endpoints (public — no auth required) ────────────────────────

export async function getLeaderboard(
  type: LeaderboardType,
  limit = 50,
): Promise<LeaderboardResponse> {
  return apiFetch<LeaderboardResponse>(
    `/api/leaderboards/${type}?limit=${limit}`,
  );
}

// ── Profile endpoints (authenticated) ───────────────────────────────────

export async function getMyGames(
  limit = 20,
  offset = 0,
): Promise<GameHistoryResponse> {
  return apiFetch<GameHistoryResponse>(
    `/api/users/me/games?limit=${limit}&offset=${offset}`,
    {},
    true,
  );
}

export async function getMyRankings(): Promise<UserRankingsResponse> {
  return apiFetch<UserRankingsResponse>('/api/users/me/rankings', {}, true);
}
