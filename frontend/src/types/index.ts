// ── Shared TypeScript types ───────────────────────────────────────────────────

export interface User {
  id: string;
  username: string;
  email: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface SignupPayload {
  username: string;
  email: string;
  password: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface ApiError {
  detail: string | { msg: string; loc: string[] }[];
}

// ── Game types ────────────────────────────────────────────────────────────────

export interface StartGameResponse {
  game_id: string;
  started_at: string;
  expires_at: string;
  duration_seconds: number;
}

export interface FinishGameResponse {
  game_id: string;
  clicks: number;
  started_at: string;
  finished_at: string;
  status: 'active' | 'completed' | 'expired';
}
