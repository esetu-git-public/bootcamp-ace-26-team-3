/**
 * ML Model Service
 * Centralized service for all machine learning model predictions and explainability.
 * 
 * Features:
 * - Single prediction with SHAP explainability
 * - Bulk predictions with job management
 * - Model performance metrics
 * - Feature importance analysis
 * - Prediction confidence intervals
 * - Risk stratification and recommendations
 */

import * as apiService from './api';
import { formatPercent } from '../utils/percent';

/**
 * Get single customer churn prediction with SHAP explainability
 * @param {string} customerId - Customer ID to predict
 * @returns {Promise<object>} Prediction with churn_probability, risk_category, explainability, recommendation
 */
export async function getSinglePrediction(customerId) {
  return apiService.runSinglePrediction(customerId);
}

/**
 * Get customer prediction history (audit log of model runs)
 * @param {string} customerId - Customer ID
 * @returns {Promise<array>} Array of historical predictions with timestamps
 */
export async function getPredictionHistory(customerId) {
  return apiService.getCustomerPredictionHistory(customerId);
}

/**
 * Upload bulk predictions CSV file
 * @param {File} file - CSV file with customer data
 * @returns {Promise<object>} Job ID and status for bulk prediction tracking
 */
export async function uploadBulkPredictions(file) {
  return apiService.uploadBulkPredictions(file);
}

/**
 * Get status of bulk prediction job
 * @param {string} jobId - Job ID from bulk upload
 * @returns {Promise<object>} Job status, progress, and processing info
 */
export async function getBulkPredictionStatus(jobId) {
  return apiService.getBulkPredictionStatus(jobId);
}

/**
 * Get preview of bulk prediction results (first N rows)
 * @param {string} jobId - Job ID from bulk upload
 * @returns {Promise<object>} Preview rows showing sample predictions
 */
export async function getBulkPredictionPreview(jobId) {
  return apiService.getBulkPredictionPreview(jobId);
}

/**
 * Parse risk score into human-readable category
 * @param {number} probability - Churn probability (0-100)
 * @returns {string} Risk category: 'Low', 'Medium', or 'High'
 */
export function getRiskCategory(probability) {
  if (probability >= 70) return 'High';
  if (probability >= 30) return 'Medium';
  return 'Low';
}

/**
 * Get color for risk category for UI display
 * @param {string} category - Risk category
 * @returns {object} Color codes for risk visualization
 */
export function getRiskColors(category) {
  switch (category) {
    case 'High':
      return { bg: 'rgba(239,68,68,0.1)', border: 'rgba(239,68,68,0.3)', text: '#fca5a5' };
    case 'Medium':
      return { bg: 'rgba(251,191,36,0.1)', border: 'rgba(251,191,36,0.3)', text: '#fcd34d' };
    case 'Low':
      return { bg: 'rgba(16,185,129,0.1)', border: 'rgba(16,185,129,0.3)', text: '#a7f3d0' };
    default:
      return { bg: 'rgba(100,116,139,0.1)', border: 'rgba(100,116,139,0.3)', text: '#cbd5e1' };
  }
}

/**
 * Format SHAP explainability values for display
 * @param {object} explainability - Raw SHAP values from model
 * @returns {array} Formatted array with feature names and values for display
 */
export function formatExplainability(explainability) {
  if (!explainability || typeof explainability !== 'object') {
    return [];
  }

  return Object.entries(explainability)
    .map(([feature, value]) => ({
      feature: feature.replace(/_/g, ' '),
      originalFeature: feature,
      value: parseFloat(value),
      impact: value > 0 ? 'increases' : value < 0 ? 'decreases' : 'neutral',
      magnitude: Math.abs(value)
    }))
    .sort((a, b) => b.magnitude - a.magnitude);
}

/**
 * Interpret SHAP value impact on model output
 * @param {number} value - SHAP value
 * @returns {string} Human-readable interpretation
 */
export function interpretSHAPValue(value) {
  const absVal = Math.abs(value);
  if (absVal < 0.1) return 'minimal effect';
  if (absVal < 0.5) return 'weak effect';
  if (absVal < 1.0) return 'moderate effect';
  if (absVal < 2.0) return 'strong effect';
  return 'very strong effect';
}

/**
 * Calculate confidence interval bounds for display
 * @param {number} probability - Predicted probability
 * @param {number} lowerBound - Confidence interval lower bound
 * @param {number} upperBound - Confidence interval upper bound
 * @returns {object} Formatted bounds with percentage values
 */
export function formatConfidenceInterval(probability, lowerBound, upperBound) {
  return {
    point: formatPercent(probability, 2).replace('%', ''),
    lower: formatPercent(lowerBound, 2).replace('%', ''),
    upper: formatPercent(upperBound, 2).replace('%', ''),
    range: `${formatPercent(lowerBound, 2)} - ${formatPercent(upperBound, 2)}`
  };
}

