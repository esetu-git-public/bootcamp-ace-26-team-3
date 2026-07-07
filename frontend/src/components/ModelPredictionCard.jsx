/**
 * ModelPredictionCard Component
 * 
 * Displays ML model predictions with:
 * - Churn probability with confidence interval
 * - Risk category badge
 * - SHAP feature importance visualization
 * - Recommendation card
 * - Prediction timestamp
 */

import React from 'react';
import * as mlModel from '../services/mlModel';
import { clampPercent, formatPercent } from '../utils/percent';

export function ModelPredictionCard({ prediction, loading = false, error = null, onRegenerate = null }) {
  if (loading) {
    return (
      <div style={styles.card}>
        <h3 style={styles.cardTitle}>Model Prediction</h3>
        <div style={styles.loaderContainer}>
          <div style={styles.spinner}></div>
          <p>Calculating churn prediction…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.card}>
        <h3 style={styles.cardTitle}>Model Prediction</h3>
        <div style={styles.errorBox}>
          <p style={{ margin: 0 }}>⚠️ {error}</p>
        </div>
      </div>
    );
  }

  if (!prediction) {
    return (
      <div style={styles.card}>
        <h3 style={styles.cardTitle}>Model Prediction</h3>
        <p style={styles.placeholderText}>
          No prediction available. {onRegenerate && 'Click the button to generate one.'}
        </p>
      </div>
    );
  }

  const riskColors = mlModel.getRiskColors(prediction.risk_category);
  const isChurn = prediction.will_cancel === 1;

  return (
    <div style={styles.card}>
      <h3 style={styles.cardTitle}>Model Prediction</h3>

      {/* Churn Verdict */}
      <div style={styles.verdictBox(isChurn)}>
        {isChurn ? '🔴 PREDICTED CHURN RISK' : '🟢 PREDICTED STABLE'}
      </div>

      {/* Probability with Confidence Interval */}
      <div style={styles.metricRow}>
        <span style={styles.metricLabel}>Churn Probability:</span>
        <div style={styles.probabilityDisplay}>
          <span style={styles.probabilityValue}>
            {formatPercent(prediction.churn_probability, 2)}
          </span>
          {prediction.probability_confidence_lower !== undefined && prediction.probability_confidence_upper !== undefined && (
            <span style={styles.confidenceInterval}>
              (95% CI: {formatPercent(prediction.probability_confidence_lower, 2)} - {formatPercent(prediction.probability_confidence_upper, 2)})
            </span>
          )}
        </div>
      </div>

      {/* Risk Category */}
      <div style={styles.metricRow}>
        <span style={styles.metricLabel}>Risk Category:</span>
        <span style={styles.riskBadge(riskColors)}>
          {prediction.risk_category}
        </span>
      </div>

      {/* SHAP Explainability */}
      {prediction.explainability && (
        <div style={styles.explainabilitySection}>
          <h4 style={styles.subTitle}>Feature Importance (SHAP)</h4>
          <p style={styles.helperText}>
            Features that increased (red) or decreased (green) churn risk prediction:
          </p>
          <div style={styles.featureList}>
            {mlModel.formatExplainability(prediction.explainability).map((feature, idx) => (
              <FeatureImportanceBar key={idx} feature={feature} />
            ))}
          </div>
        </div>
      )}

      {/* Recommendation */}
      {prediction.recommendation_type && (
        <div style={styles.recommendationBox(isChurn)}>
          <h4 style={styles.recommendationTitle}>
            Recommended Action
          </h4>
          <p style={styles.recommendationAction}>
            <strong>{prediction.recommendation_type}</strong>
          </p>
          <p style={styles.recommendationDesc}>
            {prediction.recommendation_desc}
          </p>
        </div>
      )}

      {onRegenerate && (
        <button onClick={onRegenerate} style={styles.regenerateBtn}>
          Recalculate Prediction
        </button>
      )}
    </div>
  );
}

/**
 * Feature Importance Bar Component
 */
