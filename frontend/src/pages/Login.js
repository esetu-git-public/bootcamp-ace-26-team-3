import React, { useState } from 'react';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export default function Login({ onLoginSuccess }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [focusedField, setFocusedField] = useState(null);
  const [hovered, setHovered] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username || !password) {
      setError('Please enter both username and password.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username,
          password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Incorrect username or password');
      }

      onLoginSuccess(data.access_token);
    } catch (err) {
      setError(err.message || 'Connection error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.glowBg}></div>
      <div style={styles.card}>
        {error && (
          <div style={styles.errorAlert}>
            <span style={styles.errorIcon}>⚠️</span>
            <span style={styles.errorText}>{error}</span>
          </div>
        )}

        <div style={styles.header}>
          <div style={styles.logo}>⚡</div>
          <h2 style={styles.title}>Subscription Churn Predictor</h2>
          <p style={styles.subtitle}>Enter credentials to access manager panel</p>
        </div>

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.inputGroup}>
            <label style={styles.label}>Email or Username</label>
            <input
              type="text"
              placeholder="e.g., admin"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              onFocus={() => setFocusedField('username')}
              onBlur={() => setFocusedField(null)}
              style={{
                ...styles.input,
                ...(focusedField === 'username' ? styles.inputFocus : {}),
                ...(error ? styles.inputError : {}),
              }}
              disabled={loading}
            />
          </div>

          <div style={styles.inputGroup}>
            <label style={styles.label}>Password</label>
            <input
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onFocus={() => setFocusedField('password')}
              onBlur={() => setFocusedField(null)}
              style={{
                ...styles.input,
                ...(focusedField === 'password' ? styles.inputFocus : {}),
                ...(error ? styles.inputError : {}),
              }}
              disabled={loading}
            />
          </div>

          <div style={styles.row}>
            <label style={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                style={styles.checkbox}
              />
              <span>Remember me</span>
            </label>
          </div>

          <button
            type="submit"
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => setHovered(false)}
            style={{
              ...styles.button,
              ...(hovered ? styles.buttonHover : {}),
              ...(loading ? styles.buttonLoading : {}),
            }}
            disabled={loading}
          >
            {loading ? 'Signing In...' : 'Sign In'}
          </button>
        </form>

        <div style={styles.footer}>
          <span>Credentials issue? Contact Tech Lead</span>
        </div>
      </div>
    </div>
  );
}

const styles = {
  container: {
    position: 'relative',
    minHeight: '100vh',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    background: '#0F0F11',
    fontFamily: 'Inter, system-ui, sans-serif',
    overflow: 'hidden',
  },
  glowBg: {
    position: 'absolute',
    width: '400px',
    height: '400px',
    background: 'radial-gradient(circle, rgba(59, 130, 246, 0.15) 0%, rgba(99, 102, 241, 0.05) 50%, rgba(0,0,0,0) 100%)',
    top: '20%',
    left: '30%',
    filter: 'blur(40px)',
    zIndex: 1,
  },
  card: {
    position: 'relative',
    zIndex: 2,
    width: '100%',
    maxWidth: '420px',
    padding: '40px 32px',
    background: 'rgba(25, 25, 29, 0.65)',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '24px',
    backdropFilter: 'blur(20px)',
    boxShadow: '0 20px 40px rgba(0, 0, 0, 0.5)',
    display: 'flex',
    flexDirection: 'column',
  },
  errorAlert: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    background: 'rgba(239, 68, 68, 0.12)',
    border: '1px solid rgba(239, 68, 68, 0.25)',
    borderRadius: '12px',
    padding: '12px 16px',
    marginBottom: '24px',
  },
  errorIcon: {
    fontSize: '1rem',
  },
  errorText: {
    color: '#FCA5A5',
    fontSize: '0.85rem',
    fontWeight: '500',
  },
  header: {
    textAlign: 'center',
    marginBottom: '32px',
  },
  logo: {
    fontSize: '2.5rem',
    background: 'linear-gradient(135deg, #3B82F6 0%, #6366F1 100%)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    marginBottom: '12px',
    fontWeight: 'bold',
  },
  title: {
    color: '#FFFFFF',
    fontSize: '1.5rem',
    fontWeight: '700',
    margin: '0 0 8px 0',
    letterSpacing: '-0.025em',
  },
  subtitle: {
    color: '#9CA3AF',
    fontSize: '0.875rem',
    margin: 0,
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  inputGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  label: {
    color: '#D1D5DB',
    fontSize: '0.875rem',
    fontWeight: '500',
  },
  input: {
    width: '100%',
    boxSizing: 'border-box',
    background: 'rgba(15, 15, 17, 0.8)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: '12px',
    padding: '12px 16px',
    color: '#FFFFFF',
    fontSize: '0.95rem',
    outline: 'none',
    transition: 'border-color 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
  },
  inputFocus: {
    borderColor: '#3B82F6',
    boxShadow: '0 0 0 1px rgba(59, 130, 246, 0.3)',
  },
  inputError: {
    borderColor: 'rgba(239, 68, 68, 0.5)',
  },
  row: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: '4px',
  },
  checkboxLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    color: '#9CA3AF',
    fontSize: '0.85rem',
    cursor: 'pointer',
  },
  checkbox: {
    accentColor: '#3B82F6',
    cursor: 'pointer',
  },
  button: {
    background: 'linear-gradient(135deg, #3B82F6 0%, #6366F1 100%)',
    border: 'none',
    borderRadius: '12px',
    padding: '14px',
    color: '#FFFFFF',
    fontSize: '1rem',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'transform 0.2s, box-shadow 0.2s',
    boxShadow: '0 4px 12px rgba(59, 130, 246, 0.2)',
    marginTop: '10px',
  },
  buttonHover: {
    transform: 'scale(1.02)',
    boxShadow: '0 0 20px rgba(59, 130, 246, 0.4)',
  },
  buttonLoading: {
    opacity: 0.7,
    cursor: 'not-allowed',
  },
  footer: {
    textAlign: 'center',
    marginTop: '28px',
    color: '#6B7280',
    fontSize: '0.75rem',
  },
};
