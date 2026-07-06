# ML Model Integration Guide

This document describes the integrated ML model architecture for subscription churn prediction in the dashboard application.

## Overview

The application uses a **CatBoost ML model** to predict customer churn risk with SHAP explainability. The integration spans:

- **Backend**: Model inference, SHAP feature importance, confidence intervals
- **Frontend**: Unified API service, reusable components, real-time predictions
- **Data Flow**: Customer data → Model prediction → Risk stratification → Recommendations

## Architecture

### Backend ML Stack

**Model Service** (`backend/app/core/model_service.py`):
- Loads CatBoost model from `backend/app/models/catboost_model.cbm`
- Loads preprocessor pickle for feature scaling
- Computes SHAP values for local explainability
- Calculates 95% confidence intervals for probability estimates
- Fallback to rule-based scorer if model artifacts unavailable

**Risk Scoring** (`backend/app/core/risk_score.py`):
- Rule-based churn risk calculation
- Risk category derivation (Low/Medium/High)
- Recommendation generation
- Feature explainability via weighted impacts

**API Endpoints** (`backend/app/routers/predictions.py`):
- `/predictions/single/{customer_id}` (POST) - Single prediction with full explainability
- `/predictions/bulk` (POST) - Batch predictions from CSV upload
- `/predictions/bulk/status/{job_id}` (GET) - Job status tracking
- `/predictions/bulk/preview/{job_id}` (GET) - Sample results

**Dashboard Views** (`backend/database/schema.sql`):
- `v_customer_predictions` - View joining customers with latest predictions
- Aggregates KPIs: total customers, churn predictions, revenue at risk

### Frontend ML Integration

#### 1. **ML Model Service** (`frontend/src/services/mlModel.js`)

Provides utility functions for ML operations:

```javascript
// Get single prediction with SHAP
const prediction = await mlModel.getSinglePrediction(customerId);
// Returns: {churn_probability, risk_category, explainability, recommendation_type, ...}

// Format explainability for display
const features = mlModel.formatExplainability(prediction.explainability);
// Returns: [{feature, value, impact, magnitude}, ...] sorted by magnitude

// Get risk colors for UI rendering
const colors = mlModel.getRiskColors(prediction.risk_category);
// Returns: {bg, border, text} for styling

// Validate prediction completeness
const validation = mlModel.validatePrediction(prediction);
// Returns: {isValid, errors, hasExplainability, hasConfidenceInterval}
```

#### 2. **Model Prediction Card** (`frontend/src/components/ModelPredictionCard.jsx`)

Reusable component for displaying predictions:

```jsx
<ModelPredictionCard
  prediction={prediction}
  loading={isLoading}
  error={errorMessage}
  onRegenerate={() => refetchPrediction()}
/>
```

Features:
- Churn probability with 95% confidence interval
- Risk category badge with color coding
- SHAP feature importance bars
- Recommendation action card
- Loading and error states

#### 3. **Risk Visualization Components**

**RiskGauge** - Radial gauge showing probability:
```jsx
<RiskGauge probability={75.5} />
```

**PredictionTimeline** - Historical prediction log:
```jsx
<PredictionTimeline predictions={historyArray} />
```

### Data Models

#### Prediction Response

```json
{
  "customer_id": "C10239",
  "churn_probability": 65.42,
  "probability_confidence_lower": 62.1,
  "probability_confidence_upper": 68.7,
  "risk_category": "High",
  "will_cancel": 1,
  "recommendation_type": "Offer Discount",
  "recommendation_desc": "Apply 20% discount on renewal...",
  "explainability": {
    "Customer_Support_Interactions": 0.523,
    "Satisfaction_Score": -0.412,
    "Avg_Usage_Hours_Per_Week": -0.198,
    "Monthly_Total_Spend": 0.051,
    ...
  }
}
```

#### Explainability Format

SHAP values indicate feature contribution to churn prediction:
- **Positive value**: Feature increases churn risk
- **Negative value**: Feature decreases churn risk
- **Magnitude**: Strength of effect (typically 0-2 range)

