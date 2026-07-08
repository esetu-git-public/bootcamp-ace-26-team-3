import React, { useState, useEffect } from 'react';
import * as apiService from '../services/api';
import * as mlModel from '../services/mlModel';
import { ModelPredictionCard, RiskGauge, PredictionTimeline } from '../components/ModelPredictionCard';

export default function CustomerProfile({ onViewChange, onLogout, onNotify, selectedCustomerId, setSelectedCustomerId }) {
  const [customerId, setCustomerId] = useState(selectedCustomerId || 'C10239');
  const [searchId, setSearchId] = useState(selectedCustomerId || 'C10239');
  const [customer, setCustomer] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [predicting, setPredicting] = useState(false);

  const fetchCustomerDetails = async (id) => {
    setLoading(true);
    setError(null);
    setPrediction(null);
    try {
      const data = await apiService.getCustomerProfile(id);
      setCustomer(data);
      
      // If customer has a prediction in the view result, set it
      if (data.churn_probability !== null) {
        setPrediction({
          will_cancel: data.will_cancel,
          churn_probability: data.churn_probability,
          probability_confidence_lower: data.probability_confidence_lower,
          probability_confidence_upper: data.probability_confidence_upper,
          risk_category: data.risk_category,
          explainability: data.explainability,
          recommendation_type: data.recommendation_type,
          recommendation_desc: data.recommendation_desc
        });
      }
      
      fetchPredictionHistory(id);
    } catch (err) {
      if (err.status === 401) {
        onLogout({ silent: true });
      } else {
        setError(err.message || 'Failed to load customer details');
      }
      setCustomer(null);
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
      fetchPredictionHistory(customerId);
      if (onNotify) {
        onNotify({
          type: 'success',
          title: 'Prediction ready',
          message: `Churn prediction updated for ${customerId}.`
        });
      }
    } catch (err) {
      if (err.status === 401) {
        onLogout({ silent: true });
      } else {
        setError(err.message || 'Failed to run churn prediction model.');
      }
    } finally {
      setPredicting(false);
    }
  };

  const fetchPredictionHistory = async (id) => {
    try {
      const data = await mlModel.getPredictionHistory(id);
      setHistory(data || []);
    } catch (err) {
      if (err.status !== 401) {
        console.error('Failed to load prediction history', err);
      }
    }
  };

  useEffect(() => {
    if (selectedCustomerId) {
      setCustomerId(selectedCustomerId);
      setSearchId(selectedCustomerId);
      fetchCustomerDetails(selectedCustomerId);
    }
  }, [selectedCustomerId]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (searchId.trim()) {
      setCustomerId(searchId);
      if (setSelectedCustomerId) {
        setSelectedCustomerId(searchId);
      } else {
        fetchCustomerDetails(searchId);
      }
    }
  };

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <div>
          <p style={styles.eyebrow}>Deep Diagnostics & Explainability</p>
          <h1 style={styles.title}>Customer Profile Explorer</h1>
          <p style={styles.subtitle}>Detailed behavioral audit, feature importances, and historical model logs for individual customer profiles.</p>
        </div>
      </header>

      {/* Search Input */}
      <form onSubmit={handleSearchSubmit} style={styles.searchForm}>
        <input
          type="text"
          placeholder="Search Customer ID (e.g., C10239)"
          value={searchId}
          onChange={(e) => setSearchId(e.target.value)}
          style={styles.searchInput}
        />
        <button type="submit" style={styles.searchButton}>Search Profile</button>
      </form>

      {loading && <div style={styles.loader}>Accessing database registry…</div>}
      {error && <div style={styles.errorBanner}>{error}</div>}

      {!loading && customer && (
        <div style={styles.mainLayout}>
          {/* Left Column: Demographics and Subscription Profile */}
          <div style={styles.card}>
            <h3 style={styles.cardTitle}>Core Customer Profile</h3>
            <div style={styles.profileGrid}>
              <div style={styles.profileRow}><span>Customer ID:</span> <strong>{customer.customer_id}</strong></div>
              <div style={styles.profileRow}><span>Age:</span> <span>{customer.age} years old</span></div>
              <div style={styles.profileRow}><span>Income Level:</span> <span>{customer.income_level}</span></div>
              <div style={styles.profileRow}><span>Device Preference:</span> <span>{customer.device_type}</span></div>
              <div style={styles.profileRow}><span>Payment Mode:</span> <span>{customer.payment_mode}</span></div>
            </div>

            <h3 style={{ ...styles.cardTitle, marginTop: '24px' }}>Subscription & Activity Metrics</h3>
            <div style={styles.profileGrid}>
              <div style={styles.profileRow}><span>Active Subscriptions:</span> <span>{customer.number_of_subscriptions}</span></div>
              <div style={styles.profileRow}><span>Tenure Duration:</span> <span>{customer.tenure_months} months</span></div>
              <div style={styles.profileRow}><span>Monthly Total Spend:</span> <span>${Number(customer.monthly_total_spend).toFixed(2)}</span></div>
              <div style={styles.profileRow}><span>Avg Weekly Usage:</span> <span>{customer.avg_usage_hours_per_week} hours</span></div>
              <div style={styles.profileRow}><span>App Switch Rate:</span> <span>{customer.app_switch_frequency}/hr</span></div>
              <div style={styles.profileRow}><span>Support Tickets:</span> <span>{customer.customer_support_interactions}</span></div>
              <div style={styles.profileRow}><span>Satisfaction Rating:</span> <span>{customer.satisfaction_score}/10</span></div>
              <div style={styles.profileRow}><span>Discounts Claimed:</span> <span>{customer.discount_used ? 'Yes' : 'No'}</span></div>
            </div>

            <button
              onClick={runChurnPrediction}
              disabled={predicting}
              style={predicting ? styles.predictBtnDisabled : styles.predictBtn}
            >
              {predicting ? 'Calculating Churn Model…' : 'Generate Model Prediction'}
            </button>
          </div>

          {/* Right Column: Model Output and Local SHAP Explainability */}
          <div style={styles.rightCol}>
            {/* Model Prediction Card with SHAP Explainability */}
            <ModelPredictionCard
              prediction={prediction}
              loading={predicting}
              error={error}
              onRegenerate={runChurnPrediction}
            />

            {/* Prediction History Timeline */}
            <PredictionTimeline predictions={history} />

            {/* Explainable AI / Local SHAP Indicators */}
            {prediction && prediction.explainability && (
              <div style={styles.card}>
                <h3 style={styles.cardTitle}>Local Model Explainability (SHAP Factors)</h3>
                <p style={styles.helperText}>Calculated weights indicating how features influenced the model risk score upward (red) or downward (green):</p>
                <div style={styles.factorList}>
                  {Object.entries(prediction.explainability).map(([key, val]) => {
                    const isIncrease = val > 0;
                    return (
                      <div key={key} style={styles.factorRow}>
                        <span style={styles.factorName}>{key.replace(/_/g, ' ')}</span>
                        <div style={styles.factorProgressTrack}>
                          <div style={styles.factorProgressBar(val, isIncrease)} />
                        </div>
                        <span style={styles.factorValue(isIncrease)}>
                          {isIncrease ? '+' : ''}{val.toFixed(2)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Recommendation Card */}
            {prediction && (
              <div style={styles.recommendationCard(prediction.will_cancel)}>
                <h4 style={styles.recommendationTitle(prediction.will_cancel)}>
                  Retention Action Recommendation
                </h4>
                <p style={styles.recommendationHeading}>
                  <strong>Action:</strong> {prediction.recommendation_type}
                </p>
                <p style={styles.recommendationDesc}>
                  {prediction.recommendation_desc}
                </p>
              </div>
            )}

            {/* Prediction History Logs */}
            <div style={styles.card}>
              <h3 style={styles.cardTitle}>Model Audit Log (Prediction History)</h3>
              {history.length > 0 ? (
                <div style={styles.historyList}>
                  {history.map((log) => (
                    <div key={log.history_id} style={styles.historyRow}>
                      <span style={styles.historyTime}>
                        {new Date(log.evaluated_at).toLocaleString()}
                      </span>
                      <span style={styles.historyBadge(log.prediction_result)}>
                        {log.prediction_result === 1 ? 'Churn' : 'Retain'}
                      </span>
                      <strong style={styles.historyScore}>
                        {log.risk_score.toFixed(1)}% Risk
                      </strong>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={styles.placeholderText}>No historical prediction runs recorded for this profile.</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const styles = {
  page: { minHeight: '100vh', background: '#07111f', color: '#f7f8fc', padding: '24px', fontFamily: 'Inter, Arial, sans-serif' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' },
  eyebrow: { textTransform: 'uppercase', letterSpacing: '0.18em', color: '#7dd3fc', fontSize: '0.75rem', margin: 0 },
  title: { margin: '4px 0 8px', fontSize: '2rem' },
  subtitle: { margin: 0, color: '#94a3b8', maxWidth: '620px', lineHeight: 1.7 },
  searchForm: { display: 'flex', gap: '12px', marginBottom: '24px', maxWidth: '500px' },
  searchInput: { background: 'rgba(17,24,39,0.85)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '10px', padding: '12px 16px', color: '#f7f8fc', outline: 'none', fontSize: '0.95rem', flex: 1 },
  searchButton: { background: '#6366f1', color: '#ffffff', border: 'none', borderRadius: '10px', padding: '0 20px', fontWeight: 600, cursor: 'pointer', transition: 'all 0.2s' },
  loader: { padding: '40px 0', textAlign: 'center', color: '#38bdf8', fontStyle: 'italic' },
  errorBanner: { background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)', padding: '12px 16px', borderRadius: '10px', color: '#fca5a5', marginBottom: '24px' },
  mainLayout: { display: 'grid', gridTemplateColumns: '1.2fr 1.8fr', gap: '24px', alignItems: 'start' },
  card: { background: 'rgba(17,24,39,0.8)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '16px', padding: '24px', marginBottom: '16px', boxShadow: '0 12px 34px rgba(0,0,0,0.25)' },
  cardTitle: { marginTop: 0, marginBottom: '16px', color: '#e2e8f0', fontSize: '1.15rem', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '8px' },
  profileGrid: { display: 'flex', flexDirection: 'column', gap: '10px' },
  profileRow: { display: 'flex', justifyContent: 'space-between', padding: '4px 0', fontSize: '0.9rem', color: '#cbd5e1' },
  predictBtn: { width: '100%', marginTop: '24px', padding: '14px', fontSize: '0.95rem', background: '#10b981', color: '#07111f', border: 'none', borderRadius: '10px', fontWeight: 700, cursor: 'pointer', transition: 'all 0.2s' },
  predictBtnDisabled: { width: '100%', marginTop: '24px', padding: '14px', fontSize: '0.95rem', background: 'rgba(16,185,129,0.2)', color: '#10b981', border: 'none', borderRadius: '10px', fontWeight: 700, cursor: 'not-allowed' },
  rightCol: { display: 'flex', flexDirection: 'column' },
  predictionBox: (willCancel) => {
    const isChurn = willCancel === 1;
    const bg = isChurn ? 'rgba(239,68,68,0.08)' : 'rgba(16,185,129,0.08)';
    const text = isChurn ? '#fca5a5' : '#a7f3d0';
    const border = isChurn ? 'rgba(239,68,68,0.2)' : 'rgba(16,185,129,0.2)';
    return {
      padding: '16px',
      borderRadius: '10px',
      textAlign: 'center',
      fontWeight: 700,
      fontSize: '1.1rem',
      backgroundColor: bg,
      color: text,
      border: `1px solid ${border}`,
      marginBottom: '16px'
    };
  },
  metricRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '12px 0', color: '#94a3b8', fontSize: '0.95rem' },
  riskBadge: (category) => {
    const isHigh = category === 'High' || category === 'CRITICAL';
    const isMedium = category === 'Medium';
    const bg = isHigh ? '#dc3545' : isMedium ? '#ffc107' : '#10b981';
    return {
      padding: '4px 10px',
      borderRadius: '6px',
      color: '#0f172a',
      backgroundColor: bg,
      fontWeight: 700,
      fontSize: '0.85rem'
    };
  },
  placeholderText: { color: '#94a3b8', fontStyle: 'italic', textAlign: 'center', padding: '20px 0' },
  helperText: { color: '#94a3b8', fontSize: '0.85rem', marginBottom: '14px', lineHeight: 1.5 },
  factorList: { display: 'flex', flexDirection: 'column', gap: '12px' },
  factorRow: { display: 'flex', alignItems: 'center', gap: '12px', fontSize: '0.85rem' },
  factorName: { width: '160px', color: '#cbd5e1', textTransform: 'capitalize' },
  factorProgressTrack: { flex: 1, background: 'rgba(255,255,255,0.06)', height: '8px', borderRadius: '4px', overflow: 'hidden', position: 'relative' },
  factorProgressBar: (val, isIncrease) => {
    // scale SHAP value width (max at around 2.0 SHAP strength)
    const maxVal = 2.0;
    const widthPct = Math.min(100, Math.round((Math.abs(val) / maxVal) * 100));
    return {
      width: `${widthPct}%`,
      height: '100%',
      background: isIncrease ? 'linear-gradient(90deg, #f87171, #ef4444)' : 'linear-gradient(90deg, #34d399, #10b981)',
      borderRadius: '4px',
      float: isIncrease ? 'left' : 'right'
    };
  },
  factorValue: (isIncrease) => ({
    width: '45px',
    textAlign: 'right',
    fontWeight: 600,
    color: isIncrease ? '#f87171' : '#34d399'
  }),
  recommendationCard: (willCancel) => {
    const isChurn = willCancel === 1;
    const bg = isChurn ? 'rgba(245,158,11,0.06)' : 'rgba(99,102,241,0.06)';
    const border = isChurn ? '#ffc107' : '#6366f1';
    return {
      background: bg,
      padding: '20px',
      borderRadius: '16px',
      borderLeft: `5px solid ${border}`,
      marginBottom: '16px',
      borderTop: '1px solid rgba(255,255,255,0.04)',
      borderRight: '1px solid rgba(255,255,255,0.04)',
      borderBottom: '1px solid rgba(255,255,255,0.04)',
      boxShadow: '0 8px 24px rgba(0,0,0,0.15)'
    };
  },
  recommendationTitle: (willCancel) => ({
    margin: 0,
    fontSize: '1.05rem',
    fontWeight: 700,
    color: willCancel === 1 ? '#fde047' : '#818cf8',
    marginBottom: '12px'
  }),
  recommendationHeading: { margin: 0, color: '#e2e8f0', fontSize: '0.9rem', marginBottom: '6px' },
  recommendationDesc: { margin: 0, color: '#cbd5e1', fontSize: '0.9rem', lineHeight: 1.6 },
  historyList: { display: 'flex', flexDirection: 'column', gap: '8px' },
  historyRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: '0.85rem' },
  historyTime: { color: '#cbd5e1' },
  historyBadge: (predictionResult) => {
    const isChurn = predictionResult === 1;
    return {
      padding: '2px 8px',
      borderRadius: '4px',
      fontSize: '0.75rem',
      fontWeight: 600,
      backgroundColor: isChurn ? 'rgba(239,68,68,0.1)' : 'rgba(16,185,129,0.1)',
      color: isChurn ? '#fca5a5' : '#a7f3d0',
      border: `1px solid ${isChurn ? 'rgba(239,68,68,0.2)' : 'rgba(16,185,129,0.2)'}`
    };
  },
  historyScore: { color: '#e2e8f0' }
};
