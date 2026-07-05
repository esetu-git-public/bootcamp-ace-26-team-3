# Prediction Probability Implementation

## Overview

This document describes the churn probability prediction system for the Subscription Cancellation Prediction System. The model generates probability scores that indicate the likelihood of a customer canceling their subscription.

## Probability Format

All probability values are expressed as **percentages in the range 0.0 to 100.0**:
- **0.0**: No churn risk (customer very unlikely to cancel)
- **50.0**: Moderate churn risk (equal likelihood of cancellation)
- **100.0**: Extreme churn risk (customer very likely to cancel)

### API Response Fields

The prediction endpoints return three probability-related fields:

```json
{
  "churn_probability": 85.50,
  "probability_confidence_lower": 80.30,
  "probability_confidence_upper": 90.70,
  ...
}
```

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `churn_probability` | float | 0.0 - 100.0 | Point estimate of churn probability as a percentage |
| `probability_confidence_lower` | float | 0.0 - 100.0 | Lower bound of 95% confidence interval |
| `probability_confidence_upper` | float | 0.0 - 100.0 | Upper bound of 95% confidence interval |

## Calculation Methods

### 1. Machine Learning Model (Primary)

When the CatBoost model is available, probabilities are calculated as:

```
1. Raw prediction: p ∈ [0.0, 1.0] from model.predict_proba()
2. Percentage: probability = p × 100.0
3. Confidence interval: 95% binomial proportion CI
   - z-score = 1.96 (95% confidence level)
   - margin = z × √(p(1-p) / n)
   - lower = max(0.0, probability - margin)
   - upper = min(100.0, probability + margin)
```

### 2. Rule-Based Fallback

If the ML model is unavailable, a rule-based risk profile is used:

**Risk Scoring Algorithm:**
- **Base factors** (each weighted 0-30):
  - Customer support interactions (higher = more risk)
  - Satisfaction score (lower = more risk)
  - Average usage hours (lower = more risk)
- **Adjustment factors** (±5-10%):
  - Tenure months (longer tenure = lower risk)
  - Monthly spend (higher spend = slightly lower risk due to higher engagement cost)

**Confidence bounds for rule-based:**
- ±5% margin (symmetric)
- Example: score=65 → lower=60, upper=70

## Risk Category Mapping

Probabilities are categorized into risk tiers for business actions:

| Risk Category | Probability Range | Will Cancel | Recommended Action |
|---------------|-------------------|-------------|-------------------|
| **Low** | < 30% | No (0) | No Action Required |
| **Medium** | 30% - 70% | Yes (1) | Subscription Upgrade Incentive |
| **High** | ≥ 70% | Yes (1) | Immediate Offer (20% discount) |

## Feature Importance (Explainability)

Each prediction includes SHAP (SHapley Additive exPlanations) feature importance scores:

```json
{
  "explainability": {
    "Customer_Support_Interactions": 0.42,
    "Satisfaction_Score": 0.38,
    "Avg_Usage_Hours_Per_Week": 0.22,
    "Tenure_Months": 0.15,
    "Monthly_Total_Spend": -0.10,
    "Age": -0.05
  }
}
```

**Interpretation:**
- **Positive values**: Increase churn probability
- **Negative values**: Decrease churn probability
- **Magnitude**: Relative importance in the prediction

## API Endpoints

### Single Prediction
```
POST /api/v1/predictions/single/{customer_id}
```

**Response:**
```json
{
  "customer_id": "CUST0001",
  "churn_probability": 85.50,
  "probability_confidence_lower": 80.30,
  "probability_confidence_upper": 90.70,
  "risk_category": "High",
  "will_cancel": 1,
  "explainability": { ... },
  "recommendation_type": "Offer Discount",
  "recommendation_desc": "Apply 20% discount on renewal..."
}
```

### Bulk Predictions
```
POST /api/v1/predictions/bulk
```

Supports batch processing of CSV files with asynchronous job tracking.

### Customer Profile (includes latest prediction)
```
GET /api/v1/customers/{customer_id}
```

Returns customer details with the latest probability prediction and confidence interval.

## Quality Assurance

### Validation Checks
1. **Bounds validation**: All probabilities constrained to [0.0, 100.0]
2. **Confidence interval ordering**: lower ≤ probability ≤ upper
3. **Explainability completeness**: All feature weights present

### Threshold Tuning
Current thresholds (30%, 70%) can be adjusted based on:
- Business cost-benefit analysis
- False positive/negative trade-offs
- Historical churn rate

## Historical Tracking

Predictions are tracked over time for each customer:

```
GET /api/v1/customers/{customer_id}/history
```

Returns historical predictions showing probability trends, enabling trend analysis and model performance monitoring.

## Implementation Details

**Files Modified:**
- `backend/app/core/model_service.py` - Probability calculation
- `backend/app/routers/predictions.py` - Prediction endpoints
- `backend/app/schemas/common.py` - Response models
- `backend/app/routers/customers.py` - Customer profile endpoint

**Database Schema:**
- `churn_predictions` table stores `churn_probability` (0-100 scale)
- `prediction_history` table tracks `risk_score` over time

## Future Enhancements

1. **Model Uncertainty Quantification**: Monte Carlo dropout for better CI estimation
2. **Calibration**: Temperature scaling to improve probability calibration
3. **Dynamic Thresholds**: Business logic to adjust risk thresholds per segment
4. **Probability Distributions**: Return full distributions instead of point estimates
