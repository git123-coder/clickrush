import { useState, type FormEvent } from 'react';
import * as api from '../services/api';
import type { User } from '../types';

interface Props {
  onSuccess: (user: User) => void;
  onSwitchToLogin: () => void;
}

export default function SignupPage({ onSuccess, onSwitchToLogin }: Props) {
  const [username, setUsername] = useState('');
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [error, setError]       = useState('');
  const [loading, setLoading]   = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const user = await api.signup({ username, email, password });
      // Auto-login after signup
      await api.login({ email, password });
      onSuccess(user);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Signup failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page-center">
      <div className="card">
        <h1 className="card-title">ClickRush</h1>
        <p className="card-subtitle">Create your account to get started</p>

        {error && <div className="error-banner">{error}</div>}

        <form onSubmit={handleSubmit} noValidate>
          <div className="form-group">
            <label className="form-label" htmlFor="signup-username">Username</label>
            <input
              id="signup-username"
              className="form-input"
              type="text"
              placeholder="e.g. clickmaster42"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              minLength={3}
              maxLength={50}
              autoFocus
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="signup-email">Email</label>
            <input
              id="signup-email"
              className="form-input"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="signup-password">Password</label>
            <input
              id="signup-password"
              className="form-input"
              type="password"
              placeholder="Minimum 8 characters"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              minLength={8}
            />
          </div>

          <button
            id="signup-submit"
            className="btn btn-primary"
            type="submit"
            disabled={loading}
            style={{ marginTop: '0.5rem' }}
          >
            {loading ? 'Creating account…' : 'Create Account'}
          </button>
        </form>

        <div className="divider-text">Already have an account?</div>
        <button className="btn btn-ghost" onClick={onSwitchToLogin}>
          Log In
        </button>
      </div>
    </div>
  );
}
