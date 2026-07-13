import React, { useState, useEffect } from 'react';
import { 
  getBulkJobInsights, 
  getBulkJobResults, 
  exportBulkPdfReport,
  exportReport
} from '../services/api';

export default function DatasetInsights({ jobId, onViewChange, setSelectedJobId, onNotify }) {
  const [insights, setInsights] = useState(null);
  const [results, setResults] = useState([]);
  const [page, setPage] = useState(1);
  const [limit] = useState(10);
  const [totalResults, setTotalResults] = useState(0);
  const [loading, setLoading] = useState(true);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [downloadingCsv, setDownloadingCsv] = useState(false);

  useEffect(() => {
    if (!jobId) {
      onNotify({
        type: 'error',
        title: 'Error',
        message: 'No Job ID provided for insights view.'
      });
      onViewChange('dashboard');
      return;
    }

    async function loadData() {
      setLoading(true);
      try {
        const insightsData = await getBulkJobInsights(jobId);
        setInsights(insightsData);

        const resultsData = await getBulkJobResults(jobId, page, limit);
        setResults(resultsData.results);
        setTotalResults(resultsData.total);
      } catch (err) {
        onNotify({
          type: 'error',
          title: 'Failed to load report',
          message: err.message || 'Unable to retrieve insights for this upload.'
        });
        onViewChange('dashboard');
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [jobId, page, limit, onViewChange, onNotify]);

  const handleDownloadCsv = async () => {
    setDownloadingCsv(true);
    try {
      const { blob, filename } = await exportReport('csv', { jobId });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      onNotify({
        type: 'success',
        title: 'CSV Downloaded',
        message: 'Prediction results downloaded successfully.'
      });
    } catch (err) {
      onNotify({
        type: 'error',
        title: 'CSV Export Failed',
        message: err.message || 'Unable to export CSV file.'
      });
    } finally {
      setDownloadingCsv(false);
    }
  };

  const handleDownloadPdf = async () => {
    setDownloadingPdf(true);
    try {
      const { blob, filename } = await exportBulkPdfReport(jobId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      onNotify({
        type: 'success',
        title: 'PDF Downloaded',
        message: 'Insights dashboard report saved as PDF.'
      });
    } catch (err) {
      onNotify({
        type: 'error',
        title: 'PDF Export Failed',
        message: err.message || 'Unable to export PDF report.'
      });
    } finally {
      setDownloadingPdf(false);
    }
  };

  if (loading || !insights) {
    return (
      <div style={styles.loadingContainer}>
        <div style={styles.loadingSpinner}></div>
        <p style={{ marginTop: '16px', color: '#94a3b8' }}>Generating Dataset Insights Report...</p>
      </div>
    );
  }

  const kpis = insights.kpis;
  const totalPages = Math.ceil(totalResults / limit);

  return (
    <div style={styles.container}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <button 
            type="button" 
            style={styles.backButton}
            onClick={() => {
              setSelectedJobId('');
              onViewChange('dashboard');
            }}
          >
            ← Back to Executive Dashboard
          </button>
          <h1 style={styles.title}>Dataset Insights Dashboard</h1>
          <p style={styles.subtitle}>
            Bulk Upload Report &bull; Job ID: <span style={styles.jobIdHighlight}>{jobId}</span>
          </p>
        </div>
        <div style={styles.headerRight}>
          <button 
            type="button" 
            disabled={downloadingCsv}
            onClick={handleDownloadCsv}
            style={styles.secondaryButton}
          >
            {downloadingCsv ? 'Downloading CSV...' : 'Download Results CSV'}
          </button>
          <button 
            type="button" 
            disabled={downloadingPdf}
            onClick={handleDownloadPdf}
            style={styles.primaryButton}
          >
            {downloadingPdf ? 'Generating PDF...' : 'Download Insights PDF'}
          </button>
        </div>
      </header>

      {/* KPI Cards Grid */}
      <section style={styles.kpiGrid}>
        <div style={styles.kpiCard}>
          <div style={{ ...styles.kpiGlow, background: '#6366f1' }} />
          <span style={styles.kpiLabel}>Total Monitored</span>
          <strong style={{ ...styles.kpiValue, color: '#818cf8' }}>
            {kpis.total_customers.toLocaleString()}
          </strong>
          <span style={styles.kpiDesc}>Uploaded customer rows</span>
        </div>
        <div style={styles.kpiCard}>
          <div style={{ ...styles.kpiGlow, background: '#ef4444' }} />
          <span style={styles.kpiLabel}>Predicted Churn</span>
          <strong style={{ ...styles.kpiValue, color: '#f87171' }}>
            {kpis.predicted_churn_customers.toLocaleString()}
          </strong>
          <span style={styles.kpiDesc}>Customers likely to leave</span>
        </div>
        <div style={styles.kpiCard}>
          <div style={{ ...styles.kpiGlow, background: '#f59e0b' }} />
          <span style={styles.kpiLabel}>High Risk Users</span>
          <strong style={{ ...styles.kpiValue, color: '#fbbf24' }}>
            {kpis.high_risk_customers.toLocaleString()}
          </strong>
          <span style={styles.kpiDesc}>Churn probability &gt; 70%</span>
        </div>
        <div style={styles.kpiCard}>
          <div style={{ ...styles.kpiGlow, background: '#10b981' }} />
          <span style={styles.kpiLabel}>Revenue at Risk</span>
          <strong style={{ ...styles.kpiValue, color: '#34d399' }}>
            ${kpis.monthly_revenue_at_risk.toLocaleString()}
          </strong>
          <span style={styles.kpiDesc}>Monthly spend at high risk</span>
        </div>
      </section>

      {/* Row of primary charts */}
      <section style={styles.grid2Columns}>
        {/* Risk Distribution Card */}
        <div style={styles.glassCard}>
          <h3 style={styles.cardTitle}>Churn Risk Distribution</h3>
          <p style={styles.cardSubtitle}>Segmentation of uploaded customers by churn risk category</p>
          <div style={styles.chartContainer}>
            {insights.risk_distribution.map((item) => {
              const colorsMap = {
                Low: { text: '#34d399', bg: 'rgba(16, 185, 129, 0.15)', bar: '#10b981' },
                Medium: { text: '#fbbf24', bg: 'rgba(245, 158, 11, 0.15)', bar: '#f59e0b' },
                High: { text: '#f87171', bg: 'rgba(239, 68, 68, 0.15)', bar: '#ef4444' }
              };
              const colorInfo = colorsMap[item.risk_category] || colorsMap.Low;
              return (
                <div key={item.risk_category} style={styles.distributionRow}>
                  <div style={styles.distHeader}>
                    <span style={{ ...styles.distCategory, color: colorInfo.text }}>
                      {item.risk_category} Risk
                    </span>
                    <span style={styles.distStats}>
                      <strong>{item.customer_count.toLocaleString()}</strong> ({item.percentage}%)
                    </span>
                  </div>
                  <div style={styles.progressBarBg}>
                    <div style={{ ...styles.progressBarFill, width: `${item.percentage}%`, background: colorInfo.bar }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Churn Probability Histogram */}
        <div style={styles.glassCard}>
          <h3 style={styles.cardTitle}>Churn Probability Buckets</h3>
          <p style={styles.cardSubtitle}>Distribution of risk probabilities in 10% buckets</p>
          <div style={styles.histogramWrapper}>
            {insights.churn_probability_buckets.map((b) => (
              <div key={b.bucket} style={styles.histogramColumn}>
                <div style={styles.histogramBarTrack}>
                  <div 
                    style={{ 
                      ...styles.histogramBarFill, 
                      height: `${(b.count / (kpis.total_customers || 1)) * 100}%` 
                    }} 
                    title={`${b.bucket}: ${b.count} customers`}
                  />
                </div>
                <span style={styles.histogramLabel}>{b.bucket.replace('%', '')}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Secondary Demographic Risk Grids */}
      <section style={styles.grid3Columns}>
        {/* Device Type Risk */}
        <div style={styles.glassCard}>
          <h3 style={styles.cardTitle}>Risk by Device Type</h3>
          <div style={{ marginTop: '12px' }}>
            {insights.device_risk_breakdown.map((d) => (
              <div key={d.device_type} style={styles.breakdownRow}>
                <div style={styles.breakdownHeader}>
                  <span style={styles.breakdownName}>{d.device_type}</span>
                  <span style={styles.breakdownMeta}>{d.high_risk} High Risk / {d.total_customers} total</span>
                </div>
                <div style={styles.progressBarBg}>
                  <div style={{ ...styles.progressBarFill, width: `${d.churn_rate}%`, background: '#ef4444' }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Payment Mode Risk */}
        <div style={styles.glassCard}>
          <h3 style={styles.cardTitle}>Risk by Payment Mode</h3>
          <div style={{ marginTop: '12px' }}>
            {insights.payment_risk_breakdown.map((p) => (
              <div key={p.payment_mode} style={styles.breakdownRow}>
                <div style={styles.breakdownHeader}>
                  <span style={styles.breakdownName}>{p.payment_mode}</span>
                  <span style={styles.breakdownMeta}>{p.high_risk} High Risk / {p.total_customers} total</span>
                </div>
                <div style={styles.progressBarBg}>
                  <div style={{ ...styles.progressBarFill, width: `${p.churn_rate}%`, background: '#ef4444' }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Income Level Risk */}
        <div style={styles.glassCard}>
          <h3 style={styles.cardTitle}>Risk by Income Level</h3>
          <div style={{ marginTop: '12px' }}>
            {insights.income_risk_breakdown.map((i) => (
              <div key={i.income_level} style={styles.breakdownRow}>
                <div style={styles.breakdownHeader}>
                  <span style={styles.breakdownName}>{i.income_level} Income</span>
                  <span style={styles.breakdownMeta}>{i.high_risk} High Risk / {i.total_customers} total</span>
                </div>
                <div style={styles.progressBarBg}>
                  <div style={{ ...styles.progressBarFill, width: `${i.churn_rate}%`, background: '#ef4444' }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Engagement & Retention Section */}
      <section style={styles.grid2Columns}>
        {/* Engagement Averages by Risk */}
        <div style={styles.glassCard}>
          <h3 style={styles.cardTitle}>Engagement Metrics by Risk Category</h3>
          <div style={styles.tableWrap}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>Risk Category</th>
                  <th style={styles.th}>Avg Weekly Usage</th>
                  <th style={styles.th}>Avg Support Tickets</th>
                  <th style={styles.th}>Avg App Switches</th>
                </tr>
              </thead>
              <tbody>
                {insights.engagement_by_risk.map((item) => (
                  <tr key={item.risk_category}>
                    <td style={styles.td}><strong>{item.risk_category}</strong></td>
                    <td style={styles.td}>{item.avg_usage_hours} hrs</td>
                    <td style={styles.td}>{item.avg_support_interactions} tickets</td>
                    <td style={styles.td}>{item.avg_app_switches} times</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Retention Offer Recommendations Breakdown */}
        <div style={styles.glassCard}>
          <h3 style={styles.cardTitle}>Retention Offer Split</h3>
          <div style={{ marginTop: '12px' }}>
            {insights.recommendation_type_counts.map((rec) => (
              <div key={rec.recommendation_type} style={styles.breakdownRow}>
                <div style={styles.breakdownHeader}>
                  <span style={styles.breakdownName}>{rec.recommendation_type}</span>
                  <span style={styles.breakdownMeta}>{rec.count} recommendations</span>
                </div>
                <div style={styles.progressBarBg}>
                  <div 
                    style={{ 
                      ...styles.progressBarFill, 
                      width: `${(rec.count / kpis.total_customers) * 100}%`, 
                      background: '#6366f1' 
                    }} 
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Tables Row: Top High Risk & Top Low Engagement */}
      <section style={styles.grid2Columns}>
        {/* Top High Churn Probability */}
        <div style={styles.glassCard}>
          <h3 style={styles.cardTitle}>Highest Churn Risk Customers</h3>
          <div style={styles.tableWrap}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>Customer ID</th>
                  <th style={styles.th}>Probability</th>
                  <th style={styles.th}>Tenure</th>
                  <th style={styles.th}>Support Tickets</th>
                  <th style={styles.th}>Offer</th>
                </tr>
              </thead>
              <tbody>
                {insights.tables.top_high_risk_customers.map((c) => (
                  <tr key={c.customer_id}>
                    <td style={styles.td}><strong>{c.customer_id}</strong></td>
                    <td style={{ ...styles.td, color: '#f87171', fontWeight: 'bold' }}>{c.churn_probability}%</td>
                    <td style={styles.td}>{c.tenure_months} months</td>
                    <td style={styles.td}>{c.customer_support_interactions}</td>
                    <td style={styles.td}>{c.recommendation_type}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Low Engagement High Risk */}
        <div style={styles.glassCard}>
          <h3 style={styles.cardTitle}>Low Engagement, High-Risk Users</h3>
          <div style={styles.tableWrap}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>Customer ID</th>
                  <th style={styles.th}>Probability</th>
                  <th style={styles.th}>Usage</th>
                  <th style={styles.th}>Satisfaction</th>
                  <th style={styles.th}>Offer</th>
                </tr>
              </thead>
              <tbody>
                {insights.tables.low_engagement_high_risk_customers.map((c) => (
                  <tr key={c.customer_id}>
                    <td style={styles.td}><strong>{c.customer_id}</strong></td>
                    <td style={{ ...styles.td, color: '#f87171', fontWeight: 'bold' }}>{c.churn_probability}%</td>
                    <td style={styles.td}>{c.avg_usage_hours_per_week} hrs/wk</td>
                    <td style={styles.td}>{c.satisfaction_score}/10</td>
                    <td style={styles.td}>{c.recommendation_type}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Main Results Table Section */}
      <section style={styles.glassCard}>
        <h3 style={styles.cardTitle}>All Upload Prediction Records</h3>
        <p style={styles.cardSubtitle}>Full paginated listing of predictions in the uploaded dataset</p>
        <div style={styles.tableWrap}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Customer ID</th>
                <th style={styles.th}>Age</th>
                <th style={styles.th}>Tenure (Months)</th>
                <th style={styles.th}>Spend</th>
                <th style={styles.th}>Usage (Hrs/Wk)</th>
                <th style={styles.th}>Satisfaction</th>
                <th style={styles.th}>Churn Probability</th>
                <th style={styles.th}>Risk Category</th>
                <th style={styles.th}>Recommendation</th>
              </tr>
            </thead>
            <tbody>
              {results.map((c) => {
                const colorsMap = {
                  Low: '#34d399',
                  Medium: '#fbbf24',
                  High: '#f87171'
                };
                return (
                  <tr key={c.customer_id}>
                    <td style={styles.td}><strong>{c.customer_id}</strong></td>
                    <td style={styles.td}>{c.age}</td>
                    <td style={styles.td}>{c.tenure_months}m</td>
                    <td style={styles.td}>${c.monthly_total_spend.toFixed(2)}</td>
                    <td style={styles.td}>{c.avg_usage_hours_per_week} hrs</td>
                    <td style={styles.td}>{c.satisfaction_score}/10</td>
                    <td style={{ ...styles.td, fontWeight: 'bold' }}>{c.churn_probability}%</td>
                    <td style={{ ...styles.td, color: colorsMap[c.risk_category], fontWeight: 'bold' }}>
                      {c.risk_category}
                    </td>
                    <td style={styles.td}>{c.recommendation_type}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {/* Pagination controls */}
        {totalPages > 1 && (
          <div style={styles.paginationRow}>
            <button 
              type="button" 
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
              style={page <= 1 ? styles.disabledPageBtn : styles.pageBtn}
            >
              Previous
            </button>
            <span style={styles.pageLabel}>
              Page {page} of {totalPages} &bull; ({totalResults} total records)
            </span>
            <button 
              type="button" 
              disabled={page >= totalPages}
              onClick={() => setPage(page + 1)}
              style={page >= totalPages ? styles.disabledPageBtn : styles.pageBtn}
            >
              Next
            </button>
          </div>
        )}
      </section>
    </div>
  );
}

const styles = {
  container: {
    padding: '24px 40px',
    display: 'flex',
    flexDirection: 'column',
    gap: '24px',
    background: '#07111f',
    minHeight: '100vh',
    fontFamily: 'Inter, system-ui, sans-serif'
  },
  loadingContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '60vh',
    background: '#07111f'
  },
  loadingSpinner: {
    width: '40px',
    height: '40px',
    border: '4px solid rgba(99, 102, 241, 0.1)',
    borderTop: '4px solid #6366f1',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite'
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
    paddingBottom: '20px'
  },
  headerLeft: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px'
  },
  backButton: {
    background: 'none',
    border: 'none',
    color: '#818cf8',
    cursor: 'pointer',
    fontSize: '0.9rem',
    fontWeight: 600,
    alignSelf: 'flex-start',
    padding: '0',
    marginBottom: '8px',
    transition: 'color 0.2s'
  },
  title: {
    fontSize: '1.8rem',
    fontWeight: 700,
    color: '#f8fafc',
    margin: 0
  },
  subtitle: {
    fontSize: '0.95rem',
    color: '#94a3b8',
    margin: 0
  },
  jobIdHighlight: {
    color: '#818cf8',
    fontFamily: 'monospace',
    fontWeight: 'bold',
    background: 'rgba(99, 102, 241, 0.15)',
    padding: '2px 6px',
    borderRadius: '4px'
  },
  headerRight: {
    display: 'flex',
    gap: '12px',
    alignItems: 'center'
  },
  primaryButton: {
    background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
    border: 'none',
    color: '#ffffff',
    padding: '10px 20px',
    fontSize: '0.9rem',
    fontWeight: 600,
    borderRadius: '8px',
    cursor: 'pointer',
    boxShadow: '0 4px 12px rgba(99, 102, 241, 0.2)',
    transition: 'all 0.2s'
  },
  secondaryButton: {
    background: 'rgba(255, 255, 255, 0.03)',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    color: '#e2e8f0',
    padding: '10px 20px',
    fontSize: '0.9rem',
    fontWeight: 600,
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'all 0.2s'
  },
  kpiGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
    gap: '20px'
  },
  kpiCard: {
    position: 'relative',
    background: 'rgba(15, 23, 42, 0.4)',
    border: '1px solid rgba(255, 255, 255, 0.06)',
    borderRadius: '12px',
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    overflow: 'hidden'
  },
  kpiGlow: {
    position: 'absolute',
    top: '-30px',
    right: '-30px',
    width: '80px',
    height: '80px',
    borderRadius: '50%',
    filter: 'blur(35px)',
    opacity: 0.35
  },
  kpiLabel: {
    fontSize: '0.85rem',
    color: '#94a3b8',
    fontWeight: 500,
    textTransform: 'uppercase',
    letterSpacing: '0.05em'
  },
  kpiValue: {
    fontSize: '2rem',
    fontWeight: 800,
    margin: '4px 0'
  },
  kpiDesc: {
    fontSize: '0.8rem',
    color: '#64748b'
  },
  grid2Columns: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(450px, 1fr))',
    gap: '24px'
  },
  grid3Columns: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
    gap: '24px'
  },
  glassCard: {
    background: 'rgba(15, 23, 42, 0.45)',
    backdropFilter: 'blur(16px)',
    border: '1px solid rgba(255, 255, 255, 0.06)',
    borderRadius: '16px',
    padding: '24px',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden'
  },
  cardTitle: {
    fontSize: '1.15rem',
    fontWeight: 700,
    color: '#f1f5f9',
    margin: 0
  },
  cardSubtitle: {
    fontSize: '0.85rem',
    color: '#64748b',
    marginTop: '4px',
    marginBottom: '16px'
  },
  chartContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    marginTop: '12px'
  },
  distributionRow: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px'
  },
  distHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '0.9rem'
  },
  distCategory: {
    fontWeight: 'bold'
  },
  distStats: {
    color: '#94a3b8'
  },
  progressBarBg: {
    height: '8px',
    background: 'rgba(255, 255, 255, 0.05)',
    borderRadius: '4px',
    overflow: 'hidden'
  },
  progressBarFill: {
    height: '100%',
    borderRadius: '4px'
  },
  histogramWrapper: {
    display: 'flex',
    alignItems: 'flex-end',
    height: '150px',
    gap: '8px',
    marginTop: '20px'
  },
  histogramColumn: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    height: '100%',
    justifyContent: 'flex-end'
  },
  histogramBarTrack: {
    height: '120px',
    width: '100%',
    display: 'flex',
    alignItems: 'flex-end',
    background: 'rgba(255, 255, 255, 0.02)',
    borderRadius: '4px',
    overflow: 'hidden'
  },
  histogramBarFill: {
    width: '100%',
    background: 'linear-gradient(to top, #6366f1, #818cf8)',
    borderRadius: '4px 4px 0 0',
    transition: 'height 0.3s ease'
  },
  histogramLabel: {
    fontSize: '0.7rem',
    color: '#64748b',
    marginTop: '6px',
    whiteSpace: 'nowrap'
  },
  breakdownRow: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    marginBottom: '14px'
  },
  breakdownHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '0.85rem'
  },
  breakdownName: {
    color: '#e2e8f0',
    fontWeight: 500
  },
  breakdownMeta: {
    color: '#64748b'
  },
  tableWrap: {
    overflowX: 'auto',
    marginTop: '10px'
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    textAlign: 'left'
  },
  th: {
    borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
    padding: '12px 16px',
    color: '#94a3b8',
    fontSize: '0.85rem',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.05em'
  },
  td: {
    borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
    padding: '12px 16px',
    color: '#cbd5e1',
    fontSize: '0.9rem'
  },
  paginationRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: '20px',
    paddingTop: '16px',
    borderTop: '1px solid rgba(255, 255, 255, 0.08)'
  },
  pageBtn: {
    background: 'rgba(255, 255, 255, 0.03)',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '6px',
    color: '#cbd5e1',
    padding: '6px 14px',
    cursor: 'pointer',
    fontSize: '0.85rem',
    transition: 'all 0.2s'
  },
  disabledPageBtn: {
    background: 'rgba(255, 255, 255, 0.01)',
    border: '1px solid rgba(255, 255, 255, 0.04)',
    borderRadius: '6px',
    color: '#475569',
    padding: '6px 14px',
    fontSize: '0.85rem',
    cursor: 'not-allowed'
  },
  pageLabel: {
    fontSize: '0.85rem',
    color: '#94a3b8'
  }
};
