// frontend/src/pages/CustomerProfile.js
import React, { useState, useEffect } from 'react';

export default function CustomerProfile() {
  const [customerId, setCustomerId] = useState('C10239'); // Default ID to start with
  const [searchId, setSearchId] = useState('C10239');
  const [customer, setCustomer] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Backend API Base URL
  const API_BASE_URL = 'http://localhost:8000/api/v1';

  // 1. Fetch Customer Profile details
  const fetchCustomerDetails = async (id) => {
    setLoading(true);
    setError(null);
    setPrediction(null);
    try {
      const response = await fetch(`${API_BASE_URL}/customers/${id}`);
      if (!response.ok) {
        throw new Error('Customer not found in the database.');
      }
      const data = await response.json();
      setCustomer(data);
      fetchPredictionHistory(id);
    } catch (err) {
      setError(err.message);
      setCustomer(null);
    } finally {
      setLoading(false);
    }
  };

  // 2. Trigger the Churn Prediction Model
  const runChurnPrediction = async () => {
    if (!customer) return;
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/predict/${customerId}`, {
        method: 'POST',
      });
      const data = await response.json();
      setPrediction(data);
      // Refresh history after running a new prediction
      fetchPredictionHistory(customerId);
    } catch (err) {
      setError('Failed to run churn prediction model.');
    } finally {
      setLoading(false);
    }
  };

  // 3. Fetch past Prediction History
  const fetchPredictionHistory = async (id) => {
    try {
      const response = await fetch(`${API_BASE_URL}/predictions/history/${id}`);
      const data = await response.json();
      setHistory(data.history || []);
    } catch (err) {
      console.error('Failed to load prediction history', err);
    }
  };

  useEffect(() => {
    fetchCustomerDetails(customerId);
  }, [customerId]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setCustomerId(searchId);
  };

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>Customer Profile & Churn Insights</h1>

      {/* Search Bar */}
      <form onSubmit={handleSearchSubmit} style={styles.searchForm}>
        <input
          type="text"
          placeholder="Enter Customer ID (e.g., C10239)"
          value={searchId}
          onChange={(e) => setSearchId(e.target.value)}
          style={styles.searchInput}
        />
        <button type="submit" style={styles.searchButton}>Load Profile</button>
      </form>

      {loading && <p style={styles.infoText}>Processing data...</p>}
      {error && <p style={styles.errorText}>{error}</p>}

      {customer && (
        <div style={styles.dashboardGrid}>
          
          {/* Left Column: Demographics & Usage */}
          <div style={styles.card}>
            <h2 style={styles.cardTitle}>Core Customer Profile</h2>
            <div style={styles.profileRow}><strong>Customer ID:</strong> {customer.customer_id}</div>
            <div style={styles.profileRow}><strong>Age:</strong> {customer.age}</div>
            <div style={styles.profileRow}><strong>Income Level:</strong> {customer.income_level}</div>
            <div style={styles.profileRow}><strong>Device Preferred:</strong> {customer.device_type}</div>
            <div style={styles.profileRow}><strong>Payment Mode:</strong> {customer.payment_mode}</div>
            
            <h2 style={styles.cardTitleDivider}>Subscription & Usage</h2>
            <div style={styles.profileRow}><strong>Subscriptions:</strong> {customer.number_of_subscriptions} active</div>
            <div style={styles.profileRow}><strong>Tenure:</strong> {customer.tenure_months} months</div>
            <div style={styles.profileRow}><strong>Monthly Spend:</strong> ${customer.monthly_total_spend}</div>
            <div style={styles.profileRow}><strong>Avg Weekly Usage:</strong> {customer.avg_usage_hours_per_week} hours</div>
            <div style={styles.profileRow}><strong>App Switch Frequency:</strong> {customer.app_switch_frequency} times/hr</div>
            <div style={styles.profileRow}><strong>Support Interactions:</strong> {customer.customer_support_interactions}</div>
            <div style={styles.profileRow}><strong>Satisfaction Score:</strong> {customer.satisfaction_score}/5</div>
            <div style={styles.profileRow}><strong>Discount Applied:</strong> {customer.discount_used ? 'Yes' : 'No'}</div>
            
            <button onClick={runChurnPrediction} style={styles.predictButton}>
              Generate Churn Prediction
            </button>
          </div>

          {/* Right Column: Prediction Engine Output */}
          <div style={styles.rightCol}>
            
            {/* Churn Output Card */}
            <div style={styles.card}>
              <h2 style={styles.cardTitle}>ML Prediction Output</h2>
              {prediction ? (
                <div>
                  <div style={styles.predictionBox(prediction.prediction)}>
                    {prediction.prediction === 1 ? 'LIKELY TO CANCEL' : 'NOT LIKELY TO CANCEL'}
                  </div>
                  <div style={styles.metricRow}>
                    <span>Churn Probability:</span>
                    <strong style={{ fontSize: '1.25rem' }}>{prediction.risk_score}%</strong>
                  </div>
                  <div style={styles.metricRow}>
                    <span>Risk Category:</span>
                    <strong style={styles.riskBadge(prediction.risk_category)}>{prediction.risk_category}</strong>
                  </div>
                </div>
              ) : (
                <p style={styles.placeholderText}>Click 'Generate Churn Prediction' on the left panel to run calculations.</p>
              )}
            </div>

            {/* Explainable AI / SHAP Factors Card */}
            {prediction && (
              <div style={styles.card}>
                <h2 style={styles.cardTitle}>Explainable AI (Local Model Factors)</h2>
                <p style={{ fontSize: '0.9rem', color: '#666', marginBottom: '10px' }}>
                  Top factors contributing to this prediction:
                </p>
                <ul style={styles.reasonList}>
                  {prediction.reasons.map((reason, idx) => (
                    <li key={idx} style={styles.reasonItem}>• {reason}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Retention Recommendations Card */}
            {prediction && prediction.prediction === 1 && (
              <div style={styles.recommendationCard}>
                <h2 style={styles.recommendationTitle}>Retention Recommendation Engine</h2>
                <div style={styles.recommendationBox}>
                  <strong>Action Recommended:</strong>
                  <p style={{ marginTop: '5px' }}>
                    {customer.monthly_total_spend > 100 
                      ? 'High subscription spending detected. Recommend sending a 15% discount code on renewal.'
                      : 'Low engagement and satisfaction detected. Recommend routing to VIP support desk for immediate call outreach.'}
                  </p>
                </div>
              </div>
            )}

            {/* Prediction Log History */}
            <div style={styles.card}>
              <h2 style={styles.cardTitle}>Prediction History log</h2>
              {history.length > 0 ? (
                <ul style={styles.historyList}>
                  {history.map((log) => (
                    <li key={log.history_id} style={styles.historyItem}>
                      <span>Run #{log.history_id}:</span> 
                      <strong>{log.risk_score}% Risk</strong> ({log.risk_category})
                    </li>
                  ))}
                </ul>
              ) : (
                <p style={styles.placeholderText}>No previous historical logs recorded for this customer.</p>
              )}
            </div>

          </div>
        </div>
      )}
    </div>
  );
}

// Simple Inline CSS Object to styled component layout automatically
const styles = {
  container: { padding: '24px', fontFamily: 'Arial, sans-serif', maxWidth: '1200px', margin: '0 auto', backgroundColor: '#f9f9f9', minHeight: '100vh' },
  title: { fontSize: '2rem', fontWeight: 'bold', color: '#333', marginBottom: '20px' },
  searchForm: { display: 'flex', gap: '10px', marginBottom: '24px' },
  searchInput: { padding: '10px', fontSize: '1rem', border: '1px solid #ccc', borderRadius: '4px', flex: '1', maxWidth: '300px' },
  searchButton: { padding: '10px 20px', fontSize: '1rem', backgroundColor: '#007bff', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' },
  dashboardGrid: { display: 'grid', gridTemplateColumns: '1fr 1.2fr', gap: '24px' },
  card: { backgroundColor: '#fff', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)', marginBottom: '16px' },
  cardTitle: { fontSize: '1.2rem', fontWeight: 'bold', color: '#2c3e50', borderBottom: '2px solid #ecf0f1', paddingBottom: '8px', marginBottom: '12px' },
  cardTitleDivider: { fontSize: '1.2rem', fontWeight: 'bold', color: '#2c3e50', borderBottom: '2px solid #ecf0f1', paddingBottom: '8px', margin: '20px 0 12px 0' },
  profileRow: { display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #f9f9f9', fontSize: '0.95rem' },
  predictButton: { width: '100%', marginTop: '20px', padding: '12px', fontSize: '1rem', backgroundColor: '#28a745', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' },
  rightCol: { display: 'flex', flexDirection: 'column' },
  predictionBox: (isChurn) => ({
    padding: '16px',
    borderRadius: '4px',
    textAlign: 'center',
    fontWeight: 'bold',
    fontSize: '1.2rem',
    marginBottom: '16px',
    backgroundColor: isChurn === 1 ? '#f8d7da' : '#d4edda',
    color: isChurn === 1 ? '#721c24' : '#155724',
    border: isChurn === 1 ? '1px solid #f5c6cb' : '1px solid #c3e6cb'
  }),
  metricRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '10px 0' },
  riskBadge: (category) => ({
    padding: '4px 8px',
    borderRadius: '4px',
    color: '#fff',
    backgroundColor: category === 'CRITICAL' || category === 'HIGH' ? '#dc3545' : category === 'MEDIUM' ? '#ffc107' : '#28a745'
  }),
  reasonList: { listStyle: 'none', padding: 0, margin: 0 },
  reasonItem: { padding: '8px 0', color: '#2c3e50', borderBottom: '1px solid #f5f5f5' },
  recommendationCard: { backgroundColor: '#fff3cd', padding: '20px', borderRadius: '8px', borderLeft: '5px solid #ffc107', marginBottom: '16px' },
  recommendationTitle: { fontSize: '1.2rem', fontWeight: 'bold', color: '#856404', marginBottom: '10px' },
  recommendationBox: { color: '#856404' },
  historyList: { listStyle: 'none', padding: 0, margin: 0 },
  historyItem: { display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #f1f1f1', fontSize: '0.9rem' },
  placeholderText: { color: '#888', fontStyle: 'italic', textAlign: 'center', margin: '20px 0' },
  infoText: { color: '#007bff', fontWeight: 'bold' },
  errorText: { color: '#dc3545', fontWeight: 'bold', marginBottom: '16px' }
};