Example interpretation:
- Support Interactions +0.523: Each support ticket increases churn probability by ~5.2%
- Satisfaction -0.412: Each satisfaction point decreases churn probability by ~4.1%

## Integration Examples

### Example 1: Load and Display Single Prediction

```javascript
import { useState, useEffect } from 'react';
import * as mlModel from '../services/mlModel';
import { ModelPredictionCard } from '../components/ModelPredictionCard';

function CustomerAnalysis({ customerId }) {
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadPrediction();
  }, [customerId]);

  const loadPrediction = async () => {
    setLoading(true);
    try {
      const data = await mlModel.getSinglePrediction(customerId);
      setPrediction(data);
    } catch (error) {
      console.error('Prediction failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ModelPredictionCard
      prediction={prediction}
      loading={loading}
      onRegenerate={loadPrediction}
    />
  );
}
```

### Example 2: Bulk Predictions with Progress

```javascript
const [bulkFile, setBulkFile] = useState(null);
const [jobId, setJobId] = useState(null);
const [status, setStatus] = useState(null);

const uploadBulkPredictions = async (file) => {
  const result = await mlModel.uploadBulkPredictions(file);
  setJobId(result.job_id);
};

const pollJobStatus = async () => {
  const result = await mlModel.getBulkPredictionStatus(jobId);
  setStatus(result);
  
  if (result.status !== 'COMPLETED') {
    setTimeout(pollJobStatus, 2000); // Poll every 2s
  }
};
```

### Example 3: Feature Importance Visualization

```javascript
function FeatureAnalysis({ prediction }) {
  const features = mlModel.formatExplainability(prediction.explainability);
  
  return (
    <div>
      {features.map(feature => (
        <div key={feature.feature}>
          <span>{feature.feature}</span>
          <ProgressBar 
            value={Math.abs(feature.value)} 
            color={feature.impact === 'increases' ? 'red' : 'green'}
          />
          <span>{feature.value.toFixed(3)}</span>
        </div>
      ))}
    </div>
  );
}
```

## Model Input Features

Required features for prediction:

| Feature | Type | Range | Description |
|---------|------|-------|-------------|
| Age | int | 18-80 | Customer age in years |
| Tenure_Months | int | 1-120 | Subscription duration in months |
| Monthly_Total_Spend | float | 0-500 | Monthly spending in dollars |
| Avg_Usage_Hours_Per_Week | float | 0-168 | Weekly app usage hours |
| Customer_Support_Interactions | int | 0-50 | Number of support tickets |
| Satisfaction_Score | int | 1-10 | Customer satisfaction rating |
| Number_of_Subscriptions | int | 1-5 | Active subscription count |
| Income_Level | string | Low/Medium/High | Customer income bracket |
| Device_Type | string | Mobile/Desktop/Tablet | Primary device |
| Payment_Mode | string | UPI/CC/DC/Wallet | Payment method |
| Discount_Used | bool | true/false | Discount claim history |
| App_Switch_Frequency | int | 0-20 | App switches per hour |

## Risk Categories

The model produces three risk tiers:

### Low Risk (Probability < 30%)
- **Action**: Monitor
- **Description**: Stable engagement, retain with standard service
- **Color**: Green

### Medium Risk (Probability 30-70%)
- **Action**: Subscription Upgrade
- **Description**: Offer premium features to increase engagement
- **Color**: Yellow

### High Risk (Probability ≥ 70%)
- **Action**: Offer Discount
- **Description**: Implement retention strategy (20% discount recommendation)
- **Color**: Red

## Error Handling

### Model Not Available
If CatBoost or SHAP artifacts are missing:
```
Backend → Falls back to rule-based scorer
Frontend → Receives valid prediction (from rule-based model)
User → Sees prediction with [Rule-Based] indicator
```

### Authentication Failures
All ML endpoints require JWT auth. Errors include:
- `401 Unauthorized`: Token invalid/expired
- `403 Forbidden`: User lacks permission

### API Error Codes