function FeatureImportanceBar({ feature }) {
  const isPositive = feature.impact === 'increases';
  const percentage = Math.min(Math.abs(feature.value) * 100, 100); // Scale for display
  const barColor = isPositive ? 'rgba(239, 68, 68, 0.6)' : 'rgba(16, 185, 129, 0.6)';
  const barDirection = isPositive ? 'flex-end' : 'flex-start';

  return (
    <div style={styles.featureRow}>
      <div style={styles.featureNameColumn}>
        <span style={styles.featureName}>{feature.feature}</span>
        <span style={styles.featureImpact}>{mlModel.interpretSHAPValue(feature.value)}</span>
      </div>
      <div style={styles.featureBarContainer}>
        <div
          style={{
            ...styles.featureBar,
            width: `${percentage}%`,
            backgroundColor: barColor,
            justifyContent: barDirection
          }}
        >
          {percentage > 15 && (
            <span style={styles.featureBarValue}>
              {isPositive ? '↑' : '↓'} {feature.value.toFixed(3)}
            </span>
          )}
        </div>
      </div>
      <span style={styles.featureValue}>
        {feature.value > 0 ? '+' : ''}{feature.value.toFixed(3)}
      </span>
    </div>
  );
}

/**
 * Risk Gauge Component - Visual representation of churn probability
 */
export function RiskGauge({ probability = 0 }) {
  const percent = clampPercent(probability);
  const riskLevel = mlModel.getRiskCategory(percent);
  const riskColors = mlModel.getRiskColors(riskLevel);
  const arcRatio = percent / 100;
  const arcY = 100 - 70 * Math.sqrt(Math.max(0, 1 - Math.pow((arcRatio - 0.5) * 2, 2)));
  const rotation = arcRatio * 180 - 90; // Rotate from -90 to 90 degrees

  return (
    <div style={styles.gaugeContainer}>
      <svg style={styles.gaugeSvg} viewBox="0 0 200 120">
        {/* Background arc */}
        <path
          d="M 30 100 A 70 70 0 0 1 170 100"
          fill="none"
          stroke="rgba(255, 255, 255, 0.1)"
          strokeWidth="8"
          strokeLinecap="round"
        />
        {/* Risk arc gradient */}
        <defs>
          <linearGradient id="riskGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="rgba(16, 185, 129, 0.6)" />
            <stop offset="50%" stopColor="rgba(251, 191, 36, 0.6)" />
            <stop offset="100%" stopColor="rgba(239, 68, 68, 0.6)" />
          </linearGradient>
        </defs>
        <path
          d={`M 30 100 A 70 70 0 0 1 ${30 + 140 * arcRatio} ${arcY}`}
          fill="none"
          stroke="url(#riskGradient)"
          strokeWidth="8"
          strokeLinecap="round"
        />
        {/* Needle */}
        <g transform={`translate(100, 100) rotate(${rotation})`}>
          <polygon points="0,-5 2,0 -2,0" fill={riskColors.text} />
          <line x1="0" y1="0" x2="0" y2="-60" stroke={riskColors.text} strokeWidth="2" />
        </g>
        {/* Center circle */}
        <circle cx="100" cy="100" r="6" fill={riskColors.text} />
      </svg>
      <div style={styles.gaugeLabel}>
        <div style={styles.gaugeLabelValue}>{formatPercent(percent)}</div>
        <div style={styles.gaugeLabelRisk}>{riskLevel} Risk</div>
      </div>
    </div>
  );
}

/**
 * Prediction Timeline Component - Shows prediction history
 */
export function PredictionTimeline({ predictions = [] }) {
  if (!predictions || predictions.length === 0) {
    return (
      <div style={styles.card}>
        <h3 style={styles.cardTitle}>Prediction History</h3>
        <p style={styles.placeholderText}>No historical predictions recorded.</p>
      </div>
    );
  }

  return (
    <div style={styles.card}>
      <h3 style={styles.cardTitle}>Prediction Timeline</h3>
      <div style={styles.timeline}>
        {predictions.map((prediction, idx) => (
          <PredictionTimelineEntry
            key={idx}
            prediction={prediction}
            isLatest={idx === 0}
          />
        ))}
      </div>
    </div>
  );
}

