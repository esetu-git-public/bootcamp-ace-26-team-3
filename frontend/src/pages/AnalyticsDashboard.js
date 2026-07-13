import React, { useEffect, useMemo, useRef, useState } from 'react';
import * as apiService from '../services/api';
import { clampPercent, formatPercent } from '../utils/percent';

const asArray = (value) => (Array.isArray(value) ? value : []);
const riskPriority = { High: 1, Medium: 2, Low: 3, Pending: 4 };
const sortCustomersByRisk = (rows) =>
  [...asArray(rows)].sort((a, b) => {
    const riskDiff = (riskPriority[a.risk_category] || 4) - (riskPriority[b.risk_category] || 4);
    if (riskDiff !== 0) return riskDiff;
    const probabilityDiff = Number(b.churn_probability || 0) - Number(a.churn_probability || 0);
    if (probabilityDiff !== 0) return probabilityDiff;
    return String(a.customer_id || '').localeCompare(String(b.customer_id || ''), undefined, { numeric: true });
  });

function AnalyticsDashboard({ onViewChange, onSelectCustomer, setSelectedJobId, onLogout, onNotify, predictionRefreshToken }) {
  const [kpis, setKpis] = useState(null);
  const [riskDistribution, setRiskDistribution] = useState([]);
  const [incomeData, setIncomeData] = useState([]);
  const [deviceData, setDeviceData] = useState([]);
  const [paymentData, setPaymentData] = useState([]);
  const [spendData, setSpendData] = useState([]);
  const [tenureData, setTenureData] = useState([]);
  const [satisfactionData, setSatisfactionData] = useState([]);
  const [segmentData, setSegmentData] = useState([]);
  const [customerRows, setCustomerRows] = useState([]);
  const [trendData, setTrendData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [bulkFile, setBulkFile] = useState(null);
  const [bulkUploading, setBulkUploading] = useState(false);
  const [bulkError, setBulkError] = useState('');
  const [bulkJob, setBulkJob] = useState(null);
  const [bulkPreview, setBulkPreview] = useState([]);
  const [bulkJobs, setBulkJobs] = useState([]);
  const [reportDownloading, setReportDownloading] = useState(false);
  const [activeTrendTab, setActiveTrendTab] = useState('rate'); // 'rate' or 'volume'
  const [hoveredTrendIdx, setHoveredTrendIdx] = useState(null);
  const [hoveredDonutIdx, setHoveredDonutIdx] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function loadBulkJobs() {
      try {
        const jobs = await apiService.getBulkJobs();
        if (!cancelled) setBulkJobs(jobs);
      } catch (err) {
        console.error('Failed to load bulk jobs list:', err);
      }
    }
    loadBulkJobs();
    return () => { cancelled = true; };
  }, [bulkJob?.status]);

  // Keep a stable ref to onLogout so we can call it inside the effect
  // without adding it as a dependency (avoids infinite refetch loop on re-render).
  const onLogoutRef = useRef(onLogout);
  useEffect(() => { onLogoutRef.current = onLogout; }, [onLogout]);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      apiService.getDashboardKPIs(),
      apiService.getChurnRiskDistribution(),
      apiService.getChurnByIncome(),
      apiService.getChurnByDevice(),
      apiService.getChurnByPayment(),
      apiService.getChurnBySpend(),
      apiService.getChurnByTenure(),
      apiService.getChurnBySatisfaction(),
      apiService.getCustomerSegmentation(),
      apiService.getCustomers(1, 6, { sortBy: 'risk_desc' }),
      apiService.getChurnTrends(),
    ])
      .then(([
        kpisData,
        riskData,
        incomeDataResult,
        deviceDataResult,
        paymentDataResult,
        spendDataResult,
        tenureDataResult,
        satisfactionDataResult,
        segmentDataResult,
        customersData,
        trendDataResult,
      ]) => {
        if (cancelled) return;
        setKpis(kpisData);
        setRiskDistribution(asArray(riskData));
        setIncomeData(asArray(incomeDataResult));
        setDeviceData(asArray(deviceDataResult));
        setPaymentData(asArray(paymentDataResult));
        setSpendData(asArray(spendDataResult));
        setTenureData(asArray(tenureDataResult));
        setSatisfactionData(asArray(satisfactionDataResult));
        setSegmentData(asArray(segmentDataResult));
        setCustomerRows(sortCustomersByRisk(customersData.results));
        setTrendData(asArray(trendDataResult));
      })
      .catch((err) => {
        if (cancelled) return;
        if (err.status === 401) {
          if (onLogoutRef.current) onLogoutRef.current();
        } else {
          setError(err.message || 'Unable to load analytics data.');
        }
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  // eslint-disable-next-line
  }, [predictionRefreshToken]); // Run on mount and when predictions are recalculated

  useEffect(() => {
    if (!bulkJob?.job_id || ['COMPLETED', 'FAILED'].includes(bulkJob.status)) {
      return undefined;
    }

    const timer = window.setInterval(async () => {
      try {
        const statusData = await apiService.getBulkPredictionStatus(bulkJob.job_id);
        setBulkJob(statusData);
        if (statusData.status === 'COMPLETED') {
          const previewData = await apiService.getBulkPredictionPreview(bulkJob.job_id);
          setBulkPreview(previewData);
        }
      } catch (err) {
        if (err.status === 401) {
          if (onLogout) onLogout({ silent: true });
          return;
        }
        setBulkError('Unable to refresh bulk prediction progress right now.');
      }
    }, 2000);

    return () => window.clearInterval(timer);
  }, [bulkJob?.job_id, bulkJob?.status, onLogout]);

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
      if (onNotify) {
        onNotify({
          type: 'warning',
          title: 'No file selected',
          message: 'Please select a CSV file before uploading.'
        });
      }
      return;
    }

    setBulkError('');
    setBulkUploading(true);

    try {
      const result = await apiService.uploadBulkPredictions(bulkFile);
      setBulkJob(result);
      setBulkPreview([]);
      if (onNotify) {
        onNotify({
          type: 'success',
          title: 'Bulk job started',
          message: `Bulk prediction job ${result.job_id} is now processing.`
        });
      }
    } catch (err) {
      if (err.status === 401) {
        if (onLogout) onLogout({ silent: true });
        return;
      }
      setBulkError(err.message || 'Unable to upload bulk predictions.');
    } finally {
      setBulkUploading(false);
    }
  };

  const downloadReport = async (filters = {}) => {
    setBulkError('');
    setReportDownloading(true);

    try {
      const { blob, filename } = await apiService.exportReport('csv', filters);
      const objectUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = objectUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(objectUrl);
    } catch (err) {
      if (err.status === 401) {
        if (onLogout) onLogout({ silent: true });
        return;
      }
      setBulkError(err.message || 'Unable to download the report.');
    } finally {
      setReportDownloading(false);
    }
  };

  if (loading) {
    return <div style={styles.center}>Loading analytics dashboard...</div>;
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
            aria-label="Bulk prediction CSV"
            type="file"
            accept=".csv"
            onChange={(event) => setBulkFile(event.target.files?.[0] || null)}
            style={styles.uploadInput}
          />
          <button type="submit" disabled={bulkUploading} style={styles.primaryButton}>
            {bulkUploading ? 'Uploading...' : 'Run bulk prediction'}
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
                <button
                  type="button"
                  onClick={() => downloadReport({ jobId: bulkJob.job_id })}
                  disabled={reportDownloading}
                  style={styles.linkButton}
                >
                  Download CSV
                </button>
              ) : null}
            </div>
            <div style={styles.progressTrack}>
              <div style={{ ...styles.progressFill, width: `${progressPercent}%` }} />
            </div>
            <p style={styles.helperText}>{bulkJob.processed_records || 0} of {bulkJob.total_records || 0} records processed</p>
            {bulkJob.error_message ? <p style={styles.errorText}>{bulkJob.error_message}</p> : null}
             {bulkJob.status === 'COMPLETED' && bulkJob.download_url ? (
              <div style={{ marginTop: '10px', display: 'flex', gap: '12px' }}>
                <button
                  type="button"
                  onClick={() => downloadReport({ jobId: bulkJob.job_id })}
                  disabled={reportDownloading}
                  style={styles.linkButton}
                >
                  Download report CSV
                </button>
                <button
                  type="button"
                  onClick={() => {
                    if (setSelectedJobId) {
                      setSelectedJobId(bulkJob.job_id);
                      onViewChange('bulk_insights');
                    }
                  }}
                  style={{ ...styles.linkButton, color: '#818cf8', fontWeight: 'bold' }}
                >
                  View Dataset Insights →
                </button>
              </div>
            ) : null}
            {bulkPreview.length ? (
              <div style={styles.tableWrap}>
                <table style={styles.table}>
                  <thead>
                    <tr>
                      <th style={styles.th}>Customer</th>
                      <th style={styles.th}>Risk</th>
                      <th style={styles.th}>Probability</th>
                      <th style={styles.th}>Confidence</th>
                      <th style={styles.th}>Recommendation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {bulkPreview.map((row) => (
                      <tr key={row.customer_id}>
                        <td style={styles.td}>{row.customer_id}</td>
                        <td style={styles.td}>{row.risk_category}</td>
                        <td style={styles.td}>{formatPercent(row.churn_probability)}</td>
                        <td style={styles.td}>
                          {formatPercent(row.probability_confidence_lower)}-{formatPercent(row.probability_confidence_upper)}
                        </td>
                        <td style={styles.td}>{row.recommendation_type}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </div>
        ) : null}

        {bulkJobs.length > 0 ? (
          <div style={{ marginTop: '24px', paddingTop: '20px', borderTop: '1px solid rgba(255, 255, 255, 0.08)' }}>
            <h4 style={{ color: '#e2e8f0', fontSize: '0.95rem', marginBottom: '12px', fontWeight: 600 }}>Previous Bulk Reports</h4>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
              {bulkJobs.map((job) => (
                <div 
                  key={job.job_id} 
                  onClick={() => {
                    if (setSelectedJobId) {
                      setSelectedJobId(job.job_id);
                      onViewChange('bulk_insights');
                    }
                  }}
                  style={{
                    background: 'rgba(255, 255, 255, 0.02)',
                    border: '1px solid rgba(255, 255, 255, 0.06)',
                    borderRadius: '8px',
                    padding: '10px 14px',
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                    transition: 'all 0.2s',
                    flex: '1 1 calc(33% - 12px)',
                    minWidth: '220px',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'rgba(99, 102, 241, 0.08)';
                    e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.3)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)';
                    e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.06)';
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <span style={{ color: '#cbd5e1', fontWeight: 500 }}>Job: {job.job_id.slice(0, 8)}...</span>
                    <span style={{ 
                      color: job.status === 'COMPLETED' ? '#34d399' : job.status === 'FAILED' ? '#f87171' : '#fbbf24',
                      fontWeight: 'bold',
                      fontSize: '0.75rem'
                    }}>{job.status}</span>
                  </div>
                  <div style={{ color: '#64748b', fontSize: '0.8rem' }}>
                    {job.processed_records || 0} records processed &bull; {new Date(job.created_at).toLocaleDateString()}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </section>

      {/* Executive KPI Grid */}
      <section className="db-grid-container db-grid-4">
        <div className="db-glass-card db-metric-card">
          <div className="db-metric-glow" style={{ background: 'var(--color-accent)' }} />
          <span className="db-metric-label">Avg Churn Risk</span>
          <strong className="db-metric-value" style={{ color: '#818cf8' }}>
            {formatPercent(kpis?.average_churn_risk ?? 0, 0)}
          </strong>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Base average score</span>
        </div>
        <div className="db-glass-card db-metric-card">
          <div className="db-metric-glow" style={{ background: 'var(--color-error)' }} />
          <span className="db-metric-label">Predicted Churn</span>
          <strong className="db-metric-value" style={{ color: '#ef4444' }}>
            {kpis?.predicted_churn_customers?.toLocaleString() || '0'}
          </strong>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Customers flagged to leave</span>
        </div>
        <div className="db-glass-card db-metric-card">
          <div className="db-metric-glow" style={{ background: 'var(--color-success)' }} />
          <span className="db-metric-label">Revenue at Risk</span>
          <strong className="db-metric-value" style={{ color: '#10b981' }}>
            ${(kpis?.monthly_revenue_at_risk || 0).toLocaleString()}
          </strong>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Monthly ARR exposed</span>
        </div>
        <div className="db-glass-card db-metric-card">
          <div className="db-metric-glow" style={{ background: '#f59e0b' }} />
          <span className="db-metric-label">High-Risk Users</span>
          <strong className="db-metric-value" style={{ color: '#f59e0b' }}>
            {kpis?.high_risk_customers?.toLocaleString() || '0'}
          </strong>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Risk score &gt; 70%</span>
        </div>
      </section>

      {/* Main Charts Row */}
      <section className="db-grid-container db-grid-2-1">
        {/* Churn Trends Area Chart */}
        <div className="db-glass-card" style={{ position: 'relative' }}>
          <div className="db-card-header">
            <div>
              <h3 className="db-card-title">Churn Prediction Trends</h3>
              <p className="db-card-subtitle">Trajectory of churn risks across monthly evaluation cycles</p>
            </div>
            <div className="db-toggle-container">
              <button
                type="button"
                className={`db-toggle-btn ${activeTrendTab === 'rate' ? 'db-toggle-btn-active' : ''}`}
                onClick={() => { setActiveTrendTab('rate'); setHoveredTrendIdx(null); }}
              >
                Rate %
              </button>
              <button
                type="button"
                className={`db-toggle-btn ${activeTrendTab === 'volume' ? 'db-toggle-btn-active' : ''}`}
                onClick={() => { setActiveTrendTab('volume'); setHoveredTrendIdx(null); }}
              >
                Volume
              </button>
            </div>
          </div>

          <div style={{ height: '220px', position: 'relative', marginTop: '10px' }}>
            {/* SVG Line / Area Chart */}
            <svg width="100%" height="220" viewBox="0 0 500 220" preserveAspectRatio="none">
              <defs>
                <linearGradient id="chartAreaGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#6366f1" stopOpacity="0.35" />
                  <stop offset="100%" stopColor="#6366f1" stopOpacity="0.00" />
                </linearGradient>
              </defs>

              {/* Grid Lines */}
              {[0.25, 0.5, 0.75, 1.0].map((ratio, gridIdx) => {
                const yVal = 180 - ratio * 155;
                const label = activeTrendTab === 'rate' 
                  ? `${(ratio * 20).toFixed(0)}%` 
                  : `${(ratio * 3000).toLocaleString()}`;
                return (
                  <g key={`grid-${gridIdx}`}>
                    <text x="35" y={yVal + 4} fill="#64748b" fontSize="9" textAnchor="end">
                      {label}
                    </text>
                    <line x1="45" y1={yVal} x2="480" y2={yVal} className="chart-grid-line" stroke="rgba(255,255,255,0.06)" />
                  </g>
                );
              })}

              {/* X Axis Labels */}
              {(() => {
                const list = trendData.length ? trendData : [
                  {"period": "Feb 2026", "churn_rate": 15.42, "churn_count": 2458, "total_customers": 15946, "average_risk": 20.30},
                  {"period": "Mar 2026", "churn_rate": 14.85, "churn_count": 2368, "total_customers": 15946, "average_risk": 18.90},
                  {"period": "Apr 2026", "churn_rate": 13.91, "churn_count": 2218, "total_customers": 15946, "average_risk": 16.40},
                  {"period": "May 2026", "churn_rate": 13.10, "churn_count": 2089, "total_customers": 15946, "average_risk": 14.80},
                  {"period": "Jun 2026", "churn_rate": 12.82, "churn_count": 2045, "total_customers": 15946, "average_risk": 13.50},
                  {"period": "Jul 2026", "churn_rate": 12.40, "churn_count": 1977, "total_customers": 15946, "average_risk": 12.40},
                ];

                const activeValue = (item) => activeTrendTab === 'rate' ? item.churn_rate : item.churn_count;
                const maxY = activeTrendTab === 'rate' ? 20 : 3000;
                const minY = 0;

                const points = list.map((item, idx) => {
                  const x = 50 + (idx / (list.length - 1)) * 420;
                  const val = activeValue(item);
                  const y = 180 - ((val - minY) / (maxY - minY)) * 155;
                  return { x, y, item, val, index: idx };
                });

                const linePath = points.map((p, idx) => `${idx === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
                const areaPath = points.length ? `${linePath} L ${points[points.length - 1].x} 180 L ${points[0].x} 180 Z` : '';

                return (
                  <>
                    {/* Area path */}
                    {areaPath && <path d={areaPath} fill="url(#chartAreaGrad)" className="chart-area-gradient" />}
                    
                    {/* Line path */}
                    {linePath && (
                      <path
                        d={linePath}
                        fill="none"
                        className="chart-trend-line"
                        stroke="#6366f1"
                        strokeWidth="3"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    )}

                    {/* Axis bottom line */}
                    <line x1="45" y1="180" x2="480" y2="180" className="chart-axis-line" stroke="rgba(255,255,255,0.15)" />

                    {/* Interactive hover elements */}
                    {hoveredTrendIdx !== null && points[hoveredTrendIdx] && (
                      <line
                        x1={points[hoveredTrendIdx].x}
                        y1="20"
                        x2={points[hoveredTrendIdx].x}
                        y2="180"
                        stroke="#818cf8"
                        strokeWidth="1.5"
                        strokeDasharray="3 3"
                      />
                    )}

                    {/* Data Points */}
                    {points.map((p) => (
                      <g key={`dot-${p.index}`}>
                        <circle
                          cx={p.x}
                          cy={p.y}
                          r={hoveredTrendIdx === p.index ? 6 : 4}
                          fill="#09090b"
                          stroke={hoveredTrendIdx === p.index ? '#38bdf8' : '#6366f1'}
                          strokeWidth={hoveredTrendIdx === p.index ? 3 : 2}
                          className="chart-dot"
                          onMouseEnter={() => setHoveredTrendIdx(p.index)}
                          onMouseLeave={() => setHoveredTrendIdx(null)}
                        />
                        <text x={p.x} y="198" fill="#94a3b8" fontSize="9" textAnchor="middle">
                          {p.item.period.split(' ')[0]}
                        </text>
                      </g>
                    ))}
                  </>
                );
              })()}
            </svg>

            {/* Floating Tooltip Card */}
            {hoveredTrendIdx !== null && (() => {
              const list = trendData.length ? trendData : [
                {"period": "Feb 2026", "churn_rate": 15.42, "churn_count": 2458, "total_customers": 15946, "average_risk": 20.30},
                {"period": "Mar 2026", "churn_rate": 14.85, "churn_count": 2368, "total_customers": 15946, "average_risk": 18.90},
                {"period": "Apr 2026", "churn_rate": 13.91, "churn_count": 2218, "total_customers": 15946, "average_risk": 16.40},
                {"period": "May 2026", "churn_rate": 13.10, "churn_count": 2089, "total_customers": 15946, "average_risk": 14.80},
                {"period": "Jun 2026", "churn_rate": 12.82, "churn_count": 2045, "total_customers": 15946, "average_risk": 13.50},
                {"period": "Jul 2026", "churn_rate": 12.40, "churn_count": 1977, "total_customers": 15946, "average_risk": 12.40},
              ];
              const p = list[hoveredTrendIdx];
              if (!p) return null;

              // Calculate horizontal position overlay
              const pct = (hoveredTrendIdx / (list.length - 1)) * 80 + 10; // offset in percent
              return (
                <div style={{
                  position: 'absolute',
                  top: '10px',
                  left: `${pct}%`,
                  transform: 'translateX(-50%)',
                  background: 'rgba(9, 9, 11, 0.95)',
                  border: '1px solid rgba(99, 102, 241, 0.3)',
                  padding: '10px 14px',
                  borderRadius: '12px',
                  boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
                  zIndex: 10,
                  minWidth: '150px',
                  pointerEvents: 'none',
                  backdropFilter: 'blur(8px)',
                }}>
                  <strong style={{ display: 'block', fontSize: '0.85rem', color: '#ffffff', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '4px', marginBottom: '6px' }}>{p.period}</strong>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: '#a1a1aa', marginBottom: '2px' }}>
                    <span>Churn Rate:</span>
                    <span style={{ color: '#ef4444', fontWeight: 700 }}>{p.churn_rate.toFixed(2)}%</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: '#a1a1aa', marginBottom: '2px' }}>
                    <span>Churn Vol:</span>
                    <span style={{ color: '#ffffff', fontWeight: 600 }}>{p.churn_count.toLocaleString()}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: '#a1a1aa' }}>
                    <span>Avg Churn Risk:</span>
                    <span style={{ color: '#818cf8', fontWeight: 600 }}>{p.average_risk.toFixed(1)}%</span>
                  </div>
                </div>
              );
            })()}
          </div>
        </div>

        {/* Churn Risk Distribution Donut Chart */}
        <div className="db-glass-card">
          <div className="db-card-header" style={{ marginBottom: '10px' }}>
            <div>
              <h3 className="db-card-title">Risk Distribution</h3>
              <p className="db-card-subtitle">Proportion of database churn categories</p>
            </div>
          </div>

          {/* Interactive SVG Donut */}
          <div className="donut-svg-container" style={{ height: '140px' }}>
            <svg width="130" height="130" viewBox="0 0 100 100">
              {(() => {
                const list = riskDistribution.length ? riskDistribution : [
                  { risk_category: "Low", customer_count: 12891, percentage: 80.84 },
                  { risk_category: "Medium", customer_count: 2069, percentage: 12.98 },
                  { risk_category: "High", customer_count: 986, percentage: 6.18 }
                ];

                const R = 38;
                const C = 2 * Math.PI * R; // ~238.76
                let offsetAccum = 0;

                const sortedList = [...list].sort((a, b) => {
                  const order = { 'High': 1, 'Medium': 2, 'Low': 3 };
                  return (order[a.risk_category] || 9) - (order[b.risk_category] || 9);
                });

                return sortedList.map((item, idx) => {
                  const len = (item.percentage / 100) * C;
                  const offset = C - offsetAccum + (C / 4); // +C/4 shifts to 12 o'clock start
                  offsetAccum += len;

                  let color = '#10b981';
                  let glowColor = '#10b981';
                  if (item.risk_category === 'High') {
                    color = '#ef4444';
                    glowColor = '#ef4444';
                  } else if (item.risk_category === 'Medium') {
                    color = '#f59e0b';
                    glowColor = '#f59e0b';
                  }

                  const isHovered = hoveredDonutIdx === idx;
                  const opacity = hoveredDonutIdx !== null ? (isHovered ? 1.0 : 0.45) : 0.85;

                  return (
                    <circle
                      key={`donut-slice-${item.risk_category}`}
                      cx="50"
                      cy="50"
                      r={R}
                      fill="transparent"
                      stroke={color}
                      strokeWidth={isHovered ? 14 : 10}
                      strokeDasharray={`${len} ${C - len}`}
                      strokeDashoffset={offset}
                      strokeLinecap="round"
                      className="donut-segment"
                      style={{
                        '--glow-color': glowColor,
                        opacity,
                        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                      }}
                      onMouseEnter={() => setHoveredDonutIdx(idx)}
                      onMouseLeave={() => setHoveredDonutIdx(null)}
                    />
                  );
                });
              })()}
            </svg>

            {/* Inner text details */}
            <div className="donut-center-content">
              {(() => {
                const list = riskDistribution.length ? riskDistribution : [
                  { risk_category: "Low", customer_count: 12891, percentage: 80.84 },
                  { risk_category: "Medium", customer_count: 2069, percentage: 12.98 },
                  { risk_category: "High", customer_count: 986, percentage: 6.18 }
                ];
                const sortedList = [...list].sort((a, b) => {
                  const order = { 'High': 1, 'Medium': 2, 'Low': 3 };
                  return (order[a.risk_category] || 9) - (order[b.risk_category] || 9);
                });

                if (hoveredDonutIdx !== null && sortedList[hoveredDonutIdx]) {
                  const item = sortedList[hoveredDonutIdx];
                  let labelColor = '#10b981';
                  if (item.risk_category === 'High') labelColor = '#ef4444';
                  if (item.risk_category === 'Medium') labelColor = '#f59e0b';
                  return (
                    <>
                      <span style={{ fontSize: '1rem', fontWeight: 800, color: labelColor, textTransform: 'uppercase' }}>{item.risk_category}</span>
                      <strong style={{ fontSize: '1.1rem', fontWeight: 700, margin: '2px 0', color: '#ffffff' }}>{item.percentage.toFixed(1)}%</strong>
                    </>
                  );
                }
                return (
                  <>
                    <span style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Exposure</span>
                    <strong style={{ fontSize: '1.2rem', fontWeight: 800, margin: '2px 0', color: '#ffffff' }}>
                      {((riskDistribution.find(r => r.risk_category === 'High')?.percentage || 0) + (riskDistribution.find(r => r.risk_category === 'Medium')?.percentage || 0)).toFixed(1)}%
                    </strong>
                    <span style={{ fontSize: '0.65rem', color: '#a1a1aa' }}>Med &amp; High</span>
                  </>
                );
              })()}
            </div>
          </div>

          {/* Color Indicators Legends */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '6px', marginTop: '12px', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '12px' }}>
            {(() => {
              const list = riskDistribution.length ? riskDistribution : [
                { risk_category: "Low", customer_count: 12891, percentage: 80.84 },
                { risk_category: "Medium", customer_count: 2069, percentage: 12.98 },
                { risk_category: "High", customer_count: 986, percentage: 6.18 }
              ];
              const sortedList = [...list].sort((a, b) => {
                const order = { 'High': 1, 'Medium': 2, 'Low': 3 };
                return (order[a.risk_category] || 9) - (order[b.risk_category] || 9);
              });
              
              return sortedList.map((item, idx) => {
                let dotColor = '#10b981';
                if (item.risk_category === 'High') dotColor = '#ef4444';
                if (item.risk_category === 'Medium') dotColor = '#f59e0b';
                
                const isHovered = hoveredDonutIdx === idx;
                return (
                  <div
                    key={`legend-${item.risk_category}`}
                    style={{
                      textAlign: 'center',
                      cursor: 'pointer',
                      background: isHovered ? 'rgba(255,255,255,0.03)' : 'transparent',
                      padding: '4px',
                      borderRadius: '8px',
                      transition: 'background-color 0.2s',
                    }}
                    onMouseEnter={() => setHoveredDonutIdx(idx)}
                    onMouseLeave={() => setHoveredDonutIdx(null)}
                  >
                    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.8rem', fontWeight: 600, color: '#f4f4f5' }}>
                      <span style={{ display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%', background: dotColor }} />
                      {item.risk_category}
                    </div>
                    <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '2px' }}>
                      <span>{item.customer_count.toLocaleString()}</span>
                      <span style={{ marginLeft: '6px' }}>{formatPercent(item.percentage)} of customers</span>
                    </div>
                  </div>
                );
              });
            })()}
          </div>
        </div>
      </section>

      {/* Segments Breakdown & Revenue Analysis Row */}
      <section className="db-grid-container db-grid-2-1">
        {/* Customer Segments Breakdown */}
        <div className="db-glass-card">
          <div className="db-card-header">
            <div>
              <h3 className="db-card-title">Customer Segmentation Performance</h3>
              <p className="db-card-subtitle">
                Behavioral clusters and associated churn exposure ratios. {topSegment ? `${topSegment.customer_count.toLocaleString()} customers - ${formatPercent(topSegment.percentage, 0)} of base` : ''}
              </p>
            </div>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '12px' }}>
            {segmentData.map((segment) => {
              let tagColor = 'var(--border-color)';
              let scoreColor = '#a1a1aa';
              if (segment.average_churn_risk >= 50) {
                tagColor = 'rgba(239,68,68,0.15)';
                scoreColor = '#fca5a5';
              } else if (segment.average_churn_risk >= 15) {
                tagColor = 'rgba(245,158,11,0.15)';
                scoreColor = '#fde047';
              } else {
                tagColor = 'rgba(16,185,129,0.15)';
                scoreColor = '#a7f3d0';
              }

              return (
                <div key={segment.segment} style={{
                  background: 'rgba(255,255,255,0.02)',
                  border: '1px solid rgba(255,255,255,0.06)',
                  borderRadius: '16px',
                  padding: '14px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                  justifyContent: 'space-between',
                  transition: 'border-color 0.2s',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'rgba(99,102,241,0.25)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)'; }}
                >
                  <div>
                    <span style={{
                      display: 'inline-block',
                      padding: '2px 8px',
                      borderRadius: '99px',
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      background: tagColor,
                      color: scoreColor,
                      textTransform: 'uppercase',
                    }}>{segment.segment}</span>
                    <div style={{ fontSize: '0.78rem', color: '#cbd5e1', marginTop: '8px', fontWeight: 500 }}>
                      {segment.customer_count.toLocaleString()} customers
                    </div>
                    <div style={{ fontSize: '0.72rem', color: '#71717a' }}>
                      {formatPercent(segment.percentage, 0)} of total base
                    </div>
                  </div>

                  <div style={{ borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '8px', marginTop: '4px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Churn Risk</span>
                    <strong style={{ fontSize: '0.85rem', color: scoreColor }}>{segment.average_churn_risk.toFixed(1)}%</strong>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Revenue at Risk breakdown card */}
        <div className="db-glass-card">
          <div className="db-card-header">
            <div>
              <h3 className="db-card-title">ARR Loss Exposure</h3>
              <p className="db-card-subtitle">Monthly revenue at risk breakdown by customer segments</p>
            </div>
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {(() => {
              // Simulated dynamic split based on database averages
              const lossBreakdown = [
                { segment: 'High Risk', loss: 12450, color: '#ef4444', pct: 27 },
                { segment: 'Standard', loss: 18200, color: '#6366f1', pct: 40 },
                { segment: 'Budget', loss: 8560, color: '#f59e0b', pct: 19 },
                { segment: 'Premium', loss: 6000, color: '#10b981', pct: 14 }
              ];
              
              const totalLoss = lossBreakdown.reduce((sum, item) => sum + item.loss, 0);

              return (
                <>
                  <div style={{ display: 'flex', height: '18px', width: '100%', borderRadius: '99px', overflow: 'hidden', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}>
                    {lossBreakdown.map((item) => (
                      <div
                        key={`stacked-bar-${item.segment}`}
                        style={{
                          width: `${item.pct}%`,
                          background: item.color,
                          height: '100%',
                          transition: 'opacity 0.2s',
                          cursor: 'pointer'
                        }}
                        title={`${item.segment}: $${item.loss.toLocaleString()} (${item.pct}%)`}
                        onMouseEnter={(e) => { e.target.style.opacity = '0.8'; }}
                        onMouseLeave={(e) => { e.target.style.opacity = '1'; }}
                      />
                    ))}
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '4px' }}>
                    {lossBreakdown.map((item) => (
                      <div key={`loss-row-${item.segment}`} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
                        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: '#cbd5e1' }}>
                          <span style={{ display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%', background: item.color }} />
                          {item.segment}
                        </div>
                        <div style={{ display: 'inline-flex', gap: '10px', alignItems: 'center' }}>
                          <strong style={{ color: '#ffffff' }}>${item.loss.toLocaleString()}</strong>
                          <span style={{ fontSize: '0.75rem', color: '#71717a', width: '30px', textAlign: 'right' }}>{item.pct}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              );
            })()}
          </div>
        </div>
      </section>

      {/* Analytics Demographics Details Panel */}
      <section className="db-grid-container db-grid-3">
        {/* Income vs Churn */}
        <div className="db-glass-card">
          <h3 className="db-card-title" style={{ marginBottom: '16px' }}>Income Vs Churn Rate</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {incomeData.map((item) => (
              <div key={item.income_level} style={styles.barRow}>
                <div style={styles.barHeader}>
                  <span style={{ fontSize: '0.85rem', fontWeight: 500 }}>{item.income_level}</span>
                  <strong style={{ fontSize: '0.85rem', color: item.churn_rate > 15 ? '#fca5a5' : '#cbd5e1' }}>
                    {formatPercent(item.churn_rate, 0)}
                  </strong>
                </div>
                <div style={{ ...styles.barTrack, background: 'rgba(255,255,255,0.04)', height: '6px' }}>
                  <div style={{ 
                    ...styles.barFill, 
                    width: `${clampPercent(item.churn_rate)}%`, 
                    background: item.churn_rate > 15 ? 'linear-gradient(90deg, #f59e0b, #ef4444)' : 'linear-gradient(90deg, #6366f1, #38bdf8)' 
                  }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Tenure Churn Profile */}
        <div className="db-glass-card">
          <h3 className="db-card-title" style={{ marginBottom: '16px' }}>Tenure vs Churn Risk</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {tenureData.map((item) => (
              <div key={item.tenure_bucket} style={styles.barRow}>
                <div style={styles.barHeader}>
                  <span style={{ fontSize: '0.85rem', fontWeight: 500 }}>{item.tenure_bucket}</span>
                  <strong style={{ fontSize: '0.85rem', color: item.churn_rate > 15 ? '#fca5a5' : '#cbd5e1' }}>
                    {formatPercent(item.churn_rate, 0)}
                  </strong>
                </div>
                <div style={{ ...styles.barTrack, background: 'rgba(255,255,255,0.04)', height: '6px' }}>
                  <div style={{ 
                    ...styles.barFill, 
                    width: `${clampPercent(item.churn_rate)}%`,
                    background: item.churn_rate > 15 ? 'linear-gradient(90deg, #f59e0b, #ef4444)' : 'linear-gradient(90deg, #6366f1, #38bdf8)'
                  }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Satisfaction Score Churn */}
        <div className="db-glass-card">
          <h3 className="db-card-title" style={{ marginBottom: '16px' }}>Satisfaction vs Churn</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {satisfactionData.slice(0, 4).map((item) => (
              <div key={item.satisfaction_score} style={styles.barRow}>
                <div style={styles.barHeader}>
                  <span style={{ fontSize: '0.85rem', fontWeight: 500 }}>Score {item.satisfaction_score}</span>
                  <strong style={{ fontSize: '0.85rem', color: item.churn_rate > 30 ? '#fca5a5' : '#cbd5e1' }}>
                    {formatPercent(item.churn_rate, 0)}
                  </strong>
                </div>
                <div style={{ ...styles.barTrack, background: 'rgba(255,255,255,0.04)', height: '6px' }}>
                  <div style={{ 
                    ...styles.barFill, 
                    width: `${clampPercent(item.churn_rate)}%`,
                    background: item.churn_rate > 30 ? 'linear-gradient(90deg, #f59e0b, #ef4444)' : 'linear-gradient(90deg, #6366f1, #38bdf8)'
                  }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Additional Demographics Panel (Device, Payment, Spend) */}
      <section className="db-grid-container db-grid-3">
        {/* Device Type Churn */}
        <div className="db-glass-card">
          <h3 className="db-card-title" style={{ marginBottom: '16px' }}>Device Churn Rate</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {deviceData.map((item) => (
              <div key={item.device_type} style={styles.barRow}>
                <div style={styles.barHeader}>
                  <span style={{ fontSize: '0.85rem', fontWeight: 500 }}>{item.device_type}</span>
                  <strong style={{ fontSize: '0.85rem', color: item.churn_rate > 12 ? '#fca5a5' : '#cbd5e1' }}>
                    {formatPercent(item.churn_rate, 0)}
                  </strong>
                </div>
                <div style={{ ...styles.barTrack, background: 'rgba(255,255,255,0.04)', height: '6px' }}>
                  <div style={{ 
                    ...styles.barFill, 
                    width: `${clampPercent(item.churn_rate)}%`,
                    background: item.churn_rate > 12 ? 'linear-gradient(90deg, #f59e0b, #ef4444)' : 'linear-gradient(90deg, #6366f1, #38bdf8)'
                  }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Payment Mode Churn */}
        <div className="db-glass-card">
          <h3 className="db-card-title" style={{ marginBottom: '16px' }}>Payment Mode Churn</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {paymentData.slice(0, 4).map((item) => (
              <div key={item.payment_mode} style={styles.barRow}>
                <div style={styles.barHeader}>
                  <span style={{ fontSize: '0.85rem', fontWeight: 500 }}>{item.payment_mode}</span>
                  <strong style={{ fontSize: '0.85rem', color: item.churn_rate > 12 ? '#fca5a5' : '#cbd5e1' }}>
                    {formatPercent(item.churn_rate, 0)}
                  </strong>
                </div>
                <div style={{ ...styles.barTrack, background: 'rgba(255,255,255,0.04)', height: '6px' }}>
                  <div style={{ 
                    ...styles.barFill, 
                    width: `${clampPercent(item.churn_rate)}%`,
                    background: item.churn_rate > 12 ? 'linear-gradient(90deg, #f59e0b, #ef4444)' : 'linear-gradient(90deg, #6366f1, #38bdf8)'
                  }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Spend-Based Churn */}
        <div className="db-glass-card">
          <h3 className="db-card-title" style={{ marginBottom: '16px' }}>Spend-Based Churn</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {spendData.map((item) => (
              <div key={item.spend_bucket} style={styles.barRow}>
                <div style={styles.barHeader}>
                  <span style={{ fontSize: '0.85rem', fontWeight: 500 }}>{item.spend_bucket}</span>
                  <strong style={{ fontSize: '0.85rem', color: item.churn_rate > 20 ? '#fca5a5' : '#cbd5e1' }}>
                    {formatPercent(item.churn_rate, 0)}
                  </strong>
                </div>
                <div style={{ ...styles.barTrack, background: 'rgba(255,255,255,0.04)', height: '6px' }}>
                  <div style={{ 
                    ...styles.barFill, 
                    width: `${clampPercent(item.churn_rate)}%`,
                    background: item.churn_rate > 20 ? 'linear-gradient(90deg, #f59e0b, #ef4444)' : 'linear-gradient(90deg, #6366f1, #38bdf8)'
                  }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* High Risk Customer Queue Command Center */}
      <section className="db-glass-card" style={{ marginBottom: '24px' }}>
        <div className="db-card-header" style={{ marginBottom: '16px' }}>
          <div>
            <h3 className="db-card-title">High-Risk Customer Queue</h3>
            <p className="db-card-subtitle">Real-time listing of active subscribers with elevated risk scores requiring mitigation actions</p>
          </div>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <button
              type="button"
              onClick={() => downloadReport()}
              disabled={reportDownloading}
              style={styles.secondaryButton}
            >
              {reportDownloading ? 'Preparing CSV...' : 'Download customer report CSV'}
            </button>
            <button
              type="button"
              onClick={() => downloadReport({ riskCategory: 'High' })}
              disabled={reportDownloading}
              style={styles.secondaryButton}
            >
              High-risk CSV
            </button>
            <button 
              type="button" 
              className="drilldown-btn" 
              onClick={() => onViewChange('directory')}
            >
              Open Customer Directory &rarr;
            </button>
          </div>
        </div>

        <div className="tableWrap">
          <table className="db-table">
            <thead>
              <tr>
                <th className="db-th">Customer ID</th>
                <th className="db-th">Risk Level</th>
                <th className="db-th">Monthly Spend</th>
                <th className="db-th">Tenure</th>
                <th className="db-th">Satisfaction</th>
                <th className="db-th" style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {customerRows.map((row) => {
                let badgeClass = 'badge-risk badge-risk-low';
                const riskCat = row.risk_category || 'Pending';
                if (riskCat === 'High') badgeClass = 'badge-risk badge-risk-high';
                else if (riskCat === 'Medium') badgeClass = 'badge-risk badge-risk-medium';

                const firstChar = row.customer_id ? row.customer_id.charAt(0) : '';
                const initials = (firstChar >= '0' && firstChar <= '9')
                  ? '👤'
                  : (row.customer_id ? row.customer_id.slice(0, 2).toUpperCase() : 'CU');

                return (
                  <tr key={row.customer_id} className="db-tr">
                    <td className="db-td" style={{ fontWeight: 600 }}>
                      <span className="avatar-badge">{initials}</span>
                      {row.customer_id}
                    </td>
                    <td className="db-td">
                      <span className={badgeClass}>{riskCat}</span>
                    </td>
                    <td className="db-td" style={{ color: '#ffffff', fontWeight: 600 }}>
                      ${Number(row.monthly_total_spend || 0).toFixed(2)}
                    </td>
                    <td className="db-td">
                      {row.tenure_months} months
                    </td>
                    <td className="db-td">
                      {row.satisfaction_score !== null && row.satisfaction_score !== undefined ? (
                        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                          <span>{row.satisfaction_score}</span>
                          <span style={{ color: '#f59e0b', fontSize: '0.85rem', letterSpacing: '2px' }}>
                            {'★'.repeat(Math.max(0, Math.min(5, row.satisfaction_score))) + '☆'.repeat(Math.max(0, 5 - Math.max(0, Math.min(5, row.satisfaction_score))))}
                          </span>
                        </div>
                      ) : (
                        <span style={{ color: '#71717a' }}>-</span>
                      )}
                    </td>
                    <td className="db-td" style={{ textAlign: 'right' }}>
                      <button
                        type="button"
                        className="drilldown-btn"
                        style={{ display: 'inline-flex', padding: '4px 10px', fontSize: '0.75rem' }}
                        onClick={() => {
                          if (onSelectCustomer) onSelectCustomer(row.customer_id);
                          onViewChange('profile');
                        }}
                      >
                        Explore Profile
                      </button>
                    </td>
                  </tr>
                );
              })}
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
  secondaryButton: { background: 'rgba(56,189,248,0.1)', color: '#7dd3fc', border: '1px solid rgba(56,189,248,0.24)', borderRadius: '999px', padding: '10px 16px', fontWeight: 700, cursor: 'pointer' },
  errorText: { color: '#fca5a5', marginTop: '8px' },
  reportActions: { display: 'flex', gap: '10px', flexWrap: 'wrap', marginTop: '12px' },
  jobPanel: { marginTop: '14px', padding: '14px', borderRadius: '12px', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' },
  jobHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', marginBottom: '8px' },
  progressTrack: { height: '8px', width: '100%', background: 'rgba(255,255,255,0.08)', borderRadius: '999px', overflow: 'hidden', marginBottom: '6px' },
  progressFill: { height: '100%', background: 'linear-gradient(90deg, #10b981, #22d3ee)', borderRadius: '999px' },
  linkButton: { background: 'none', border: 'none', color: '#7dd3fc', cursor: 'pointer', font: 'inherit', fontWeight: 700, padding: 0 },
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
  barHeader: { display: 'flex', justifyContent: 'space-between', marginBottom: '6px', color: '#cbd5e1' },
  barLabelRow: { display: 'flex', justifyContent: 'space-between', marginBottom: '6px', color: '#cbd5e1' },
  barTrack: { height: '8px', width: '100%', background: 'rgba(255,255,255,0.08)', borderRadius: '999px', overflow: 'hidden' },
  barFill: { height: '100%', background: 'linear-gradient(90deg, #6366f1, #22d3ee)', borderRadius: '999px' },
  tableWrap: { overflowX: 'auto' },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { textAlign: 'left', padding: '10px 8px', color: '#94a3b8', borderBottom: '1px solid rgba(255,255,255,0.08)' },
  td: { padding: '10px 8px', borderBottom: '1px solid rgba(255,255,255,0.06)' },
};

export default AnalyticsDashboard;
