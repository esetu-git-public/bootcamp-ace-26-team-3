import React, { useEffect, useMemo, useState } from 'react';

const API_BASE_URL = 'http://localhost:8000/api/v1';

function AnalyticsDashboard() {
  const [kpis, setKpis] = useState(null);
  const [riskDistribution, setRiskDistribution] = useState([]);
  const [incomeData, setIncomeData] = useState([]);
  const [deviceData, setDeviceData] = useState([]);
  const [customerRows, setCustomerRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    const headers = token ? { Authorization: `Bearer ${token}` } : {};

    Promise.all([
      fetch(`${API_BASE_URL}/dashboard/kpis`, { headers }),
      fetch(`${API_BASE_URL}/analytics/churn-risk-distribution`, { headers }),
      fetch(`${API_BASE_URL}/analytics/churn-by-income`, { headers }),
      fetch(`${API_BASE_URL}/analytics/churn-by-device`, { headers }),
      fetch(`${API_BASE_URL}/customers?page=1&limit=6`, { headers }),
    ])
      .then(async (responses) => {
        const [kpisRes, riskRes, incomeRes, deviceRes, customersRes] = responses;
        const kpisData = await kpisRes.json();
        const riskData = await riskRes.json();
        const incomeDataResult = await incomeRes.json();
        const deviceDataResult = await deviceRes.json();
        const customersData = await customersRes.json();

        if (!kpisRes.ok || !riskRes.ok || !incomeRes.ok || !deviceRes.ok || !customersRes.ok) {
          throw new Error('Unable to load analytics data right now.');
        }

        setKpis(kpisData);
        setRiskDistribution(riskData);
        setIncomeData(incomeDataResult);
        setDeviceData(deviceDataResult);
        setCustomerRows(customersData.results || []);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const totalRisk = useMemo(() => {
    if (!riskDistribution.length) return 0;
    return riskDistribution.reduce((sum, item) => sum + item.customer_count, 0);
  }, [riskDistribution]);

  if (loading) {
    return <div style={styles.center}>Loading analytics dashboard…</div>;
  }

  if (error) {
    return <div style={styles.center}>{error}</div>;
  }

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <div>
          <p style={styles.eyebrow}>Subscription Churn Intelligence</p>
          <h1 style={styles.title}>Executive analytics dashboard</h1>
        </div>
        <div style={styles.headerCard}>
          <strong>{kpis?.total_customers?.toLocaleString() || '0'}</strong>
          <span>customers monitored</span>
        </div>
      </header>

      <section style={styles.grid}>
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>KPI snapshot</h3>
          <div style={styles.metricGrid}>
            <MetricCard label="Predicted churn" value={kpis?.predicted_churn_customers || 0} tone="warn" />
            <MetricCard label="High risk" value={kpis?.high_risk_customers || 0} tone="danger" />
            <MetricCard label="Avg churn risk" value={`${kpis?.average_churn_risk || 0}%`} tone="accent" />
            <MetricCard label="Revenue at risk" value={`$${(kpis?.monthly_revenue_at_risk || 0).toLocaleString()}`} tone="success" />
          </div>
        </div>

        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Risk distribution</h3>
          <div style={styles.listGroup}>
            {riskDistribution.map((item) => (
              <div key={item.risk_category} style={styles.listRow}>
                <span>{item.risk_category}</span>
                <strong>{item.customer_count}</strong>
              </div>
            ))}
          </div>
          <p style={styles.helperText}>Across {totalRisk} customers in the active view</p>
        </div>
      </section>

      <section style={styles.grid}>
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Income vs churn</h3>
          {incomeData.map((item) => (
            <div key={item.income_level} style={styles.barRow}>
              <div style={{ flex: 1 }}>
                <div style={styles.barLabelRow}>
                  <span>{item.income_level}</span>
                  <span>{item.churn_rate}%</span>
                </div>
                <div style={styles.barTrack}>
                  <div style={{ ...styles.barFill, width: `${Math.min(item.churn_rate * 2.2, 100)}%` }} />
                </div>
              </div>
            </div>
          ))}
        </div>

        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Device split</h3>
          {deviceData.map((item) => (
            <div key={item.device_type} style={styles.barRow}>
              <div style={{ flex: 1 }}>
                <div style={styles.barLabelRow}>
                  <span>{item.device_type}</span>
                  <span>{item.churn_rate}%</span>
                </div>
                <div style={styles.barTrack}>
                  <div style={{ ...styles.barFill, width: `${Math.min(item.churn_rate * 2.2, 100)}%` }} />
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section style={styles.card}>
        <h3 style={styles.cardTitle}>High-risk customer queue</h3>
        <div style={styles.tableWrap}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Customer</th>
                <th style={styles.th}>Risk</th>
                <th style={styles.th}>Spend</th>
                <th style={styles.th}>Tenure</th>
              </tr>
            </thead>
            <tbody>
              {customerRows.map((row) => (
                <tr key={row.customer_id}>
                  <td style={styles.td}>{row.customer_id}</td>
                  <td style={styles.td}>{row.risk_category || 'Pending'}</td>
                  <td style={styles.td}>${Number(row.monthly_total_spend || 0).toFixed(2)}</td>
                  <td style={styles.td}>{row.tenure_months} months</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function MetricCard({ label, value, tone }) {
  const colors = {
    warn: '#f59e0b',
    danger: '#ef4444',
    accent: '#6366f1',
    success: '#10b981',
  };

  return (
    <div style={{ ...styles.metricCard, borderColor: colors[tone] || colors.accent }}>
      <span style={styles.metricLabel}>{label}</span>
      <strong style={styles.metricValue}>{value}</strong>
    </div>
  );
}

const styles = {
  page: { minHeight: '100vh', background: '#07111f', color: '#f7f8fc', padding: '24px', fontFamily: 'Inter, Arial, sans-serif' },
  center: { minHeight: '100vh', display: 'flex', justifyContent: 'center', alignItems: 'center', background: '#07111f', color: '#f7f8fc' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' },
  eyebrow: { textTransform: 'uppercase', letterSpacing: '0.18em', color: '#7dd3fc', fontSize: '0.75rem', margin: 0 },
  title: { margin: '4px 0 0', fontSize: '2rem' },
  headerCard: { background: 'rgba(17,24,39,0.8)', border: '1px solid rgba(255,255,255,0.08)', padding: '14px 18px', borderRadius: '12px', display: 'flex', flexDirection: 'column', minWidth: '180px' },
  grid: { display: 'grid', gap: '16px', gridTemplateColumns: '2fr 1fr', marginBottom: '16px' },
  card: { background: 'rgba(17,24,39,0.8)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '16px', padding: '18px', boxShadow: '0 12px 34px rgba(0,0,0,0.25)' },
  cardTitle: { marginTop: 0, marginBottom: '12px' },
  metricGrid: { display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '12px' },
  metricCard: { border: '1px solid', borderRadius: '12px', padding: '14px', background: 'rgba(255,255,255,0.03)' },
  metricLabel: { display: 'block', color: '#cbd5e1', fontSize: '0.9rem', marginBottom: '6px' },
  metricValue: { fontSize: '1.2rem' },
  listGroup: { display: 'flex', flexDirection: 'column', gap: '8px' },
  listRow: { display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,0.08)' },
  helperText: { color: '#94a3b8', fontSize: '0.85rem', marginTop: '8px' },
  barRow: { marginBottom: '10px' },
  barLabelRow: { display: 'flex', justifyContent: 'space-between', marginBottom: '6px', color: '#cbd5e1' },
  barTrack: { height: '8px', width: '100%', background: 'rgba(255,255,255,0.08)', borderRadius: '999px', overflow: 'hidden' },
  barFill: { height: '100%', background: 'linear-gradient(90deg, #6366f1, #22d3ee)', borderRadius: '999px' },
  tableWrap: { overflowX: 'auto' },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { textAlign: 'left', padding: '10px 8px', color: '#94a3b8', borderBottom: '1px solid rgba(255,255,255,0.08)' },
  td: { padding: '10px 8px', borderBottom: '1px solid rgba(255,255,255,0.06)' },
};

export default AnalyticsDashboard;