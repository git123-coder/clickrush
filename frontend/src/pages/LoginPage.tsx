import { useState, type FormEvent } from 'react';
import * as api from '../services/api';
import type { User } from '../types';

interface Props {
  onSuccess: (user: User) => void;
  onSwitchToSignup: () => void;
}

export default function LoginPage({ onSuccess, onSwitchToSignup }: Props) {
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [error, setError]       = useState('');
  const [loading, setLoading]   = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.login({ email, password });
      const user = await api.getMe();
      onSuccess(user);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page-center">
      <div className="card">
        <h1 className="card-title">ClickRush</h1>
        <p className="card-subtitle">Welcome back! Log in to continue</p>

        {error && <div className="error-banner">{error}</div>}

        <form onSubmit={handleSubmit} noValidate>
          <div className="form-group">
            <label className="form-label" htmlFor="login-email">Email</label>
            <input
              id="login-email"
              className="form-input"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              autoFocus
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="login-password">Password</label>
            <input
              id="login-password"
              className="form-input"
              type="password"
              placeholder="Your password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
            />
          </div>

          <button
            id="login-submit"
            className="btn btn-primary"
            type="submit"
            disabled={loading}
            style={{ marginTop: '0.5rem' }}
          >
            {loading ? 'Logging in…' : 'Log In'}
          </button>
        </form>

        <div className="divider-text">Don't have an account?</div>
        <button className="btn btn-ghost" onClick={onSwitchToSignup}>
          Create Account
        </button>
      </div>
    </div>
  );
}