| Code | Meaning | Resolution |
|------|---------|-----------|
| 400 | Invalid customer data | Validate input fields match schema |
| 404 | Customer not found | Verify customer ID exists |
| 422 | Missing required fields | Provide all required features |
| 500 | Model inference error | Check backend logs, retry |
| 503 | Service unavailable | Wait and retry |

## Performance Considerations

### Inference Speed
- **Single prediction**: ~100-500ms (model + SHAP)
- **Bulk prediction (100 rows)**: ~10-30s
- **Confidence interval calc**: Included in inference time

### Caching Strategy

Recommendations:
1. **Cache predictions** for 1 hour per customer
2. **Cache model artifacts** in memory (never reload unless restart)
3. **Cache bulk job results** for 24 hours
4. **Don't cache** explainability data (too large)

### Optimization Tips

1. **Batch operations**: Use bulk endpoint instead of N single calls
2. **Async polling**: Don't block UI during bulk processing
3. **Feature validation**: Catch data errors client-side before submission
4. **Lazy loading**: Load SHAP only when detail view shown

## Testing

### Backend Testing

```bash
# Test single prediction
curl -H "Authorization: Bearer $TOKEN" \
  -X POST http://localhost:8000/api/v1/predictions/single/C10239

# Test bulk upload
curl -H "Authorization: Bearer $TOKEN" \
  -F "file=@predictions.csv" \
  http://localhost:8000/api/v1/predictions/bulk
```

### Frontend Testing

```javascript
// Mock prediction for component testing
const mockPrediction = {
  churn_probability: 65.42,
  risk_category: 'High',
  explainability: {
    'Customer_Support_Interactions': 0.523,
    'Satisfaction_Score': -0.412
  },
  recommendation_type: 'Offer Discount'
};
```

## Common Patterns

### Pattern 1: Validation before Prediction

```javascript
const isValidInput = (customer) => {
  return customer.age >= 18 && 
         customer.tenure_months >= 1 &&
         customer.satisfaction_score >= 1;
};
```

### Pattern 2: Risk-Based Actions

```javascript
const executeRetentionAction = (prediction) => {
  switch(prediction.risk_category) {
    case 'High':
      return sendUrgentOffer(prediction.customer_id);
    case 'Medium':
      return suggestUpgrade(prediction.customer_id);
    case 'Low':
      return scheduleNPS(prediction.customer_id);
  }
};
```

### Pattern 3: Confidence-Based UI

```javascript
const shouldShowConfidence = (prediction) => {
  const range = prediction.probability_confidence_upper - 
                prediction.probability_confidence_lower;
  return range < 15; // Show if CI is tight (high confidence)
};
```

## Troubleshooting

### "Model artifacts not available"
- Check: Backend `/app/models/` contains `catboost_model.cbm`
- Check: Backend has `catboost` and `shap` packages installed
- Solution: `pip install catboost shap`

### "SHAP not available"
- Indicates: SHAP library missing or incompatible
- Impact: Predictions work, but explainability unavailable
- Solution: Check backend logs, reinstall SHAP with compatible versions

### Predictions differ from expected
- Possible causes:
  1. Feature values outside training range
  2. Categorical encoding mismatch
  3. Model version mismatch
- Solution: Check backend logs for preprocessing errors

### Bulk job stuck in PROCESSING
- Likely: Large file or backend issue
- Check: Backend logs for errors
- Workaround: Split CSV into smaller batches

## Security Notes

1. **Model Protection**: Store model artifacts outside web-root
2. **Inference Auditing**: Log all predictions for compliance
3. **Data Privacy**: Don't log raw customer features (log IDs only)
4. **Rate Limiting**: Implement quotas on bulk endpoints
5. **Input Validation**: Sanitize all incoming customer data

## Future Enhancements

- [ ] A/B testing framework for recommendation effectiveness
- [ ] Batch retraining pipeline
- [ ] Model versioning and rollback
- [ ] Fairness metrics dashboard
- [ ] Custom SHAP force plots
- [ ] Explainability export to PDF
- [ ] Model monitoring and drift detection
