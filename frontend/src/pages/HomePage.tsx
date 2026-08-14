import * as api from '../services/api';
import type { User } from '../types';
import GamePage from './GamePage';

interface Props {
  user: User;
  onLogout: () => void;
}

export default function HomePage({ user, onLogout }: Props) {
  function handleLogout() {
    api.logout();
    onLogout();
  }

  return (
    <div>
      <header className="home-header">
        <span className="home-logo">⚡ ClickRush</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ fontSize: '0.85rem', color: 'var(--clr-muted)' }}>
            @{user.username}
          </span>
          <button
            id="logout-btn"
            className="btn btn-ghost"
            onClick={handleLogout}
            style={{ width: 'auto', padding: '0.45rem 1rem', fontSize: '0.85rem' }}
          >
            Log Out
          </button>
        </div>
      </header>

      {/* The game lives directly in the home screen */}
      <GamePage username={user.username} />
    </div>
  );
}
