# SHAP Explainability API Quick Reference

## Endpoints Overview

### 1. Local Explanation Endpoint
**Get detailed SHAP explanation for a customer's prediction**

```
POST /api/v1/explainability/explain-prediction/{customer_id}
```

**Authentication**: Required (Bearer Token)

**Response**:
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
    }
  ]
}
```

**Example cURL**:
```bash
curl -X POST "http://localhost:8000/api/v1/explainability/explain-prediction/CUST_001" \
  -H "Authorization: Bearer eyJhbGc..."
```

---

### 2. Global Feature Importance Endpoint
**Get most important features across all customers**

```
GET /api/v1/explainability/feature-importance?top_n=10
```

**Query Parameters**:
- `top_n` (optional, default=10): Number of top features to return (1-50)

**Response**:
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
    }
  ],
  "total_features": 12,
  "base_value": 0.45,
  "importance_percentiles": {
    "min": 0.02,
    "max": 0.25,
    "mean": 0.1,
    "median": 0.09
  }
}
```

**Example cURL**:
```bash
curl -X GET "http://localhost:8000/api/v1/explainability/feature-importance?top_n=5" \
  -H "Authorization: Bearer eyJhbGc..."
```

---

### 3. Feature Interaction Analysis Endpoint
**Analyze how two features interact in their effect on churn**

```
GET /api/v1/explainability/feature-interaction?feature1=<name>&feature2=<name>
```

**Query Parameters**:
- `feature1` (required): Name of first feature
- `feature2` (required): Name of second feature

**Response**:
```json
{
  "feature1": "Satisfaction_Score",
  "feature2": "Customer_Support_Interactions",
  "shap_correlation": 0.65,
  "interpretation": "Strong interaction"
}
```

**Example cURL**:
```bash
curl -X GET "http://localhost:8000/api/v1/explainability/feature-interaction?feature1=Satisfaction_Score&feature2=Customer_Support_Interactions" \
  -H "Authorization: Bearer eyJhbGc..."
```

---

### 4. Interactive Explanation Endpoint
**Generate comprehensive visualization data**

```
POST /api/v1/explainability/interactive-explanation/{customer_id}
```

**Response**:
```json
{
  "customer_id": "CUST_123",
  "explanation": {
    "prediction": {
      "probability": 0.75,
      "class": "churn",
      "confidence": 0.75
    },
    "force_plot": {
      "base_value": 0.45,
      "prediction_value": 0.75,
      "positive_features": [...],
      "negative_features": [...]
    },
    "decision_plot": {
      "base_value": 0.45,
      "final_value": 0.75,
      "decision_path": [...]
    },
    "waterfall_plot": {
      "waterfall_steps": [...],
      "final_value": 0.75
    },
    "summary": "This customer has a 75.0% churn probability..."
  }
}
```

**Example cURL**:
```bash
curl -X POST "http://localhost:8000/api/v1/explainability/interactive-explanation/CUST_001" \
  -H "Authorization: Bearer eyJhbGc..."
```

---

### 5. Available Features Endpoint
**Get list of all available features for analysis**

```
GET /api/v1/explainability/available-features
```

**Response**:
```json
{
  "features": [
    {
      "name": "Satisfaction_Score",
      "available_for_interaction": true
    },
    {
      "name": "Monthly_Total_Spend",
      "available_for_interaction": true
    }
  ],
  "total_features": 12
}
```

**Example cURL**:
```bash
curl -X GET "http://localhost:8000/api/v1/explainability/available-features" \
  -H "Authorization: Bearer eyJhbGc..."
```

---

## Response Data Structures

### Feature Contribution Object
```json
{
  "feature": "Feature_Name",
  "shap_value": -0.15,           // Signed SHAP value
  "abs_shap_value": 0.15,        // Absolute SHAP value
  "direction": "negative",        // "positive", "negative", or "neutral"
  "original_value": 2             // Customer's actual feature value
}
```

### Force Plot Object
```json
{
  "base_value": 0.45,            // Model's baseline prediction
  "prediction_value": 0.75,      // Final prediction
  "positive_features": [
    {
      "feature": "Feature_A",
      "shap_value": 0.12,
      "feature_value": "123"
    }
  ],
  "negative_features": [
    {
      "feature": "Feature_B",
      "shap_value": -0.10,
      "feature_value": "2"
    }
  ]
}
```

### Decision Path Object
```json
{
  "base_value": 0.45,
  "final_value": 0.75,
  "decision_path": [
    {
      "step": 0,
      "feature": "Feature_A",
      "shap_value": 0.08,
      "cumulative_value": 0.53,
      "direction": "up",
      "feature_value": "100"
    }
  ]
}
```

### Waterfall Plot Object
```json
{
  "waterfall_steps": [
    {
      "step": "Base Value",
      "value": 0.45,
      "cumulative": 0.45,
      "type": "base"
    },
    {
      "step": "Feature_A",
      "value": 0.12,
      "cumulative": 0.57,
      "type": "positive"
    }
  ],
  "final_value": 0.75
}
```

