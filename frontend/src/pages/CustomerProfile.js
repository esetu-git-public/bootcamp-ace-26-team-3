import React, { useState, useEffect, useRef } from 'react';
import * as apiService from '../services/api';
import * as mlModel from '../services/mlModel';
import { ModelPredictionCard, RiskGauge, PredictionTimeline } from '../components/ModelPredictionCard';
import { formatPercent } from '../utils/percent';

// ─── CSS injected once ───────────────────────────────────────────────────────
if (typeof document !== 'undefined' && !document.getElementById('cp-keyframes')) {
  const s = document.createElement('style');
  s.id = 'cp-keyframes';
  s.textContent = `
    @keyframes fadeSlideUp  { from { opacity:0; transform:translateY(18px); } to { opacity:1; transform:translateY(0); } }
    @keyframes bar-grow     { from { width: 0 !important; } to {} }
    .cp-card { animation: fadeSlideUp .38s ease both; }
    .cp-bar  { animation: bar-grow .6s cubic-bezier(.22,1,.36,1) both; }
    .cp-stat-card:hover { transform: translateY(-3px) scale(1.01); box-shadow: 0 16px 40px rgba(0,0,0,.45) !important; }
    .cp-predict-btn:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(16,185,129,.4) !important; }
    .cp-search-btn:hover { background: #4f46e5 !important; }
  `;
  document.head.appendChild(s);
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
const AVATAR_PALETTE = ['#6366f1','#10b981','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#ec4899'];

function getAvatarColor(id = '') {
  const n = id.split('').reduce((a, c) => a + c.charCodeAt(0), 0);
  return AVATAR_PALETTE[n % AVATAR_PALETTE.length];
}

function getInitials(id = '') {
  return id.replace(/[^a-zA-Z0-9]/g, '').slice(0, 2).toUpperCase() || '??';
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function SatisfactionDots({ score }) {
  return (
    <div style={{ display: 'flex', gap: '5px', alignItems: 'center' }}>
      {Array.from({ length: 10 }, (_, i) => {
        const lit = i < score;
        const col = score <= 3 ? '#ef4444' : score <= 6 ? '#f59e0b' : '#10b981';
        return (
          <div key={i} style={{
            width: '10px', height: '10px', borderRadius: '50%',
            background: lit ? col : 'rgba(255,255,255,0.1)',
            boxShadow: lit ? `0 0 6px ${col}` : 'none',
            transition: 'all .2s'
          }} />
        );
      })}
      <span style={{ color: '#cbd5e1', fontSize: '.8rem', marginLeft: '6px' }}>
        {score}/10
      </span>
    </div>
  );
}

function MetricBar({ label, value, max, unit = '', color = '#6366f1', delay = 0 }) {
  const pct = Math.min(100, Math.round((value / max) * 100));
  return (
    <div style={{ marginBottom: '12px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px', fontSize: '.82rem', color: '#94a3b8' }}>
        <span>{label}</span>
        <span style={{ color: '#e2e8f0', fontWeight: 600 }}>{value}{unit}</span>
      </div>
      <div style={{ background: 'rgba(255,255,255,.07)', borderRadius: '6px', height: '7px', overflow: 'hidden' }}>
        <div className="cp-bar" style={{
          width: `${pct}%`, height: '100%', borderRadius: '6px',
          background: `linear-gradient(90deg, ${color}99, ${color})`,
          animationDelay: `${delay}s`
        }} />
      </div>
    </div>
  );
}

function StatPill({ label, value, color = '#38bdf8', icon }) {
  return (
    <div className="cp-stat-card" style={{
      background: 'rgba(17,24,39,.85)', border: '1px solid rgba(255,255,255,.09)',
      borderRadius: '12px', padding: '14px 18px', display: 'flex', flexDirection: 'column',
      gap: '4px', transition: 'all .22s', boxShadow: '0 6px 20px rgba(0,0,0,.25)', cursor: 'default'
    }}>
      <span style={{ fontSize: '1.4rem' }}>{icon}</span>
      <span style={{ fontSize: '1.25rem', fontWeight: 700, color }}>{value}</span>
      <span style={{ fontSize: '.72rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '.07em' }}>{label}</span>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function CustomerProfile({ onViewChange, onLogout, onNotify, selectedCustomerId, setSelectedCustomerId, onPredictionRecalculated }) {
  const [customerId, setCustomerId]   = useState(selectedCustomerId || '');
  const [searchId,   setSearchId]     = useState(selectedCustomerId || '');
  const [customer,   setCustomer]     = useState(null);
  const [prediction, setPrediction]   = useState(null);
  const [history,    setHistory]      = useState([]);
  const [loading,    setLoading]      = useState(false);
  const [error,      setError]        = useState(null);
  const [predicting, setPredicting]   = useState(false);
  const [notFound,   setNotFound]     = useState(false);
  const inputRef = useRef(null);

  const fetchCustomerDetails = async (id) => {
    if (!id) return;
    setLoading(true);
    setError(null);
    setPrediction(null);
    setNotFound(false);
    try {
      const data = await apiService.getCustomerProfile(id);
      setCustomer(data);
      if (data.churn_probability !== null && data.churn_probability !== undefined) {
        setPrediction({
          will_cancel:                  data.will_cancel,
          churn_probability:            data.churn_probability,
          probability_confidence_lower: data.probability_confidence_lower,
          probability_confidence_upper: data.probability_confidence_upper,
          risk_category:               data.risk_category,
          explainability:              data.explainability,
          recommendation_type:         data.recommendation_type,
          recommendation_desc:         data.recommendation_desc,
        });
      }
      fetchPredictionHistory(id);
    } catch (err) {
      if (err.status === 401)      { onLogout({ silent: true }); }
      else if (err.status === 404) { setNotFound(true); setCustomer(null); }
      else                         { setError(err.message || 'Failed to load customer details'); setCustomer(null); }
    } finally {
      setLoading(false);
    }
  };

  const runChurnPrediction = async () => {
    if (!customer) return;
    setPredicting(true);
    setError(null);
    try {
      const data = await mlModel.getSinglePrediction(customerId);
      setPrediction(data);
      if (onPredictionRecalculated) {
        onPredictionRecalculated();
      }
      await fetchCustomerDetails(customerId);
      if (onNotify) {
        onNotify({
          type: 'success',
          title: 'Prediction ready',
          message: `Churn prediction updated for ${customerId}.`
        });
      }
    } catch (err) {
      if (err.status === 401) { onLogout({ silent: true }); }
      else { setError(err.message || 'Failed to run churn prediction model.'); }
    } finally { setPredicting(false); }
  };

  const fetchPredictionHistory = async (id) => {
    try {
      const data = await mlModel.getPredictionHistory(id);
      setHistory(data || []);
    } catch (err) {
      if (err.status !== 401) console.error('Failed to load prediction history', err);
    }
  };

  useEffect(() => {
    if (selectedCustomerId) {
      setCustomerId(selectedCustomerId);
      setSearchId(selectedCustomerId);
      fetchCustomerDetails(selectedCustomerId);
    }
  // eslint-disable-next-line
  }, [selectedCustomerId]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    const id = searchId.trim();
    if (!id) return;
    setCustomerId(id);
    if (setSelectedCustomerId) setSelectedCustomerId(id);
    else fetchCustomerDetails(id);
  };

  const avatarColor = getAvatarColor(customer?.customer_id || '');
  const riskColor   = prediction?.risk_category === 'High'   ? '#ef4444'
                    : prediction?.risk_category === 'Medium' ? '#f59e0b'
                    : '#10b981';

  return (
    <div style={S.page}>

      {/* Page Header */}
      <header style={S.pageHeader}>
        <div>
          <p style={S.eyebrow}>Deep Diagnostics &amp; Explainability</p>
          <h1 style={S.title}>Customer Profile Explorer</h1>
          <p style={S.subtitle}>
            Behavioral audit, feature importances, and historical model logs for individual customer profiles.
          </p>
        </div>
      </header>

      {/* Search Bar */}
      <form onSubmit={handleSearchSubmit} style={S.searchForm}>
        <div style={S.searchInputWrap}>
          <span style={{ fontSize: '1rem' }}>🔍</span>
          <input
            ref={inputRef}
            type="text"
            placeholder="Enter Customer ID  (e.g. 100)"
            value={searchId}
            onChange={(e) => setSearchId(e.target.value)}
            style={S.searchInput}
          />
        </div>
        <button type="submit" className="cp-search-btn" style={S.searchBtn}>
          Search Profile
        </button>
      </form>

      {/* Loading */}
      {loading && (
        <div style={S.loaderWrap}>
          <div style={S.spinner} />
          <span style={{ color: '#38bdf8', fontStyle: 'italic' }}>Accessing customer registry…</span>
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div style={S.errorBanner}>⚠️ {error}</div>
      )}

      {/* Not Found */}
      {notFound && !loading && (
        <div style={S.centeredCard}>
          <div style={{ fontSize: '3rem', marginBottom: '12px' }}>🔎</div>
          <h3 style={{ margin: '0 0 8px', color: '#e2e8f0' }}>No Customer Found</h3>
          <p style={{ margin: 0, color: '#64748b', maxWidth: '360px', textAlign: 'center', lineHeight: 1.6 }}>
            Customer ID <strong style={{ color: '#38bdf8' }}>{customerId}</strong> was not found in the database.
            Please verify the ID and try again.
          </p>
        </div>
      )}

      {/* Empty State */}
      {!loading && !customer && !notFound && !error && (
        <div style={S.centeredCard}>
          <div style={{ fontSize: '3.5rem', marginBottom: '16px' }}>👤</div>
          <h3 style={{ margin: '0 0 8px', color: '#e2e8f0', fontSize: '1.3rem' }}>No Profile Loaded</h3>
          <p style={{ margin: '0 0 20px', color: '#64748b', maxWidth: '400px', textAlign: 'center', lineHeight: 1.6 }}>
            Enter a Customer ID above and click <strong style={{ color: '#818cf8' }}>Search Profile</strong> to view
            the behavioral audit, model predictions, and SHAP explainability.
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: '#64748b', fontSize: '.82rem' }}>Try:</span>
            {['1', '42', '100'].map(id => (
              <button key={id} onClick={() => {
                setSearchId(id);
                setCustomerId(id);
                if (setSelectedCustomerId) setSelectedCustomerId(id);
                else fetchCustomerDetails(id);
              }} style={S.exampleIdBtn}>{id}</button>
            ))}
          </div>
        </div>
      )}

      {/* ── Profile Content ── */}
      {!loading && customer && (
        <div style={{ animation: 'fadeSlideUp .4s ease both' }}>

          {/* Hero Banner */}
          <div className="cp-card" style={S.heroBanner}>
            <div style={{ ...S.avatar, background: avatarColor }}>
              {getInitials(customer.customer_id)}
              {prediction && (
                <div style={{ ...S.avatarBadge, background: riskColor }}>
                  {prediction.risk_category?.[0] || '?'}
                </div>
              )}
            </div>

            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
                <h2 style={S.heroId}>{customer.customer_id}</h2>
                {prediction && (
                  <span style={{ ...S.heroBadge, background: `${riskColor}22`, color: riskColor, border: `1px solid ${riskColor}44` }}>
                    {prediction.risk_category} Risk
                  </span>
                )}
                {prediction?.will_cancel === 1 && (
                  <span style={S.churnFlag}>🔴 Predicted Churn</span>
                )}
                {prediction?.will_cancel === 0 && (
                  <span style={S.stableFlag}>🟢 Predicted Stable</span>
                )}
              </div>
              <p style={S.heroMeta}>
                {customer.age} yrs &nbsp;•&nbsp; {customer.income_level} Income &nbsp;•&nbsp; {customer.device_type} &nbsp;•&nbsp; {customer.payment_mode}
              </p>
              {customer.created_at && (
                <p style={{ ...S.heroMeta, marginTop: '2px', color: '#475569' }}>
                  Member since {new Date(customer.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long' })}
                </p>
              )}
            </div>

            {prediction && (
              <div style={{ marginLeft: 'auto', flexShrink: 0 }}>
                <RiskGauge probability={prediction.churn_probability} />
              </div>
            )}
          </div>

          {/* KPI Strip */}
          <div style={S.kpiStrip}>
            <StatPill icon="📅" label="Tenure"          value={`${customer.tenure_months}m`}     color="#38bdf8" />
            <StatPill icon="💳" label="Monthly Spend"   value={`$${Number(customer.monthly_total_spend).toFixed(0)}`} color="#a78bfa" />
            <StatPill icon="📺" label="Subscriptions"   value={customer.number_of_subscriptions} color="#34d399" />
            <StatPill icon="⏱️" label="Wkly Usage"      value={`${customer.avg_usage_hours_per_week}h`} color="#fb923c" />
            <StatPill icon="🎫" label="Support Tickets" value={customer.customer_support_interactions} color="#f87171" />
            <StatPill icon="⭐" label="Satisfaction"    value={`${customer.satisfaction_score}/10`}
              color={customer.satisfaction_score <= 3 ? '#ef4444' : customer.satisfaction_score <= 6 ? '#f59e0b' : '#10b981'} />
            {prediction && (
              <StatPill icon="📊" label="Churn Risk" value={formatPercent(prediction.churn_probability)} color={riskColor} />
            )}
          </div>

          {/* Main 2-column Grid */}
          <div style={S.mainGrid}>

            {/* ── LEFT COLUMN ── */}
            <div style={S.leftCol}>

              {/* Core Demographics */}
              <div className="cp-card" style={S.card}>
                <h3 style={S.cardTitle}>
                  <span style={S.titleDot} />
                  Core Customer Profile
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                  {[
                    { label: 'Customer ID',    value: <span style={{ fontFamily: 'monospace', color: '#38bdf8', fontWeight: 700 }}>{customer.customer_id}</span> },
                    { label: 'Age',            value: `${customer.age} years old` },
                    { label: 'Income Level',   value: customer.income_level },
                    { label: 'Device',         value: customer.device_type },
                    { label: 'Payment Mode',   value: customer.payment_mode },
                    { label: 'Discounts Used', value: customer.discount_used ? '✅ Yes' : '❌ No' },
                  ].map(({ label, value }) => (
                    <div key={label} style={S.profileRow}>
                      <span style={S.profileLabel}>{label}</span>
                      <span style={S.profileValue}>{value}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Engagement Metrics */}
              <div className="cp-card" style={S.card}>
                <h3 style={S.cardTitle}>
                  <span style={S.titleDot} />
                  Engagement &amp; Activity Metrics
                </h3>

                <div style={{ marginBottom: '20px', paddingBottom: '16px', borderBottom: '1px solid rgba(255,255,255,.07)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <span style={{ fontSize: '.82rem', color: '#94a3b8' }}>Satisfaction Score</span>
                    <SatisfactionDots score={customer.satisfaction_score} />
                  </div>
                </div>

                <MetricBar label="Weekly Usage Hours"    value={customer.avg_usage_hours_per_week}      max={50}  unit="h"   color="#38bdf8" delay={0}    />
                <MetricBar label="Monthly Spend"         value={Number(customer.monthly_total_spend).toFixed(0)} max={250} unit=""    color="#a78bfa" delay={0.05} />
                <MetricBar label="App Switch Frequency"  value={customer.app_switch_frequency}          max={50}  unit="/hr" color="#fb923c" delay={0.10} />
                <MetricBar label="Support Interactions"  value={customer.customer_support_interactions} max={15}  unit=""    color="#f87171" delay={0.15} />
                <MetricBar label="Active Subscriptions"  value={customer.number_of_subscriptions}       max={10}  unit=""    color="#34d399" delay={0.20} />
                <MetricBar label="Tenure Months"         value={customer.tenure_months}                 max={60}  unit="m"   color="#06b6d4" delay={0.25} />

                <button
                  className="cp-predict-btn"
                  onClick={runChurnPrediction}
                  disabled={predicting}
                  style={predicting ? S.predictBtnDisabled : S.predictBtn}
                >
                  {predicting
                    ? <><span style={S.btnSpinner} />Calculating Churn Model…</>
                    : <>⚡ Recalculate Prediction</>
                  }
                </button>
              </div>

              {/* Segment Benchmarks */}
              <div className="cp-card" style={S.card}>
                <h3 style={S.cardTitle}>
                  <span style={{ ...S.titleDot, background: '#f59e0b' }} />
                  Segment Benchmarks
                </h3>
                <p style={S.helperText}>Compared to {customer.income_level}-income cohort averages:</p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {[
                    { metric: 'Satisfaction',  cv: customer.satisfaction_score,                        avg: 5.2,  higherBetter: true,  unit: '/10', prefix: '' },
                    { metric: 'Weekly Usage',  cv: customer.avg_usage_hours_per_week,                  avg: 14.8, higherBetter: true,  unit: 'h',   prefix: '' },
                    { metric: 'Monthly Spend', cv: Number(customer.monthly_total_spend),               avg: 72.4, higherBetter: true,  unit: '',    prefix: '$' },
                    { metric: 'Support Calls', cv: customer.customer_support_interactions,             avg: 2.1,  higherBetter: false, unit: '',    prefix: '' },
                  ].map(({ metric, cv, avg, higherBetter, unit, prefix }) => {
                    const diff   = cv - avg;
                    const better = higherBetter ? diff >= 0 : diff <= 0;
                    const col    = better ? '#34d399' : '#f87171';
                    return (
                      <div key={metric} style={{ display: 'grid', gridTemplateColumns: '110px 1fr 80px 60px', gap: '8px', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,.05)' }}>
                        <span style={{ fontSize: '.85rem', color: '#94a3b8' }}>{metric}</span>
                        <span style={{ fontSize: '.85rem', fontWeight: 700, color: '#e2e8f0' }}>{prefix}{typeof cv === 'number' ? cv.toFixed(1) : cv}{unit}</span>
                        <span style={{ fontSize: '.75rem', color: '#64748b' }}>avg {prefix}{avg}{unit}</span>
                        <span style={{ fontSize: '.8rem', fontWeight: 700, color: col }}>{diff >= 0 ? '▲' : '▼'} {Math.abs(diff).toFixed(1)}{unit}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* ── RIGHT COLUMN ── */}
            <div style={S.rightCol}>

              {/* Model Prediction Card */}
              <ModelPredictionCard
                prediction={prediction}
                loading={predicting}
                error={null}
                onRegenerate={runChurnPrediction}
              />

              {/* Prediction Timeline */}
              <PredictionTimeline predictions={history} />

              {/* Retention Recommendation */}
              {prediction && (
                <div style={S.recommendCard}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px', marginBottom: '14px', flexWrap: 'wrap' }}>
                    <div>
                      <h4 style={{ margin: '0 0 4px', fontSize: '1.05rem', fontWeight: 700, color: '#e2e8f0' }}>
                        {prediction.will_cancel === 1 ? '🚨' : '✅'} Retention Recommendation
                      </h4>
                      <p style={{ margin: 0, fontSize: '.78rem', color: '#64748b' }}>Based on ML model output and behavioral signals</p>
                    </div>
                    <div style={{ padding: '6px 14px', borderRadius: '20px', fontWeight: 700, fontSize: '.82rem', background: `${riskColor}22`, color: riskColor, border: `1px solid ${riskColor}44`, whiteSpace: 'nowrap' }}>
                      {prediction.recommendation_type}
                    </div>
                  </div>
                  <p style={{ margin: 0, color: '#cbd5e1', fontSize: '.9rem', lineHeight: 1.65 }}>{prediction.recommendation_desc}</p>
                </div>
              )}

              {/* SHAP Explainability */}
              {prediction?.explainability && (
                <div className="cp-card" style={S.card}>
                  <h3 style={S.cardTitle}>
                    <span style={{ ...S.titleDot, background: '#a78bfa' }} />
                    Local SHAP Feature Importance
                  </h3>
                  <p style={S.helperText}>
                    <span style={{ color: '#f87171' }}>Red = increases</span> churn risk &nbsp;·&nbsp;
                    <span style={{ color: '#34d399' }}>Green = reduces</span> churn risk
                  </p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {Object.entries(prediction.explainability)
                      .sort(([, a], [, b]) => Math.abs(b) - Math.abs(a))
                      .map(([key, val]) => {
                        const isIncrease = val > 0;
                        const widthPct   = Math.min(100, Math.round((Math.abs(val) / 2.0) * 100));
                        const col        = isIncrease ? '#ef4444' : '#10b981';
                        return (
                          <div key={key} style={{ display: 'grid', gridTemplateColumns: '160px 1fr 54px', gap: '10px', alignItems: 'center', fontSize: '.84rem' }}>
                            <span style={{ color: '#cbd5e1', textTransform: 'capitalize', fontWeight: 500, lineHeight: 1.3 }}>
                              {key.replace(/_/g, ' ')}
                            </span>
                            <div style={{ background: 'rgba(255,255,255,.06)', height: '8px', borderRadius: '4px', overflow: 'hidden' }}>
                              <div className="cp-bar" style={{ width: `${widthPct}%`, height: '100%', borderRadius: '4px', background: `linear-gradient(90deg,${col}66,${col})` }} />
                            </div>
                            <span style={{ textAlign: 'right', fontWeight: 700, color: col }}>
                              {isIncrease ? '+' : ''}{val.toFixed(3)}
                            </span>
                          </div>
                        );
                      })}
                  </div>
                </div>
              )}

              {/* Prediction Audit Log */}
              <div className="cp-card" style={S.card}>
                <h3 style={S.cardTitle}>
                  <span style={{ ...S.titleDot, background: '#06b6d4' }} />
                  Model Audit Log
                </h3>
                {history.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {history.map((log, idx) => {
                      const isChurn = log.prediction_result === 1;
                      const cat     = log.risk_category;
                      const catCol  = cat === 'High' ? '#fca5a5' : cat === 'Medium' ? '#fde047' : '#a7f3d0';
                      const catBg   = cat === 'High' ? 'rgba(239,68,68,.12)' : cat === 'Medium' ? 'rgba(245,158,11,.12)' : 'rgba(16,185,129,.12)';
                      return (
                        <div key={log.history_id} style={{ display: 'grid', gridTemplateColumns: '1fr auto auto auto', gap: '12px', alignItems: 'center', padding: '10px 8px', borderRadius: '8px', borderBottom: '1px solid rgba(255,255,255,.05)' }}>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                            <span style={{ color: '#94a3b8', fontSize: '.8rem' }}>{new Date(log.evaluated_at).toLocaleString()}</span>
                            {idx === 0 && <span style={{ fontSize: '.7rem', color: '#818cf8', fontWeight: 600 }}>Latest Run</span>}
                          </div>
                          <span style={{ padding: '3px 10px', borderRadius: '6px', fontSize: '.76rem', fontWeight: 700, background: isChurn ? 'rgba(239,68,68,.12)' : 'rgba(16,185,129,.12)', color: isChurn ? '#fca5a5' : '#a7f3d0', border: `1px solid ${isChurn ? 'rgba(239,68,68,.25)' : 'rgba(16,185,129,.25)'}` }}>
                            {isChurn ? 'Churn' : 'Retain'}
                          </span>
                          <span style={{ fontWeight: 700, color: '#e2e8f0', fontSize: '.9rem' }}>{formatPercent(log.risk_score)} Risk</span>
                          <span style={{ padding: '3px 8px', borderRadius: '6px', fontSize: '.72rem', fontWeight: 700, background: catBg, color: catCol }}>{cat}</span>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p style={{ color: '#64748b', fontStyle: 'italic', textAlign: 'center', padding: '20px 0', margin: 0 }}>
                    No historical prediction runs recorded for this profile.
                  </p>
                )}
              </div>

            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Styles ──────────────────────────────────────────────────────────────────
const S = {
  page:       { minHeight: '100vh', background: '#07111f', color: '#f7f8fc', padding: '28px 32px', fontFamily: "'Inter', 'Outfit', Arial, sans-serif" },
  pageHeader: { marginBottom: '24px' },
  eyebrow:    { textTransform: 'uppercase', letterSpacing: '.18em', color: '#7dd3fc', fontSize: '.72rem', margin: '0 0 4px' },
  title:      { margin: '0 0 8px', fontSize: '2rem', fontWeight: 700, lineHeight: 1.2 },
  subtitle:   { margin: 0, color: '#64748b', maxWidth: '620px', lineHeight: 1.7, fontSize: '.92rem' },

  searchForm:      { display: 'flex', gap: '10px', marginBottom: '28px', maxWidth: '560px' },
  searchInputWrap: { flex: 1, display: 'flex', alignItems: 'center', background: 'rgba(15,23,42,.9)', border: '1px solid rgba(255,255,255,.1)', borderRadius: '12px', padding: '0 14px', gap: '10px' },
  searchInput:     { flex: 1, background: 'transparent', border: 'none', outline: 'none', color: '#f7f8fc', fontSize: '.95rem', padding: '13px 0' },
  searchBtn:       { background: '#6366f1', color: '#fff', border: 'none', borderRadius: '12px', padding: '0 24px', fontWeight: 700, cursor: 'pointer', transition: 'all .2s', fontSize: '.92rem', whiteSpace: 'nowrap' },

  loaderWrap:  { display: 'flex', alignItems: 'center', gap: '14px', justifyContent: 'center', padding: '60px 0' },
  spinner:     { width: '32px', height: '32px', border: '3px solid rgba(255,255,255,.08)', borderTop: '3px solid #6366f1', borderRadius: '50%', animation: 'spin 1s linear infinite' },
  errorBanner: { background: 'rgba(239,68,68,.1)', border: '1px solid rgba(239,68,68,.25)', padding: '14px 18px', borderRadius: '12px', color: '#fca5a5', marginBottom: '20px', fontSize: '.9rem' },

  centeredCard: { display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '70px 20px', background: 'rgba(17,24,39,.7)', border: '1px solid rgba(255,255,255,.08)', borderRadius: '20px' },
  exampleIdBtn: { background: 'rgba(56,189,248,.1)', color: '#38bdf8', border: '1px solid rgba(56,189,248,.2)', padding: '5px 12px', borderRadius: '8px', cursor: 'pointer', fontSize: '.82rem', fontWeight: 600, transition: 'all .15s' },

  heroBanner:  { display: 'flex', alignItems: 'center', gap: '24px', background: 'rgba(15,23,42,.9)', border: '1px solid rgba(255,255,255,.09)', borderRadius: '20px', padding: '24px 28px', marginBottom: '20px', flexWrap: 'wrap' },
  avatar:      { width: '72px', height: '72px', borderRadius: '20px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.5rem', fontWeight: 800, color: '#fff', flexShrink: 0, position: 'relative', letterSpacing: '.05em', boxShadow: '0 8px 24px rgba(0,0,0,.4)' },
  avatarBadge: { position: 'absolute', bottom: '-6px', right: '-6px', width: '22px', height: '22px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '.65rem', fontWeight: 800, color: '#fff', border: '2px solid #07111f' },
  heroId:      { margin: 0, fontSize: '1.6rem', fontWeight: 800, color: '#f8fafc', fontFamily: "'Outfit',sans-serif" },
  heroBadge:   { padding: '4px 12px', borderRadius: '20px', fontSize: '.8rem', fontWeight: 700 },
  churnFlag:   { padding: '4px 12px', borderRadius: '20px', background: 'rgba(239,68,68,.15)', color: '#fca5a5', fontSize: '.8rem', fontWeight: 700, border: '1px solid rgba(239,68,68,.3)' },
  stableFlag:  { padding: '4px 12px', borderRadius: '20px', background: 'rgba(16,185,129,.15)', color: '#a7f3d0', fontSize: '.8rem', fontWeight: 700, border: '1px solid rgba(16,185,129,.3)' },
  heroMeta:    { margin: '6px 0 0', color: '#64748b', fontSize: '.88rem', lineHeight: 1.5 },

  kpiStrip: { display: 'flex', gap: '12px', marginBottom: '24px', flexWrap: 'wrap' },

  mainGrid: { display: 'grid', gridTemplateColumns: '1.1fr 1.6fr', gap: '20px', alignItems: 'start' },
  leftCol:  { display: 'flex', flexDirection: 'column', gap: '16px' },
  rightCol: { display: 'flex', flexDirection: 'column', gap: '16px' },

  card:      { background: 'rgba(17,24,39,.82)', border: '1px solid rgba(255,255,255,.08)', borderRadius: '18px', padding: '22px 24px', boxShadow: '0 10px 32px rgba(0,0,0,.22)' },
  cardTitle: { marginTop: 0, marginBottom: '16px', color: '#e2e8f0', fontSize: '1.05rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '10px', borderBottom: '1px solid rgba(255,255,255,.08)', paddingBottom: '10px' },
  titleDot:  { width: '8px', height: '8px', borderRadius: '50%', background: '#6366f1', flexShrink: 0 },

  profileRow:   { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '9px 0', borderBottom: '1px solid rgba(255,255,255,.05)', fontSize: '.88rem' },
  profileLabel: { color: '#64748b', fontWeight: 500 },
  profileValue: { color: '#e2e8f0', fontWeight: 600, textAlign: 'right' },

  helperText: { color: '#64748b', fontSize: '.82rem', marginBottom: '14px', lineHeight: 1.5, marginTop: '-8px' },

  predictBtn:        { width: '100%', marginTop: '20px', padding: '14px', fontSize: '.95rem', background: 'linear-gradient(135deg,#059669,#10b981)', color: '#fff', border: 'none', borderRadius: '12px', fontWeight: 700, cursor: 'pointer', transition: 'all .22s', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', boxShadow: '0 4px 14px rgba(16,185,129,.25)' },
  predictBtnDisabled:{ width: '100%', marginTop: '20px', padding: '14px', fontSize: '.95rem', background: 'rgba(16,185,129,.15)', color: '#10b981', border: 'none', borderRadius: '12px', fontWeight: 700, cursor: 'not-allowed', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' },
  btnSpinner:        { width: '16px', height: '16px', border: '2px solid rgba(16,185,129,.3)', borderTop: '2px solid #10b981', borderRadius: '50%', animation: 'spin 0.8s linear infinite', flexShrink: 0 },

  recommendCard: { background: 'rgba(17,24,39,.85)', border: '1px solid rgba(255,255,255,.09)', borderRadius: '18px', padding: '22px 24px', boxShadow: '0 10px 32px rgba(0,0,0,.22)' },
};
