import { useEffect, useState } from 'react';
import * as api from './services/api';
import type { User } from './types';
import SignupPage from './pages/SignupPage';
import LoginPage from './pages/LoginPage';
import HomePage from './pages/HomePage';

type View = 'signup' | 'login' | 'home';

function App() {
  const [view, setView] = useState<View>('login');
  const [user, setUser] = useState<User | null>(null);

  // On mount: if a token exists, try to restore the session
  useEffect(() => {
    if (api.isAuthenticated()) {
      api.getMe()
        .then(u => {
          setUser(u);
          setView('home');
        })
        .catch(() => {
          // Token is stale/invalid — clear it
          api.logout();
          setView('login');
        });
    }
  }, []);

  function handleAuthSuccess(u: User) {
    setUser(u);
    setView('home');
  }

  function handleLogout() {
    setUser(null);
    setView('login');
  }

  if (view === 'home' && user) {
    return <HomePage user={user} onLogout={handleLogout} />;
  }

  if (view === 'signup') {
    return (
      <SignupPage
        onSuccess={handleAuthSuccess}
        onSwitchToLogin={() => setView('login')}
      />
    );
  }

  return (
    <LoginPage
      onSuccess={handleAuthSuccess}
      onSwitchToSignup={() => setView('signup')}
    />
  );
}

export default App;