---

## Code Examples

### JavaScript/React Example
```javascript
async function getCustomerExplanation(customerId, token) {
  const response = await fetch(
    `http://localhost:8000/api/v1/explainability/explain-prediction/${customerId}`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    }
  );
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  
  return response.json();
}

// Usage
const explanation = await getCustomerExplanation('CUST_001', authToken);
console.log(`Churn Probability: ${(explanation.probability * 100).toFixed(1)}%`);

// Display top factors
explanation.feature_contributions.slice(0, 3).forEach(contrib => {
  console.log(`${contrib.feature}: ${contrib.shap_value.toFixed(4)}`);
});
```

### Python Example
```python
import requests

def get_global_importance(token, top_n=10):
    """Get global feature importance from API."""
    headers = {'Authorization': f'Bearer {token}'}
    params = {'top_n': top_n}
    
    response = requests.get(
        'http://localhost:8000/api/v1/explainability/feature-importance',
        headers=headers,
        params=params
    )
    
    response.raise_for_status()
    return response.json()

# Usage
importance = get_global_importance(token)
for item in importance['global_importance']:
    print(f"{item['feature']}: {item['mean_abs_shap']:.4f}")
```

---

## Error Handling

### 503 Service Unavailable
```json
{
  "detail": "Model service not ready"
}
```
**Cause**: Model or SHAP explainer not initialized
**Solution**: Ensure model artifacts are loaded

### 404 Not Found
```json
{
  "detail": "Customer not found"
}
```
**Cause**: Customer ID doesn't exist in database
**Solution**: Check customer ID

### 400 Bad Request
```json
{
  "detail": "Insufficient customer data for analysis"
}
```
**Cause**: Not enough data for the requested analysis
**Solution**: Ensure database has sufficient customer records

### 500 Internal Server Error
```json
{
  "detail": "Explanation failed: <error message>"
}
```
**Cause**: Internal server error during processing
**Solution**: Check server logs for details

---

## Rate Limiting & Performance

- **Global Importance**: ~1-2 seconds (calls entire customer database)
- **Local Explanation**: ~100-500ms (single customer)
- **Feature Interaction**: ~2-5 seconds (sample of 500 customers)
- **Interactive Explanation**: ~1-2 seconds (combines multiple computations)

### Optimization Tips

1. **Cache global importance** - Update daily/weekly instead of on-demand
2. **Batch explanations** - Process multiple customers in parallel
3. **Limit top_n** - Return fewer features for faster responses
4. **Use sampling** - For large datasets, sample before computing global importance

---

## Integration Patterns

### Pattern 1: Display in Customer Profile
```javascript
// When showing customer details
const explanation = await getExplanation(customerId);
displayChurnRisk(explanation.probability);
displayTopFactors(explanation.feature_contributions.slice(0, 3));
```

### Pattern 2: Export Report
```python
# Generate explanation for report
explanation = api.get_explanation(customer_id)
report = f"""
Customer {customer_id}
Churn Probability: {explanation['probability']:.1%}
Base Prediction: {explanation['base_value']:.1%}

Key Factors:
{format_contributions(explanation['feature_contributions'][:5])}
"""
```

### Pattern 3: Batch Analysis
```python
# Analyze multiple customers
for customer_id in customer_ids:
    try:
        exp = api.get_explanation(customer_id)
        save_to_db(customer_id, exp)
    except Exception as e:
        log_error(customer_id, e)
```

---

## Testing the API

### Using Postman
1. Import the API collection
2. Set Bearer token in Authorization tab
3. Test each endpoint with sample customer IDs

### Using Swagger UI
1. Navigate to `http://localhost:8000/api/docs`
2. Click "Try it out" on each endpoint
3. Provide required parameters and test

### Using Python Requests
```python
import requests

base_url = 'http://localhost:8000/api/v1'
token = 'your_token_here'
headers = {'Authorization': f'Bearer {token}'}

# Test local explanation
response = requests.post(
    f'{base_url}/explainability/explain-prediction/CUST_001',
    headers=headers
)
print(response.json())

# Test feature importance
response = requests.get(
    f'{base_url}/explainability/feature-importance',
    headers=headers,
    params={'top_n': 5}
)
print(response.json())
```

---

## Best Practices

1. **Always include authentication** - All endpoints require Bearer token
2. **Handle errors gracefully** - Implement retry logic for network failures
3. **Cache when possible** - Don't fetch the same explanation repeatedly
4. **Monitor performance** - Track response times for optimization
5. **Validate inputs** - Check feature names exist before querying
6. **Document integrations** - Keep track of which systems use which endpoints

---

**Last Updated**: 2024
**API Version**: 1.0
**Status**: Production-Ready
