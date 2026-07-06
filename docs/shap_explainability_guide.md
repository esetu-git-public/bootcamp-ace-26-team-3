# SHAP Explainability Implementation Guide

## Overview

This document describes the SHAP (SHapley Additive exPlanations) explainability implementation for the subscription churn prediction model. SHAP provides unified measure of feature importance based on cooperative game theory, enabling local and global model explanations.

## Architecture

### Core Components

#### 1. **SHAPExplainer** (`backend/app/core/shap_explainer.py`)
Advanced SHAP explainer wrapper providing:
- **Local Explanations**: Feature contributions for individual predictions
- **Global Feature Importance**: Mean absolute SHAP values across dataset
- **Feature Interaction Analysis**: Correlation between SHAP values of feature pairs
- **Summary Statistics**: Detailed SHAP value statistics per feature

Key Methods:
- `explain_prediction()`: Generate local SHAP explanations
- `global_feature_importance()`: Calculate global feature importance
- `feature_interaction_analysis()`: Analyze feature interactions
- `summary_statistics()`: Get SHAP statistics for dataset

#### 2. **SHAPVisualizer** (`backend/app/core/shap_visualizer.py`)
Creates visualization-ready data structures for:
- **Force Plots**: Show positive/negative feature contributions
- **Decision Plots**: Cumulative SHAP contribution path
- **Waterfall Plots**: Ordered feature impact visualization
- **Feature Importance Charts**: Bar charts of global importance
- **Matplotlib Plots**: Generate base64-encoded plot images

#### 3. **ModelService** (`backend/app/core/model_service.py`)
Enhanced with:
- Integration with `SHAPExplainer`
- `predict_with_advanced_explanation()`: Return detailed SHAP explanations
- `get_global_importance()`: Fetch global feature importance
- `get_feature_interaction()`: Get feature interaction analysis
- `get_shap_summary_statistics()`: Get SHAP statistics

#### 4. **Explainability Router** (`backend/app/api/endpoints/explainability.py`)
RESTful endpoints for SHAP functionality:
- `POST /api/v1/explainability/explain-prediction/{customer_id}`: Local explanation
- `GET /api/v1/explainability/feature-importance`: Global importance
- `GET /api/v1/explainability/feature-interaction`: Feature interaction analysis
- `POST /api/v1/explainability/interactive-explanation/{customer_id}`: Interactive explanation
- `GET /api/v1/explainability/available-features`: Available features list

## Usage Examples

### 1. Getting Local Explanations

Get SHAP explanation for a specific customer:

```bash
curl -X POST "http://localhost:8000/api/v1/explainability/explain-prediction/CUST_123" \
  -H "Authorization: Bearer <token>"
```

Response:
```json
{
  "customer_id": "CUST_123",
  "probability": 0.75,
  "prediction": "churn",
  "base_value": 0.45,
  "feature_contributions": [
    {
      "feature": "Satisfaction_Score",
      "shap_value": -0.15,
      "abs_shap_value": 0.15,
      "direction": "negative",
      "original_value": 2
    },
    {
      "feature": "Customer_Support_Interactions",
      "shap_value": 0.12,
      "abs_shap_value": 0.12,
      "direction": "positive",
      "original_value": 5
    }
  ]
}
```

**Interpretation**: 
- Base model prediction: 45% churn probability
- Satisfaction Score (2/5) **decreases** churn probability by 15 percentage points
- Customer Support interactions **increase** churn probability by 12 percentage points
- Final prediction: 75% churn probability

### 2. Getting Global Feature Importance

Understand which features are globally most important:

```bash
curl -X GET "http://localhost:8000/api/v1/explainability/feature-importance?top_n=5" \
  -H "Authorization: Bearer <token>"
```