/**
 * Get recommendation based on churn probability
 * @param {number} probability - Churn probability (0-100)
 * @returns {object} Recommended action type and description
 */
export function getRecommendation(probability) {
  if (probability >= 70) {
    return {
      type: 'Urgent Intervention',
      action: 'Offer Discount',
      description: 'Apply 20% discount on renewal to mitigate high interaction friction.',
      priority: 'critical'
    };
  }
  if (probability >= 30) {
    return {
      type: 'Proactive Engagement',
      action: 'Subscription Upgrade',
      description: 'Provide subscription upgrade incentive for premium benefits.',
      priority: 'high'
    };
  }
  return {
    type: 'Retention Monitor',
    action: 'No Action Required',
    description: 'Customer behavior shows stable engagement.',
    priority: 'low'
  };
}

/**
 * Validate prediction data for completeness
 * @param {object} prediction - Prediction object
 * @returns {object} Validation result with isValid flag and errors
 */
export function validatePrediction(prediction) {
  const errors = [];

  if (prediction.churn_probability === undefined || prediction.churn_probability === null) {
    errors.push('Missing churn probability');
  }
  if (!prediction.risk_category) {
    errors.push('Missing risk category');
  }
  if (!prediction.recommendation_type) {
    errors.push('Missing recommendation');
  }

  return {
    isValid: errors.length === 0,
    errors,
    hasExplainability: !!prediction.explainability,
    hasConfidenceInterval: prediction.probability_confidence_lower !== undefined && prediction.probability_confidence_upper !== undefined
  };
}

/**
 * Format prediction data for API submission
 * @param {object} customerData - Raw customer data
 * @returns {object} Formatted data for model input
 */
export function formatPredictionInput(customerData) {
  return {
    customer_id: customerData.customer_id,
    age: parseInt(customerData.age) || 35,
    tenure_months: parseInt(customerData.tenure_months) || 12,
    monthly_total_spend: parseFloat(customerData.monthly_total_spend) || 75.0,
    avg_usage_hours_per_week: parseFloat(customerData.avg_usage_hours_per_week) || 15.0,
    customer_support_interactions: parseInt(customerData.customer_support_interactions) || 3,
    satisfaction_score: parseInt(customerData.satisfaction_score) || 3,
    number_of_subscriptions: parseInt(customerData.number_of_subscriptions) || 1,
    income_level: customerData.income_level || 'Medium',
    device_type: customerData.device_type || 'Mobile',
    payment_mode: customerData.payment_mode || 'UPI',
    discount_used: !!customerData.discount_used,
    app_switch_frequency: parseInt(customerData.app_switch_frequency) || 5
  };
}

/**
 * Compare two predictions to identify risk changes
 * @param {object} currentPrediction - Latest prediction
 * @param {object} previousPrediction - Prior prediction
 * @returns {object} Comparison metrics and trends
 */
export function comparePredictions(currentPrediction, previousPrediction) {
  if (!previousPrediction) {
    return {
      riskTrend: 'new',
      probabilityChange: 0,
      categoryChanged: false
    };
  }

  const probChange = (currentPrediction.churn_probability || 0) - (previousPrediction.churn_probability || 0);
  const categoryChanged = currentPrediction.risk_category !== previousPrediction.risk_category;

  let riskTrend = 'stable';
  if (probChange > 5) riskTrend = 'increasing';
  if (probChange < -5) riskTrend = 'decreasing';

  return {
    riskTrend,
    probabilityChange: probChange.toFixed(2),
    categoryChanged,
    previousCategory: previousPrediction.risk_category,
    currentCategory: currentPrediction.risk_category
  };
}

/**
 * Aggregate predictions for cohort analysis
 * @param {array} predictions - Array of individual predictions
 * @returns {object} Aggregate metrics for the cohort
 */
export function aggregatePredictions(predictions) {
  if (!predictions || predictions.length === 0) {
    return {
      totalCount: 0,
      highRiskCount: 0,
      mediumRiskCount: 0,
      lowRiskCount: 0,
      averageProbability: 0,
      highRiskPercentage: 0
    };
  }

  const highRiskCount = predictions.filter(p => p.risk_category === 'High').length;
  const mediumRiskCount = predictions.filter(p => p.risk_category === 'Medium').length;
  const lowRiskCount = predictions.filter(p => p.risk_category === 'Low').length;
  const averageProbability = predictions.reduce((sum, p) => sum + (p.churn_probability || 0), 0) / predictions.length;

  return {
    totalCount: predictions.length,
    highRiskCount,
    mediumRiskCount,
    lowRiskCount,
    averageProbability: averageProbability.toFixed(2),
    highRiskPercentage: ((highRiskCount / predictions.length) * 100).toFixed(1)
  };
}
