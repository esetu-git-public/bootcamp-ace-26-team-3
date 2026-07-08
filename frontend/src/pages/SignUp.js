import React, { useState } from 'react';
import * as apiService from '../services/api';

export default function SignUp({ onNavigateToLogin }) {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username || !email || !password) {
      setError('Please fill in all required fields (Username, Email, and Password).');
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters long.');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      await apiService.signup(username, email, password, fullName || null);

      setSuccess('Account created successfully! Redirecting to login...');
      setTimeout(() => {
        onNavigateToLogin();
      }, 2000);
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
          <span className="login-brand-icon">⚡</span>
          <span>Subscription Churn Predictor</span>
        </div>

        <div className="login-showcase-content">
          <div className="login-showcase-tag">
            📈 Advanced Predictive Analytics
          </div>
          <h1 className="login-showcase-title">
            Join Churn <br />
            Predictor Hub. <br />
            <span>Empower Decisions.</span>
          </h1>
          <p className="login-showcase-subtitle">
            Create an administrator account to upload bulk subscription data, run single-profile predictions, export automated retention PDF reports, and view historical churn probability distributions.
          </p>

          <div className="login-kpis-grid">
            <div className="login-kpi-card">
              <div className="login-kpi-value kpi-value-green">14.2%</div>
              <div className="login-kpi-label">Average Churn Rate Reductions</div>
            </div>
            <div className="login-kpi-card">
              <div className="login-kpi-value kpi-value-purple">96.5%</div>
              <div className="login-kpi-label">Prediction Accuracy Rate</div>
            </div>
          </div>
        </div>

        <div className="login-showcase-footer">
          © {new Date().getFullYear()} Churn Predictor Inc. All rights reserved.
        </div>
      </div>

      {/* Right Registration Panel */}
      <div className="login-right-panel">
        <div className="login-ambient-glow"></div>
        <div className="login-card-wrapper">
          <div className="login-glass-card">
            <div className="login-card-header">
              <h2 className="login-card-title">Create Account</h2>
              <p className="login-card-subtitle">Register to manage prediction dashboards</p>
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

            {success && (
              <div className="login-alert-error" style={{ background: 'rgba(16, 185, 129, 0.08)', borderColor: 'rgba(16, 185, 129, 0.2)', color: '#a7f3d0' }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                  <polyline points="22 4 12 14.01 9 11.01" />
                </svg>
                <span>{success}</span>
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div className="login-form-group">
                <label className="login-form-label" htmlFor="username">Username *</label>
                <div className="login-input-wrapper">
                  <input
                    id="username"
                    type="text"
                    placeholder="e.g., manager123"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className={`login-form-input ${error && !username ? 'input-has-error' : ''}`}
                    disabled={loading || success}
                    autoComplete="username"
                  />
                </div>
              </div>

              <div className="login-form-group">
                <label className="login-form-label" htmlFor="email">Email Address *</label>
                <div className="login-input-wrapper">
                  <input
                    id="email"
                    type="email"
                    placeholder="e.g., manager@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className={`login-form-input ${error && !email ? 'input-has-error' : ''}`}
                    disabled={loading || success}
                    autoComplete="email"
                  />
                </div>
              </div>

              <div className="login-form-group">
                <label className="login-form-label" htmlFor="fullName">Full Name</label>
                <div className="login-input-wrapper">
                  <input
                    id="fullName"
                    type="text"
                    placeholder="e.g., Jane Doe"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="login-form-input"
                    disabled={loading || success}
                    autoComplete="name"
                  />
                </div>
              </div>

              <div className="login-form-group">
                <label className="login-form-label" htmlFor="password">Password *</label>
                <div className="login-input-wrapper">
                  <input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="•••••••• (Min. 6 chars)"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className={`login-form-input ${error && !password ? 'input-has-error' : ''}`}
                    disabled={loading || success}
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="password-toggle-btn"
                    title={showPassword ? "Hide Password" : "Show Password"}
                    disabled={loading || success}
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

              <button
                type="submit"
                className="login-submit-btn"
                disabled={loading || success}
                style={{ marginTop: '10px' }}
              >
                {loading ? (
                  <>
                    <span className="login-spinner"></span>
                    <span>Creating Account...</span>
                  </>
                ) : (
                  <span>Register</span>
                )}
              </button>
            </form>

            <div className="login-signup-prompt" style={{ marginTop: '20px', textAlign: 'center', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
              Already have an account?{' '}
              <a
                href="#login"
                onClick={(e) => {
                  e.preventDefault();
                  onNavigateToLogin();
                }}
                style={{ color: 'var(--color-accent)', fontWeight: '600', textDecoration: 'none' }}
              >
                Sign In
              </a>
            </div>

            <div className="login-card-footer">
              Registration allows system administrator access. <br />
              All actions are logged for audit compliance.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
