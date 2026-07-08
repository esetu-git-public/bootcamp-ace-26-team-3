import React, { useState } from 'react';
import * as apiService from '../services/api';

export default function Login({ onLoginSuccess, onNavigateToSignup }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username || !password) {
      setError('Please enter both username and password.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const data = await apiService.login(username, password);
      onLoginSuccess(data.access_token, rememberMe);
    } catch (err) {
      setError(err.message || 'Connection error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page-container">
      {/* Left Showcase Panel */}
      <div className="login-left-panel">
        <div className="login-brand">
          <span className="login-brand-icon">CE</span>
          <span>Customer Engagement Tracker</span>
        </div>

        <div className="login-showcase-content">
          <div className="login-showcase-tag">
            Customer Engagement Intelligence
          </div>
          <h1 className="login-showcase-title">
            Track Signals. <br />
            Prioritize Outreach. <br />
            <span>Grow Customer Value.</span>
          </h1>
          <p className="login-showcase-subtitle">
            Sign in to monitor engagement health, spot at-risk accounts, and focus every retention action where it can make the biggest difference.
          </p>

          <div className="login-kpis-grid">
            <div className="login-kpi-card">
              <div className="login-kpi-value kpi-value-green">14.2%</div>
              <div className="login-kpi-label">Average Churn Reduction</div>
            </div>
            <div className="login-kpi-card">
              <div className="login-kpi-value kpi-value-purple">96.5%</div>
              <div className="login-kpi-label">Prediction Accuracy</div>
            </div>
          </div>
        </div>

        <div className="login-showcase-footer">
          (c) {new Date().getFullYear()} Customer Engagement Tracker. All rights reserved.
        </div>
      </div>

      {/* Right Login Panel */}
      <div className="login-right-panel">
        <div className="login-ambient-glow"></div>
        <div className="login-card-wrapper">
          <div className="login-glass-card">
            <div className="login-card-header">
              <h2 className="login-card-title">Welcome Back</h2>
              <p className="login-card-subtitle">Sign in to access your engagement dashboard</p>
            </div>

            {error && (
              <div className="login-alert-error">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div className="login-form-group">
                <label className="login-form-label" htmlFor="username">Email or Username</label>
                <div className="login-input-wrapper">
                  <input
                    id="username"
                    type="text"
                    placeholder="e.g., admin"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className={`login-form-input ${error && !username ? 'input-has-error' : ''}`}
                    disabled={loading}
                    autoComplete="username"
                  />
                </div>
              </div>

              <div className="login-form-group">
                <label className="login-form-label" htmlFor="password">Password</label>
                <div className="login-input-wrapper">
                  <input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className={`login-form-input ${error && !password ? 'input-has-error' : ''}`}
                    disabled={loading}
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="password-toggle-btn"
                    title={showPassword ? "Hide Password" : "Show Password"}
                    disabled={loading}
                  >
                    {showPassword ? (
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                        <line x1="1" y1="1" x2="23" y2="23" />
                      </svg>
                    ) : (
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>

              <div className="login-form-options">
                <label className="remember-me-checkbox">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                  />
                  <span>Remember me</span>
                </label>
                <a href="#forgot" className="forgot-password-link" onClick={(e) => e.preventDefault()}>
                  Forgot password?
                </a>
              </div>

              <button
                type="submit"
                className="login-submit-btn"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <span className="login-spinner"></span>
                    <span>Signing In...</span>
                  </>
                ) : (
                  <span>Sign In</span>
                )}
              </button>
            </form>

            <div className="login-signup-prompt" style={{ marginTop: '20px', textAlign: 'center', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
              Don't have an account?{' '}
              <a
                href="#signup"
                onClick={(e) => {
                  e.preventDefault();
                  if (onNavigateToSignup) onNavigateToSignup();
                }}
                style={{ color: 'var(--color-accent)', fontWeight: '600', textDecoration: 'none' }}
              >
                Sign Up
              </a>
            </div>

            <div className="login-card-footer">
              Credentials issue? Contact your administrator <br />
              or systems team lead.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