/**
 * Single timeline entry
 */
function PredictionTimelineEntry({ prediction, isLatest }) {
  const riskColors = mlModel.getRiskColors(prediction.risk_category || 'Low');

  return (
    <div style={styles.timelineEntry}>
      <div style={styles.timelineMarker(riskColors, isLatest)} />
      <div style={styles.timelineContent}>
        <div style={styles.timelineHeader}>
          <span style={styles.timelineTime}>
            {new Date(prediction.evaluated_at).toLocaleString()}
          </span>
          {isLatest && <span style={styles.latestBadge}>Latest</span>}
        </div>
        <div style={styles.timelineMetrics}>
          <span style={styles.timelineMetric}>
            Risk: <strong>{prediction.risk_category}</strong>
          </span>
          <span style={styles.timelineMetric}>
            Probability: <strong>{formatPercent(prediction.risk_score)}</strong>
          </span>
        </div>
      </div>
    </div>
  );
}

const styles = {
  // Card
  card: {
    background: 'rgba(17, 24, 39, 0.8)',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '16px',
    padding: '24px',
    marginBottom: '16px',
    boxShadow: '0 12px 34px rgba(0, 0, 0, 0.25)'
  },
  cardTitle: {
    marginTop: 0,
    marginBottom: '16px',
    color: '#e2e8f0',
    fontSize: '1.15rem',
    borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
    paddingBottom: '8px'
  },
  loaderContainer: {
    textAlign: 'center',
    padding: '40px 20px',
    color: '#94a3b8'
  },
  spinner: {
    width: '40px',
    height: '40px',
    border: '4px solid rgba(255, 255, 255, 0.1)',
    borderTop: '4px solid #6366f1',
    borderRadius: '50%',
    margin: '0 auto 16px',
    animation: 'spin 1s linear infinite'
  },
  errorBox: {
    padding: '12px 16px',
    background: 'rgba(239, 68, 68, 0.1)',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    borderRadius: '8px',
    color: '#fca5a5'
  },
  placeholderText: {
    color: '#94a3b8',
    fontStyle: 'italic',
    textAlign: 'center',
    padding: '20px 0',
    margin: 0
  },
  verdictBox: (isChurn) => ({
    padding: '16px',
    borderRadius: '10px',
    textAlign: 'center',
    fontWeight: 700,
    fontSize: '1.1rem',
    backgroundColor: isChurn ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)',
    color: isChurn ? '#fca5a5' : '#a7f3d0',
    border: `1px solid ${isChurn ? 'rgba(239, 68, 68, 0.3)' : 'rgba(16, 185, 129, 0.3)'}`,
    marginBottom: '16px'
  }),
  metricRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '12px',
    paddingBottom: '12px',
    borderBottom: '1px solid rgba(255, 255, 255, 0.08)'
  },
  metricLabel: {
    color: '#cbd5e1',
    fontSize: '0.9rem'
  },
  probabilityDisplay: {
    display: 'flex',
    alignItems: 'baseline',
    gap: '12px'
  },
  probabilityValue: {
    fontSize: '1.8rem',
    fontWeight: 700,
    color: '#38bdf8'
  },
  confidenceInterval: {
    fontSize: '0.85rem',
    color: '#94a3b8'
  },
  riskBadge: (colors) => ({
    padding: '6px 12px',
    borderRadius: '8px',
    backgroundColor: colors.bg,
    color: colors.text,
    border: `1px solid ${colors.border}`,
    fontWeight: 600,
    fontSize: '0.9rem'
  }),
  explainabilitySection: {
    marginTop: '20px',
    paddingTop: '16px',
    borderTop: '1px solid rgba(255, 255, 255, 0.08)'
  },
  subTitle: {
    margin: '0 0 8px',
    color: '#e2e8f0',
    fontSize: '1rem',
    fontWeight: 600
  },
  helperText: {
    color: '#94a3b8',
    fontSize: '0.85rem',
    margin: '0 0 12px',
    lineHeight: 1.5
  },
  featureList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px'
  },
  featureRow: {
    display: 'grid',
    gridTemplateColumns: '140px 1fr 60px',
    gap: '12px',
    alignItems: 'center',
    fontSize: '0.85rem'
  },
  featureNameColumn: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px'
  },
  featureName: {
    color: '#cbd5e1',
    fontWeight: 500,
    textTransform: 'capitalize'
  },
  featureImpact: {
    color: '#94a3b8',
    fontSize: '0.75rem',
    fontStyle: 'italic'
  },
  featureBarContainer: {
    display: 'flex',
    height: '20px',
    background: 'rgba(255, 255, 255, 0.04)',
    borderRadius: '4px',
    overflow: 'hidden'
  },
  featureBar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'width 0.3s ease'
  },
  featureBarValue: {
    color: '#ffffff',
    fontSize: '0.7rem',
    fontWeight: 700,
    textShadow: '0 1px 2px rgba(0, 0, 0, 0.5)'
  },
  featureValue: {
    color: '#94a3b8',
    textAlign: 'right',
    fontWeight: 600
  },
  recommendationBox: (isChurn) => ({
    marginTop: '16px',
    padding: '14px 16px',
    borderRadius: '10px',
    backgroundColor: isChurn ? 'rgba(239, 68, 68, 0.08)' : 'rgba(16, 185, 129, 0.08)',
    border: `1px solid ${isChurn ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)'}`,
    color: isChurn ? '#fca5a5' : '#a7f3d0'
  }),
  recommendationTitle: {
    margin: '0 0 8px',
    fontSize: '0.95rem',
    fontWeight: 600
  },
  recommendationAction: {
    margin: '0 0 6px',
    color: '#f7f8fc',
    fontWeight: 500
  },
  recommendationDesc: {
    margin: 0,
    fontSize: '0.9rem',
    lineHeight: 1.5
  },
  regenerateBtn: {
    width: '100%',
    marginTop: '16px',
    padding: '12px',
    background: '#6366f1',
    color: '#ffffff',
    border: 'none',
    borderRadius: '8px',
    fontWeight: 600,
    cursor: 'pointer',
    fontSize: '0.9rem',
    transition: 'all 0.2s',
    ':hover': { background: '#4f46e5' }
  },

  // Risk Gauge
  gaugeContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '12px',
    padding: '20px',
    background: 'rgba(17, 24, 39, 0.8)',
    borderRadius: '12px'
  },
  gaugeSvg: {
    width: '200px',
    height: '120px'
  },
  gaugeLabel: {
    textAlign: 'center'
  },
  gaugeLabelValue: {
    fontSize: '1.8rem',
    fontWeight: 700,
    color: '#f7f8fc'
  },
  gaugeLabelRisk: {
    fontSize: '0.9rem',
    color: '#94a3b8'
  },

  // Timeline
  timeline: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px'
  },
  timelineEntry: {
    display: 'flex',
    gap: '12px',
    paddingLeft: '12px',
    borderLeft: '2px solid rgba(255, 255, 255, 0.1)',
    paddingBottom: '16px'
  },
  timelineMarker: (colors, isLatest) => ({
    width: '16px',
    height: '16px',
    borderRadius: '50%',
    backgroundColor: colors.text,
    border: `2px solid ${colors.text}`,
    marginTop: '2px',
    boxShadow: isLatest ? `0 0 8px ${colors.text}` : 'none',
    flex: '0 0 16px'
  }),
  timelineContent: {
    flex: 1
  },
  timelineHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '6px'
  },
  timelineTime: {
    fontSize: '0.85rem',
    color: '#94a3b8'
  },
  latestBadge: {
    padding: '2px 8px',
    background: '#6366f1',
    color: '#ffffff',
    borderRadius: '4px',
    fontSize: '0.75rem',
    fontWeight: 600
  },
  timelineMetrics: {
    display: 'flex',
    gap: '16px',
    fontSize: '0.9rem'
  },
  timelineMetric: {
    color: '#cbd5e1'
  }
};

// Add CSS animation
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = `
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  `;
  document.head.appendChild(style);
}