Response:
```json
{
  "global_importance": [
    {
      "feature": "Satisfaction_Score",
      "mean_abs_shap": 0.18
    },
    {
      "feature": "Monthly_Total_Spend",
      "mean_abs_shap": 0.14
    },
    {
      "feature": "Customer_Support_Interactions",
      "mean_abs_shap": 0.12
    },
    {
      "feature": "Tenure_Months",
      "mean_abs_shap": 0.08
    },
    {
      "feature": "Age",
      "mean_abs_shap": 0.06
    }
  ],
  "base_value": 0.45,
  "importance_percentiles": {
    "min": 0.02,
    "max": 0.25,
    "mean": 0.1,
    "median": 0.09
  }
}
```

**Interpretation**: Satisfaction Score is the most important feature globally, followed by spending patterns.

### 3. Feature Interaction Analysis

Analyze how two features interact in their effect on churn:

```bash
curl -X GET "http://localhost:8000/api/v1/explainability/feature-interaction" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "feature1": "Satisfaction_Score",
    "feature2": "Customer_Support_Interactions"
  }'
```

Response:
```json
{
  "feature1": "Satisfaction_Score",
  "feature2": "Customer_Support_Interactions",
  "shap_correlation": 0.65,
  "interpretation": "Strong interaction"
}
```

**Interpretation**: These features have a strong interaction - when one increases in its effect, the other tends to as well.

### 4. Interactive Explanations

Get comprehensive visualization data for frontend display:

```bash
curl -X POST "http://localhost:8000/api/v1/explainability/interactive-explanation/CUST_123" \
  -H "Authorization: Bearer <token>"
```

Response includes:
```json
{
  "customer_id": "CUST_123",
  "explanation": {
    "prediction": {
      "probability": 0.75,
      "class": "churn",
      "confidence": 0.75
    },
    "force_plot": { ... },
    "decision_plot": { ... },
    "waterfall_plot": { ... },
    "feature_importance": { ... },
    "summary": "This customer has a 75.0% churn probability..."
  }
}
```

## Understanding SHAP Values

### What are SHAP values?
SHAP values represent the contribution of each feature to moving the prediction from the base value to the actual prediction. They are based on Shapley values from cooperative game theory.

### Interpretation

1. **Positive SHAP value**: Feature increases churn probability
2. **Negative SHAP value**: Feature decreases churn probability
3. **Magnitude**: Larger absolute values indicate stronger influence

### Base Value
The base value is the model's expected output before considering any features. It represents the average prediction across the training data.

## Visualization Types

### 1. Force Plot
Shows which features push the prediction up (positive) and down (negative).
- **Use case**: Understanding individual predictions
- **Data structure**: `force_plot` in response

### 2. Decision Plot
Shows the cumulative effect of features, creating a decision path from base value to prediction.
- **Use case**: Following the decision path step-by-step
- **Data structure**: `decision_plot` in response

### 3. Waterfall Plot
Shows the top contributing features in order of impact.
- **Use case**: Explaining to non-technical stakeholders
- **Data structure**: `waterfall_plot` in response

### 4. Feature Importance Chart
Global bar chart showing average importance of each feature.
- **Use case**: Understanding model behavior at scale
- **Use case**: Identifying which features matter most

## Integration Example (Python)

```python
import pandas as pd
from backend.app.core.model_service import model_service

# Load customer data
customer_data = {
    "income_level": "High",
    "satisfaction_score": 2,
    "discount_used": False,
    "age": 35,
    "number_of_subscriptions": 2,
    "tenure_months": 24,
    "monthly_total_spend": 120.0,
    "avg_usage_hours_per_week": 8.0,
    "app_switch_frequency": 3,
    "customer_support_interactions": 4,
    "device_type": "Desktop",
    "payment_mode": "Credit Card"
}

# Get advanced explanation
df = pd.DataFrame([customer_data])
explanation = model_service.predict_with_advanced_explanation(df)

# Print results
print(f"Churn Probability: {explanation['probability']:.2%}")
print(f"Base Value: {explanation['base_value']:.2%}")
print("\nTop Contributing Factors:")
for contrib in explanation['feature_contributions'][:3]:
    print(f"  {contrib['feature']}: {contrib['shap_value']:+.4f}")
```

