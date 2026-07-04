import React, { useState, useEffect } from 'react';
import Login from './pages/Login';
import AnalyticsDashboard from './pages/AnalyticsDashboard';
import CustomerProfile from './pages/CustomerProfile';

function App() {
  const [view, setView] = useState('login');
  const [token, setToken] = useState(localStorage.getItem('access_token'));

  useEffect(() => {
    if (token) {
      setView('dashboard');
    } else {
      setView('login');
    }
  }, [token]);

  const handleLoginSuccess = (newToken) => {
    localStorage.setItem('access_token', newToken);
    setToken(newToken);
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    setToken(null);
  };

  return (
    <div className="App">
      {view === 'login' && (
        <Login onLoginSuccess={handleLoginSuccess} />
      )}
      {view === 'dashboard' && (
        <AnalyticsDashboard onViewChange={setView} onLogout={handleLogout} />
      )}
      {view === 'profile' && (
        <CustomerProfile onViewChange={setView} onLogout={handleLogout} />
      )}
    </div>
  );
}

export default App;