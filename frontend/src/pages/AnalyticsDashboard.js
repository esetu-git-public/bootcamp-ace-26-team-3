import React, { useEffect, useMemo, useState } from 'react';

const API_BASE_URL = 'http://localhost:8000/api/v1';

function AnalyticsDashboard({ onViewChange, onLogout }) {
  const [kpis, setKpis] = useState(null);
  const [riskDistribution, setRiskDistribution] = useState([]);
  const [incomeData, setIncomeData] = useState([]);
  const [deviceData, setDeviceData] = useState([]);
  const [segmentData, setSegmentData] = useState([]);
  const [customerRows, setCustomerRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [bulkFile, setBulkFile] = useState(null);
  const [bulkUploading, setBulkUploading] = useState(false);
  const [bulkError, setBulkError] = useState('');
  const [bulkJob, setBulkJob] = useState(null);
  const [bulkPreview, setBulkPreview] = useState([]);
  const backendOrigin = API_BASE_URL.replace('/api/v1', '');

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    const headers = token ? { Authorization: `Bearer ${token}` } : {};

    Promise.all([
      fetch(`${API_BASE_URL}/dashboard/kpis`, { headers }),
      fetch(`${API_BASE_URL}/analytics/churn-risk-distribution`, { headers }),
      fetch(`${API_BASE_URL}/analytics/churn-by-income`, { headers }),
      fetch(`${API_BASE_URL}/analytics/churn-by-device`, { headers }),
      fetch(`${API_BASE_URL}/analytics/customer-segmentation`, { headers }),
      fetch(`${API_BASE_URL}/customers?page=1&limit=6`, { headers }),
    ])
      .then(async (responses) => {
        const [kpisRes, riskRes, incomeRes, deviceRes, segmentRes, customersRes] = responses;
        const kpisData = await kpisRes.json();
        const riskData = await riskRes.json();
        const incomeDataResult = await incomeRes.json();
        const deviceDataResult = await deviceRes.json();
        const segmentDataResult = await segmentRes.json();
        const customersData = await customersRes.json();

        if (!kpisRes.ok || !riskRes.ok || !incomeRes.ok || !deviceRes.ok || !segmentRes.ok || !customersRes.ok) {
          throw new Error('Unable to load analytics data right now.');
        }

        setKpis(kpisData);
        setRiskDistribution(riskData);
        setIncomeData(incomeDataResult);
        setDeviceData(deviceDataResult);
        setSegmentData(segmentDataResult);
        setCustomerRows(customersData.results || []);
      })
      .catch((err) => setError(err.message || 'Unable to load analytics data.'))
      .finally(() => setLoading(false));
  }, [onLogout]);

  useEffect(() => {
    if (!bulkJob?.job_id || ['COMPLETED', 'FAILED'].includes(bulkJob.status)) {
      return undefined;
    }

    const token = localStorage.getItem('access_token');
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    const timer = window.setInterval(async () => {
      try {
        const statusRes = await fetch(`${API_BASE_URL}/predictions/bulk/status/${bulkJob.job_id}`, { headers });
        const statusData = await statusRes.json();

        if (statusRes.ok) {
          setBulkJob(statusData);
          if (statusData.status === 'COMPLETED') {
            const previewRes = await fetch(`${API_BASE_URL}/predictions/bulk/preview/${bulkJob.job_id}`, { headers });
            if (previewRes.ok) {
              setBulkPreview(await previewRes.json());
            }
          }
        }
      } catch (err) {
        setBulkError('Unable to refresh bulk prediction progress right now.');
      }
    }, 2000);

    return () => window.clearInterval(timer);
  }, [bulkJob?.job_id, bulkJob?.status]);

  const totalRisk = useMemo(() => {
    if (!riskDistribution.length) return 0;
    return riskDistribution.reduce((sum, item) => sum + item.customer_count, 0);
  }, [riskDistribution]);

  const progressPercent = useMemo(() => {
    if (!bulkJob?.total_records || !bulkJob?.processed_records) return 0;
    return Math.min(100, Math.round((bulkJob.processed_records / bulkJob.total_records) * 100));
  }, [bulkJob]);

  const topSegment = useMemo(() => {
    if (!segmentData.length) return null;
    return segmentData.reduce((best, item) => {
      if (!best || item.percentage > best.percentage) return item;
      return best;
    }, null);
  }, [segmentData]);

  const handleBulkUpload = async (event) => {
    event.preventDefault();
    if (!bulkFile) {
      setBulkError('Please select a CSV file before uploading.');
      return;
    }

    setBulkError('');
    setBulkUploading(true);

    try {
      const token = localStorage.getItem('access_token');
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const formData = new FormData();
      formData.append('file', bulkFile);

      const response = await fetch(`${API_BASE_URL}/predictions/bulk`, {
        method: 'POST',
        headers,
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Bulk upload failed.');
      }

      const result = await response.json();
      setBulkJob(result);
      setBulkPreview([]);
    } catch (uploadError) {
      setBulkError(uploadError.message || 'Unable to upload bulk predictions.');
    } finally {
      setBulkUploading(false);
    }
  };

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
          <p style={styles.subtitle}>Monitor churn risk, segment performance, and customer exposure across the subscription base.</p>
        </div>
        <div style={styles.headerCard}>
          <strong>{kpis?.total_customers?.toLocaleString() || '0'}</strong>
          <span>customers monitored</span>
        </div>
      </header>

      <section style={styles.card}>
        <div style={styles.sectionHeader}>
          <div>
            <h3 style={styles.cardTitle}>Bulk prediction studio</h3>
            <p style={styles.helperText}>Upload a CSV of customer records to queue asynchronous churn scoring and inspect a preview of results.</p>
          </div>
        </div>
        <form onSubmit={handleBulkUpload} style={styles.uploadRow}>
          <input
            type="file"
            accept=".csv"
            onChange={(event) => setBulkFile(event.target.files?.[0] || null)}
            style={styles.uploadInput}
          />
          <button type="submit" disabled={bulkUploading} style={styles.primaryButton}>
            {bulkUploading ? 'Uploading…' : 'Run bulk prediction'}
          </button>
        </form>
        <p style={styles.helperText}>Expected columns include customer_id, age, income_level, device_type, payment_mode, number_of_subscriptions, tenure_months, monthly_total_spend, avg_usage_hours_per_week, app_switch_frequency, customer_support_interactions, satisfaction_score, and discount_used.</p>
        {bulkError ? <p style={styles.errorText}>{bulkError}</p> : null}
        {bulkJob ? (
          <div style={styles.jobPanel}>
            <div style={styles.jobHeader}>
              <div>
                <strong>Job {bulkJob.job_id}</strong>
                <p style={styles.helperText}>Status: {bulkJob.status}</p>
              </div>
              {bulkJob.download_url ? (
                <a href={`${backendOrigin}${bulkJob.download_url}`} target="_blank" rel="noreferrer" style={styles.link}>Download CSV</a>
              ) : null}
            </div>
            <div style={styles.progressTrack}>
              <div style={{ ...styles.progressFill, width: `${progressPercent}%` }} />
            </div>
            <p style={styles.helperText}>{bulkJob.processed_records || 0} of {bulkJob.total_records || 0} records processed</p>
            {bulkJob.error_message ? <p style={styles.errorText}>{bulkJob.error_message}</p> : null}
            {bulkPreview.length ? (
              <div style={styles.tableWrap}>
                <table style={styles.table}>
                  <thead>
                    <tr>
                      <th style={styles.th}>Customer</th>
                      <th style={styles.th}>Risk</th>
                      <th style={styles.th}>Probability</th>
                      <th style={styles.th}>Recommendation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {bulkPreview.map((row) => (
                      <tr key={row.customer_id}>
                        <td style={styles.td}>{row.customer_id}</td>
                        <td style={styles.td}>{row.risk_category}</td>
                        <td style={styles.td}>{row.churn_probability.toFixed(1)}%</td>
                        <td style={styles.td}>{row.recommendation_type}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </div>
        ) : null}
      </section>

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
          <h3 style={styles.cardTitle}>Top customer segment</h3>
          {topSegment ? (
            <div style={styles.segmentPanel}>
              <span style={styles.segmentName}>{topSegment.segment}</span>
              <p style={styles.segmentDetail}>{topSegment.customer_count.toLocaleString()} customers • {topSegment.percentage}% of base</p>
              <div style={styles.segmentBarTrack}>
                <div style={{ ...styles.segmentBarFill, width: `${Math.min(topSegment.percentage, 100)}%` }} />
              </div>
              <div style={styles.segmentMeta}>Average churn risk: {topSegment.average_churn_risk}%</div>
            </div>
          ) : (
            <p style={styles.helperText}>Segmentation data is unavailable.</p>
          )}
        </div>
      </section>

      <section style={styles.grid}>
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Risk distribution</h3>
          <div style={styles.listGroup}>
            {riskDistribution.map((item) => (
              <div key={item.risk_category} style={styles.riskRow}>
                <div>
                  <strong>{item.risk_category}</strong>
                  <div style={styles.smallText}>{item.percentage}% of customers</div>
                </div>
                <div style={styles.riskCount}>{item.customer_count.toLocaleString()}</div>
              </div>
            ))}
          </div>
          <p style={styles.helperText}>Total customers represented: {totalRisk.toLocaleString()}</p>
        </div>

        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Customer segments</h3>
          <div style={styles.listGroup}>
            {segmentData.map((segment) => (
              <div key={segment.segment} style={styles.segmentRow}>
                <div>
                  <strong>{segment.segment}</strong>
                  <div style={styles.smallText}>{segment.customer_count.toLocaleString()} customers</div>
                </div>
                <div style={styles.segmentValue}>{segment.percentage}%</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section style={styles.grid}>
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Income vs churn</h3>
          {incomeData.map((item) => (
            <div key={item.income_level} style={styles.barRow}>
              <div style={styles.barHeader}>
                <span>{item.income_level}</span>
                <strong>{item.churn_rate}%</strong>
              </div>
              <div style={styles.barTrack}>
                <div style={{ ...styles.barFill, width: `${Math.min(item.churn_rate * 2.2, 100)}%` }} />
              </div>
            </div>
          ))}
        </div>

        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Device churn rate</h3>
          {deviceData.map((item) => (
            <div key={item.device_type} style={styles.barRow}>
              <div style={styles.barHeader}>
                <span>{item.device_type}</span>
                <strong>{item.churn_rate}%</strong>
              </div>
              <div style={styles.barTrack}>
                <div style={{ ...styles.barFill, width: `${Math.min(item.churn_rate * 2.2, 100)}%` }} />
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
                <th style={styles.th}>Satisfaction</th>
              </tr>
            </thead>
            <tbody>
              {customerRows.map((row) => (
                <tr key={row.customer_id}>
                  <td style={styles.td}>{row.customer_id}</td>
                  <td style={styles.td}>{row.risk_category || 'Pending'}</td>
                  <td style={styles.td}>${Number(row.monthly_total_spend || 0).toFixed(2)}</td>
                  <td style={styles.td}>{row.tenure_months} months</td>
                  <td style={styles.td}>{row.satisfaction_score ?? '-'}</td>
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
  title: { margin: '4px 0 8px', fontSize: '2rem' },
  subtitle: { margin: 0, color: '#94a3b8', maxWidth: '620px', lineHeight: 1.7 },
  headerCard: { background: 'rgba(17,24,39,0.85)', border: '1px solid rgba(255,255,255,0.08)', padding: '20px', borderRadius: '22px', minWidth: '240px', display: 'flex', flexDirection: 'column', gap: '10px' },
  headerCardLabel: { color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.14em', fontSize: '0.75rem' },
  headerCardValue: { fontSize: '2.25rem', lineHeight: 1.05, margin: 0 },
  headerCardMeta: { color: '#cbd5e1', fontSize: '0.95rem' },
  grid: { display: 'grid', gap: '16px', gridTemplateColumns: '2fr 1fr', marginBottom: '16px' },
  card: { background: 'rgba(17,24,39,0.8)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '16px', padding: '18px', boxShadow: '0 12px 34px rgba(0,0,0,0.25)' },
  cardTitle: { marginTop: 0, marginBottom: '12px' },
  sectionHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' },
  uploadRow: { display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '8px' },
  uploadInput: { flex: 1, minWidth: '260px', color: '#f7f8fc' },
  primaryButton: { background: '#10b981', color: '#07111f', border: 'none', borderRadius: '999px', padding: '10px 16px', fontWeight: 700, cursor: 'pointer' },
  errorText: { color: '#fca5a5', marginTop: '8px' },
  jobPanel: { marginTop: '14px', padding: '14px', borderRadius: '12px', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' },
  jobHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', marginBottom: '8px' },
  progressTrack: { height: '8px', width: '100%', background: 'rgba(255,255,255,0.08)', borderRadius: '999px', overflow: 'hidden', marginBottom: '6px' },
  progressFill: { height: '100%', background: 'linear-gradient(90deg, #10b981, #22d3ee)', borderRadius: '999px' },
  link: { color: '#7dd3fc', textDecoration: 'none' },
  metricGrid: { display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '12px' },
  metricCard: { border: '1px solid', borderRadius: '12px', padding: '14px', background: 'rgba(255,255,255,0.03)' },
  metricLabel: { display: 'block', color: '#cbd5e1', fontSize: '0.9rem', marginBottom: '6px' },
  metricValue: { fontSize: '1.2rem' },
  listGroup: { display: 'flex', flexDirection: 'column', gap: '8px' },
  listRow: { display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,0.08)' },
  riskRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 0', borderBottom: '1px solid rgba(255,255,255,0.08)' },
  riskCount: { fontWeight: 700, color: '#f8fafc' },
  smallText: { color: '#94a3b8', fontSize: '0.85rem', marginTop: '4px' },
  helperText: { color: '#94a3b8', fontSize: '0.85rem', marginTop: '8px' },
  segmentPanel: { display: 'grid', gap: '14px' },
  segmentName: { color: '#38bdf8', fontSize: '1.1rem', fontWeight: 700 },
  segmentDetail: { margin: 0, color: '#cbd5e1' },
  segmentBarTrack: { background: 'rgba(255,255,255,0.08)', height: '12px', borderRadius: '999px', overflow: 'hidden' },
  segmentBarFill: { height: '100%', background: 'linear-gradient(90deg, #6366f1, #22d3ee)', borderRadius: '999px' },
  segmentMeta: { color: '#94a3b8', fontSize: '0.9rem' },
  segmentRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 0', borderBottom: '1px solid rgba(255,255,255,0.08)' },
  segmentValue: { fontWeight: 700, color: '#f7f8fc' },
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