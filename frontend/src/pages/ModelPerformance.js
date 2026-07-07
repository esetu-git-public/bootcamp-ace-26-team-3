import React, { useState, useEffect } from 'react';
import * as apiService from '../services/api';
import { clampPercent, formatPercent } from '../utils/percent';

export default function ModelPerformance({ onViewChange, onLogout }) {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchModelMetrics = async () => {
      setLoading(true);
      setError('');
      try {
        const data = await apiService.getModelMetrics();
        setMetrics(data);
      } catch (err) {
        if (err.status === 401) {
          if (onLogout) onLogout();
        } else {
          setError(err.message || 'Error fetching model metrics.');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchModelMetrics();
  }, [onLogout]);

  if (loading) {
    return <div style={styles.center}>Loading model performance diagnostics...</div>;
  }

  if (error) {
    return <div style={styles.center}>{error}</div>;
  }

  // Calculate confusion matrix percentages
  const matrix = metrics?.confusion_matrix || { tp: 0, fp: 0, tn: 0, fn: 0 };
  const totalMatrixCases = (matrix.tp + matrix.fp + matrix.tn + matrix.fn) || 1;
  const tnPercent = formatPercent(matrix.tn / totalMatrixCases, 1, { inputScale: 'fraction' });
  const fpPercent = formatPercent(matrix.fp / totalMatrixCases, 1, { inputScale: 'fraction' });
  const fnPercent = formatPercent(matrix.fn / totalMatrixCases, 1, { inputScale: 'fraction' });
  const tpPercent = formatPercent(matrix.tp / totalMatrixCases, 1, { inputScale: 'fraction' });

  // Normalize feature importance to find max value for scaling progress bars
  const featureImportances = metrics?.feature_importance ? Object.entries(metrics.feature_importance) : [];
  const maxImportance = featureImportances.length > 0 ? Math.max(...featureImportances.map(([_, v]) => v)) : 100;

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <div>
          <p style={styles.eyebrow}>Technical Diagnostics & Validation</p>
          <h1 style={styles.title}>Model Performance Dashboard</h1>
          <p style={styles.subtitle}>
            Analyze ML classification reliability, prediction boundaries, and feature weights for the active prediction model.
          </p>
        </div>
        <button onClick={() => onViewChange('dashboard')} style={styles.backBtn}>
          Back to Dashboard
        </button>
      </header>

      {/* Overview Metadata */}
      {metrics && (
        <section style={styles.metaSection}>
          <div style={styles.metaRow}>
            <span>Active Model Version:</span>
            <strong>{metrics.model_version}</strong>
          </div>
          <div style={styles.metaRow}>
            <span>Last Evaluated At:</span>
            <strong>{new Date(metrics.evaluated_at).toLocaleString()}</strong>
          </div>
        </section>
      )}

      {/* Metrics Row */}
      <section style={styles.metricsRow}>
        <MetricCard label="Accuracy" value={formatPercent(metrics.accuracy, 2, { inputScale: 'auto' })} tone="accent" />
        <MetricCard label="Precision" value={formatPercent(metrics.precision, 2, { inputScale: 'auto' })} tone="success" />
        <MetricCard label="Recall" value={formatPercent(metrics.recall, 2, { inputScale: 'auto' })} tone="warn" />
        <MetricCard label="F1 Score" value={formatPercent(metrics.f1_score, 2, { inputScale: 'auto' })} tone="danger" />
        <MetricCard label="ROC-AUC" value={formatPercent(metrics.roc_auc, 2, { inputScale: 'auto' })} tone="accent" />
      </section>

      {/* Grid Layout for Confusion Matrix and Feature Importance */}
      <section style={styles.grid}>
        {/* Left Column: Confusion Matrix */}
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Confusion Matrix</h3>
          <p style={styles.helperText}>
            Visualizes actual outcomes vs. model prediction performance on the evaluation test set.
          </p>

          <div style={styles.matrixContainer}>
            {/* Headers */}
            <div style={styles.matrixHeaderRow}>
              <div></div>
              <div>Predicted Stable</div>
              <div>Predicted Churn</div>
            </div>

            {/* Actual Stable Row */}
            <div style={styles.matrixRow}>
              <div style={styles.matrixLabelCell}>Actual Stable</div>
              
              {/* True Negative (TN) */}
              <div style={styles.matrixDataCell(true)}>
                <strong style={styles.matrixValueText}>{matrix.tn.toLocaleString()}</strong>
                <span style={styles.matrixLabelText}>True Negatives</span>
                <span style={styles.matrixPercentText}>{tnPercent}</span>
              </div>

              {/* False Positive (FP) */}
              <div style={styles.matrixDataCell(false)}>
                <strong style={styles.matrixValueText}>{matrix.fp.toLocaleString()}</strong>
                <span style={styles.matrixLabelText}>False Positives</span>
                <span style={styles.matrixPercentText}>{fpPercent}</span>
              </div>
            </div>

            {/* Actual Churn Row */}
            <div style={styles.matrixRow}>
              <div style={styles.matrixLabelCell}>Actual Churn</div>

              {/* False Negative (FN) */}
              <div style={styles.matrixDataCell(false)}>
                <strong style={styles.matrixValueText}>{matrix.fn.toLocaleString()}</strong>
                <span style={styles.matrixLabelText}>False Negatives</span>
                <span style={styles.matrixPercentText}>{fnPercent}</span>
              </div>

              {/* True Positive (TP) */}
              <div style={styles.matrixDataCell(true)}>
                <strong style={styles.matrixValueText}>{matrix.tp.toLocaleString()}</strong>
                <span style={styles.matrixLabelText}>True Positives</span>
                <span style={styles.matrixPercentText}>{tpPercent}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Feature Importance */}
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Global Feature Importance</h3>
          <p style={styles.helperText}>
            Calculated features importance representing average contribution weight of input features to model decision boundaries.
          </p>

          <div style={styles.featureList}>
            {featureImportances.map(([feature, val]) => {
              const scaledPercent = maxImportance ? clampPercent((val / maxImportance) * 100) : 0;
              return (
                <div key={feature} style={styles.featureRow}>
                  <div style={styles.featureHeader}>
                    <span style={styles.featureName}>{feature.replace(/_/g, ' ')}</span>
                    <strong style={styles.featureValue}>{val.toFixed(1)}%</strong>
                  </div>
                  <div style={styles.featureProgressTrack}>
                    <div style={{ ...styles.featureProgressBar, width: `${scaledPercent}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
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
  backBtn: {
    background: 'rgba(99, 102, 241, 0.12)',
    border: '1px solid rgba(99, 102, 241, 0.3)',
    borderRadius: '12px',
    color: '#818cf8',
    padding: '10px 20px',
    fontSize: '0.9rem',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  metaSection: {
    display: 'flex',
    gap: '24px',
    background: 'rgba(15, 23, 42, 0.4)',
    border: '1px solid rgba(255, 255, 255, 0.05)',
    borderRadius: '12px',
    padding: '14px 20px',
    marginBottom: '20px',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  metaRow: {
    fontSize: '0.9rem',
    color: '#cbd5e1',
    display: 'flex',
    gap: '8px',
  },
  metricsRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: '16px',
    marginBottom: '20px',
  },
  metricCard: {
    border: '1px solid',
    borderRadius: '16px',
    padding: '18px',
    background: 'rgba(17, 24, 39, 0.5)',
    boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
  },
  metricLabel: { display: 'block', color: '#cbd5e1', fontSize: '0.85rem', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' },
  metricValue: { fontSize: '1.75rem', fontWeight: 700, color: '#f8fafc' },
  grid: { display: 'grid', gap: '20px', gridTemplateColumns: '1fr 1fr', marginBottom: '16px' },
  card: { background: 'rgba(17,24,39,0.8)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '16px', padding: '24px', boxShadow: '0 12px 34px rgba(0,0,0,0.25)' },
  cardTitle: { marginTop: 0, marginBottom: '8px', color: '#e2e8f0', fontSize: '1.25rem' },
  helperText: { margin: '0 0 20px 0', color: '#94a3b8', fontSize: '0.85rem', lineHeight: 1.5 },
  
  // Confusion Matrix Styling
  matrixContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  matrixHeaderRow: {
    display: 'grid',
    gridTemplateColumns: '100px 1fr 1fr',
    textAlign: 'center',
    fontWeight: 'bold',
    color: '#94a3b8',
    fontSize: '0.85rem',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  matrixRow: {
    display: 'grid',
    gridTemplateColumns: '100px 1fr 1fr',
    alignItems: 'stretch',
    minHeight: '90px',
    gap: '12px',
  },
  matrixLabelCell: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'flex-start',
    fontWeight: 'bold',
    color: '#cbd5e1',
    fontSize: '0.85rem',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  matrixDataCell: (isCorrect) => ({
    background: isCorrect ? 'rgba(16, 185, 129, 0.05)' : 'rgba(239, 68, 68, 0.05)',
    border: `1px solid ${isCorrect ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)'}`,
    borderRadius: '12px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '8px',
  }),
  matrixValueText: { fontSize: '1.4rem', fontWeight: 700, color: '#f8fafc', marginBottom: '2px' },
  matrixLabelText: { fontSize: '0.75rem', color: '#94a3b8', marginBottom: '4px', textAlign: 'center' },
  matrixPercentText: { fontSize: '0.8rem', fontWeight: 600, color: '#cbd5e1' },

  // Feature Importance Progress Bars
  featureList: { display: 'flex', flexDirection: 'column', gap: '16px' },
  featureRow: { display: 'flex', flexDirection: 'column', gap: '6px' },
  featureHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  featureName: { color: '#cbd5e1', fontSize: '0.9rem' },
  featureValue: { color: '#f8fafc', fontSize: '0.9rem', fontWeight: 600 },
  featureProgressTrack: { height: '8px', background: 'rgba(255,255,255,0.06)', borderRadius: '999px', overflow: 'hidden' },
  featureProgressBar: { height: '100%', background: 'linear-gradient(90deg, #6366f1, #22d3ee)', borderRadius: '999px' },
};