## Best Practices

### 1. **Monitoring SHAP Values**
Track SHAP values over time to detect model drift:
```python
# Monitor global importance regularly
importance = model_service.get_global_importance(recent_data)
```

### 2. **Feature Engineering Insights**
Use SHAP to guide feature engineering:
- Features with low importance might be candidates for removal
- Features with strong interactions might benefit from interaction terms

### 3. **Model Debugging**
Use SHAP to identify model issues:
- Unexpected SHAP values for "obvious" cases
- Non-intuitive feature importance rankings

### 4. **Customer Communication**
Use SHAP visualizations in customer-facing reports:
- Explain why a customer has high churn risk
- Show what factors can improve retention

## Advanced Features

### Custom Explainer Initialization

```python
from backend.app.core.shap_explainer import SHAPExplainer, load_explainer_from_artifacts

# Initialize from model artifacts
explainer = load_explainer_from_artifacts(
    preprocessor_path="path/to/preprocessor.pkl",
    model=model
)

# Or create directly
explainer = SHAPExplainer(model, preprocessor, feature_names)
```

### Generating Matplotlib Plots

```python
from backend.app.core.shap_visualizer import SHAPVisualizer

# Generate base64-encoded plot
plot_image = SHAPVisualizer.generate_matplotlib_plot(
    plot_type="bar",
    explainer_base_value=0.45,
    shap_values=shap_values,
    feature_names=feature_names
)

# Use in HTML
html = f'<img src="{plot_image}" />'
```

## Performance Considerations

1. **SHAP Calculation**: O(n*m) where n = samples, m = features
2. **Global Importance**: Requires computing SHAP for entire dataset
3. **Caching**: Consider caching global importance (updated daily/weekly)
4. **Background Data**: Larger background datasets (1000+) improve approximation quality

## Troubleshooting

### Issue: "SHAP explainer not initialized"
**Solution**: Ensure model artifacts are properly loaded:
```python
if model_service.is_ready and model_service.shap_explainer is not None:
    # Safe to use SHAP
```

### Issue: Memory errors with large datasets
**Solution**: Sample background data:
```python
# Use subset for importance calculation
sample_data = processed_features.sample(n=500, random_state=42)
importance = model_service.get_global_importance(sample_data)
```

### Issue: Slow SHAP computation
**Solution**: 
- Use fewer samples for background data
- Cache global importance values
- Consider approximate SHAP (KernelExplainer) if TreeExplainer is too slow

## Files Overview

```
backend/app/
├── core/
│   ├── shap_explainer.py       # Advanced SHAP explainer
│   ├── shap_visualizer.py      # Visualization utilities
│   └── model_service.py        # Updated ModelService
├── api/
│   └── endpoints/
│       └── explainability.py   # SHAP API endpoints
└── main.py                      # Updated with explainability router
```

## Future Enhancements

1. **SHAP Interaction Plots**: Visualize feature interactions
2. **Partial Dependence Plots**: Show marginal effect of features
3. **Individual Conditional Expectation (ICE) Plots**: Feature effect across instances
4. **LIME Comparison**: Hybrid SHAP+LIME explanations
5. **Explanation Caching**: Pre-computed explanations for frequent queries
6. **Time-based SHAP**: SHAP values over time for temporal analysis

## References

- [SHAP Documentation](https://shap.readthedocs.io/)
- [Lundberg & Lee (2017)](https://arxiv.org/abs/1705.07874): "A Unified Approach to Interpreting Model Predictions"
- [CatBoost TreeExplainer](https://catboost.ai/)

---

**Last Updated**: 2024
**SHAP Version**: 0.45.1
**Status**: Production-Ready
