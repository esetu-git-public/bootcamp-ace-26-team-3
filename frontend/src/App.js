// Trigger compile 3
import React, { useState, useEffect, useCallback } from 'react';
import Login from './pages/Login';
import SignUp from './pages/SignUp';
import AnalyticsDashboard from './pages/AnalyticsDashboard';
import CustomerProfile from './pages/CustomerProfile';
import CustomerDirectory from './pages/CustomerDirectory';
import ModelPerformance from './pages/ModelPerformance';
import ScrumBoard from './pages/ScrumBoard';
import DatasetInsights from './pages/DatasetInsights';
import AlertNotifications from './components/AlertNotifications';

function App() {
  const [view, setView] = useState('login');
  const [token, setToken] = useState(localStorage.getItem('access_token') || sessionStorage.getItem('access_token'));
  const [selectedCustomerId, setSelectedCustomerId] = useState('');
  const [selectedJobId, setSelectedJobId] = useState('');
  const [notifications, setNotifications] = useState([]);
  const [predictionRefreshToken, setPredictionRefreshToken] = useState(0);

  const addNotification = useCallback((notification) => {
    const id = notification.id || `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setNotifications((current) => [
      { id, type: 'info', ...notification },
      ...current
    ].slice(0, 4));
  }, []);

  const dismissNotification = useCallback((id) => {
    setNotifications((current) => current.filter((notification) => notification.id !== id));
  }, []);

  const getUsernameFromToken = useCallback(() => {
    if (!token) return null;
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.sub;
    } catch {
      return null;
    }
  }, [token]);

  const currentUsername = getUsernameFromToken();
  const isAdmin = currentUsername === 'admin';

  useEffect(() => {
    if (token) {
      if (view === 'login') {
        setView('dashboard');
      }
    } else {
      setView('login');
    }
  }, [token, view]);

  useEffect(() => {
    const handleApiError = (event) => {
      const error = event.detail || {};

      if (error.status === 401) {
        setToken(null);
        setView('login');
      }

      addNotification({
        type: error.status === 401 ? 'warning' : 'error',
        title: error.status === 401 ? 'Session expired' : 'Request failed',
        message: error.message || 'Something went wrong. Please try again.'
      });
    };

    window.addEventListener('app:api-error', handleApiError);
    return () => window.removeEventListener('app:api-error', handleApiError);
  }, [addNotification]);

  const handleLoginSuccess = useCallback((newToken, rememberMe = false) => {
    const storage = rememberMe ? localStorage : sessionStorage;
    localStorage.removeItem('access_token');
    sessionStorage.removeItem('access_token');
    storage.setItem('access_token', newToken);
    setToken(newToken);
    addNotification({
      type: 'success',
      title: 'Signed in',
      message: 'Welcome back. Your dashboard is ready.'
    });
  }, [addNotification]);

  const handleLogout = useCallback((options = {}) => {
    localStorage.removeItem('access_token');
    sessionStorage.removeItem('access_token');
    setToken(null);
    setView('login');
    if (!options.silent) {
      addNotification({
        type: 'info',
        title: 'Signed out',
        message: 'You have been signed out successfully.'
      });
    }
  }, [addNotification]);

  const isAuth = token && ['dashboard', 'directory', 'profile', 'model', 'board', 'users', 'bulk_insights'].includes(view);

  return (
    <div className="App" style={styles.appContainer}>
      <AlertNotifications
        notifications={notifications}
        onDismiss={dismissNotification}
      />

      {isAuth && (
        <nav style={styles.navbar}>
          <div style={styles.brand}>
            <span style={styles.brandText}>Churn Predictor</span>
            <span style={styles.brandDot}>•</span>
            <span style={styles.brandSub}>Console</span>
          </div>
          <div style={styles.navLinks}>
            <button
              onClick={() => setView('dashboard')}
              style={view === 'dashboard' ? styles.activeNavLink : styles.navLink}
            >
              Dashboard
            </button>
            <button
              onClick={() => setView('directory')}
              style={view === 'directory' ? styles.activeNavLink : styles.navLink}
            >
              Customer Directory
            </button>
            <button
              onClick={() => setView('profile')}
              style={view === 'profile' ? styles.activeNavLink : styles.navLink}
            >
              Profile Explorer
            </button>
            <button
              onClick={() => setView('model')}
              style={view === 'model' ? styles.activeNavLink : styles.navLink}
            >
              Model Performance
            </button>
            <button
              onClick={() => setView('board')}
              style={view === 'board' ? styles.activeNavLink : styles.navLink}
            >
              Scrum Board
            </button>
            {isAdmin && (
              <button
                onClick={() => setView('users')}
                style={view === 'users' ? styles.activeNavLink : styles.navLink}
              >
                Manage Users
              </button>
            )}
          </div>
          <button onClick={handleLogout} style={styles.signOutBtn}>
            Sign Out
          </button>
        </nav>
      )}

      <main style={isAuth ? styles.mainContent : null}>
        {view === 'login' && (
          <Login
            onLoginSuccess={handleLoginSuccess}
            onNotify={addNotification}
          />
        )}
        {view === 'dashboard' && (
          <AnalyticsDashboard onViewChange={setView} onSelectCustomer={setSelectedCustomerId} setSelectedJobId={setSelectedJobId} onLogout={handleLogout} onNotify={addNotification} predictionRefreshToken={predictionRefreshToken} />
        )}
        {view === 'directory' && (
          <CustomerDirectory
            onViewChange={setView}
            onSelectCustomer={setSelectedCustomerId}
            onLogout={handleLogout}
            onNotify={addNotification}
            predictionRefreshToken={predictionRefreshToken}
          />
        )}
        {view === 'profile' && (
          <CustomerProfile
            onViewChange={setView}
            onLogout={handleLogout}
            onNotify={addNotification}
            selectedCustomerId={selectedCustomerId}
            setSelectedCustomerId={setSelectedCustomerId}
            onPredictionRecalculated={() => setPredictionRefreshToken(prev => prev + 1)}
          />
        )}
        {view === 'model' && (
          <ModelPerformance
            onViewChange={setView}
            onLogout={handleLogout}
            onNotify={addNotification}
          />
        )}
        {view === 'board' && (
          <ScrumBoard
            onViewChange={setView}
          />
        )}
        {view === 'users' && (
          <SignUp
            isAdminPanel={true}
            onNavigateToLogin={() => setView('login')}
          />
        )}
        {view === 'bulk_insights' && (
          <DatasetInsights
            jobId={selectedJobId}
            onViewChange={setView}
            setSelectedJobId={setSelectedJobId}
            onNotify={addNotification}
          />
        )}
      </main>
    </div>
  );
}

const styles = {
  appContainer: {
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
    background: '#07111f'
  },
  navbar: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '14px 28px',
    background: 'rgba(15, 23, 42, 0.75)',
    backdropFilter: 'blur(16px)',
    borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
    position: 'sticky',
    top: 0,
    zIndex: 1000
  },
  brand: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontFamily: 'Outfit, sans-serif',
    fontWeight: 700,
    fontSize: '1.2rem',
    background: 'linear-gradient(135deg, #818cf8 0%, #22d3ee 100%)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent'
  },
  brandDot: {
    color: 'rgba(255, 255, 255, 0.2)',
    fontSize: '0.9rem'
  },
  brandSub: {
    color: '#94a3b8',
    fontSize: '0.95rem',
    fontWeight: 400,
    letterSpacing: '0.05em'
  },
  navLinks: {
    display: 'flex',
    gap: '12px'
  },
  navLink: {
    background: 'none',
    border: 'none',
    color: '#94a3b8',
    fontSize: '0.95rem',
    padding: '8px 16px',
    borderRadius: '8px',
    cursor: 'pointer',
    fontWeight: 500,
    transition: 'all 0.2s'
  },
  activeNavLink: {
    background: 'rgba(99, 102, 241, 0.12)',
    border: 'none',
    color: '#818cf8',
    fontSize: '0.95rem',
    padding: '8px 16px',
    borderRadius: '8px',
    cursor: 'pointer',
    fontWeight: 600,
    boxShadow: '0 0 10px rgba(99, 102, 241, 0.08)'
  },
  signOutBtn: {
    background: 'rgba(239, 68, 68, 0.08)',
    border: '1px solid rgba(239, 68, 68, 0.2)',
    borderRadius: '8px',
    color: '#fca5a5',
    padding: '8px 16px',
    fontSize: '0.9rem',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s'
  },
  mainContent: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column'
  }
};

export default App;
