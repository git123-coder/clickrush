import { useState } from 'react';
import * as api from '../services/api';
import type { User } from '../types';
import GamePage from './GamePage';
import LeaderboardPage from './LeaderboardPage';
import ProfilePage from './ProfilePage';

type HomeView = 'game' | 'leaderboard' | 'profile';

interface Props {
  user: User;
  onLogout: () => void;
}

export default function HomePage({ user, onLogout }: Props) {
  const [homeView, setHomeView] = useState<HomeView>('game');

  function handleLogout() {
    api.logout();
    onLogout();
  }

  if (homeView === 'leaderboard') {
    return (
      <LeaderboardPage
        currentUsername={user.username}
        onBack={() => setHomeView('game')}
      />
    );
  }

  if (homeView === 'profile') {
    return (
      <ProfilePage
        username={user.username}
        onBack={() => setHomeView('game')}
      />
    );
  }

  return (
    <div>
      <header className="home-header">
        <span className="home-logo">⚡ ClickRush</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            id="leaderboard-btn"
            className="btn btn-ghost"
            onClick={() => setHomeView('leaderboard')}
            style={{ width: 'auto', padding: '0.45rem 1rem', fontSize: '0.85rem' }}
          >
            🏆 Leaderboard
          </button>
          <button
            id="profile-btn"
            className="btn btn-ghost"
            onClick={() => setHomeView('profile')}
            style={{ width: 'auto', padding: '0.45rem 1rem', fontSize: '0.85rem' }}
          >
            👤 @{user.username}
          </button>
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
