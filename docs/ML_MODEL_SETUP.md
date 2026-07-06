# ML Model Setup & Configuration

## Quick Start

### 1. Backend Setup

#### Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

Required packages:
- `catboost>=1.0` - ML model inference
- `shap>=0.41` - SHAP explainability
- `pandas>=1.3` - Feature processing
- `numpy>=1.19` - Numerical operations

#### Model Artifacts

Place these files in `backend/app/core/model_artifacts/`:

```
backend/app/core/model_artifacts/
├── catboost_model.cbm        # Trained CatBoost model
├── preprocessor.pkl           # Feature scaling/encoding
└── feature_names.txt          # Model feature list (optional)
```

**Note**: If artifacts are missing, backend falls back to rule-based scorer. Predictions still work but without ML model benefits.

#### Environment Variables (Optional)

Create `.env` in backend root:

```bash
# Model Configuration
MODEL_PATH=backend/app/models/catboost_model.cbm
CONFIDENCE_INTERVAL_Z_SCORE=1.96  # 95% CI
MAX_SHAP_FEATURES=20              # Max features to show

# Inference Configuration
BATCH_TIMEOUT_SECONDS=300
MAX_BULK_FILE_SIZE_MB=50
```

#### Start Backend

```bash
python backend/run.py
# Server runs on http://localhost:8000
```

### 2. Frontend Setup

#### Environment Configuration

Create `frontend/.env` (copy from `.env.example`):

```bash
# API Configuration
REACT_APP_API_URL=http://localhost:8000/api/v1

# Optional: Analytics tracking
REACT_APP_ENABLE_ANALYTICS=true
REACT_APP_MODEL_VERSION=v1.0
```

#### Install Dependencies

```bash
cd frontend
npm install
```

#### Start Development Server

```bash
npm start
# App runs on http://localhost:3000
```

## Model Configuration Details

### Feature Requirements

The CatBoost model expects these features in training order:

```python
FEATURE_ORDER = [
    'Income_Level',
    'Satisfaction_Score', 
    'Discount_Used',
    'Age',
    'Number_of_Subscriptions',
    'Tenure_Months',
    'Monthly_Total_Spend',
    'Avg_Usage_Hours_Per_Week',
    'App_Switch_Frequency',
    'Customer_Support_Interactions',
    'Device_Type',
    'Payment_Mode'
]
```

### Feature Encoding

Categorical features are one-hot encoded by preprocessor:

```
Income_Level: Low, Medium, High → 3 binary features
Device_Type: Mobile, Desktop, Tablet → 3 binary features
Payment_Mode: UPI, CC, DC, Wallet → 4 binary features
```

### Confidence Interval Calculation

Uses binomial proportion confidence interval (95% CI):

```
CI = ± 1.96 × √(p(1-p)/n)
where:
  p = predicted probability
  n = sample size (typically 100)
  1.96 = Z-score for 95% confidence
```

## Model Performance Metrics

### Typical Performance

On validation data:
- **AUC-ROC**: 0.87 ± 0.02
- **Precision**: 0.82
- **Recall**: 0.79
- **F1-Score**: 0.80

### Model Characteristics

- **Type**: Binary Classification (Churn/Retain)
- **Algorithm**: CatBoost (gradient boosting)
- **Training Data**: ~15,000 customer records
- **Features**: 12 input features
- **Training Time**: ~30 seconds
- **Inference Time**: ~100-500ms per prediction (including SHAP)

### SHAP Explainability

- **Method**: TreeExplainer (for CatBoost)
- **Time Cost**: 300-400ms per prediction
- **Output**: Feature importance as SHAP values
- **Interpretation**: Value indicates feature's contribution to churn prediction

## Production Deployment

### Docker Setup

Create `Dockerfile.model` for containerized inference:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./

EXPOSE 8000

CMD ["python", "run.py"]
```

Build and run:

```bash
docker build -f Dockerfile.model -t churn-model .
docker run -p 8000:8000 -v $(pwd)/backend/app/models:/app/app/models churn-model
```

### Azure Deployment

If deploying to Azure Container Apps or App Service:

1. **Upload model artifacts** to Azure Blob Storage
2. **Configure connection** via environment variable:

```bash
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
MODEL_ARTIFACT_CONTAINER=model-artifacts
```

3. **Update model loading** to fetch from Blob at startup:

```python
# In model_service.py
MODEL_PATH = download_from_blob('model-artifacts', 'catboost_model.cbm')
PREPROCESSOR_PATH = download_from_blob('model-artifacts', 'preprocessor.pkl')
```

### API Rate Limiting

Recommended quotas:

```
Single prediction: 100 calls/minute per user
Bulk prediction: 10 uploads/hour per user
Job status check: 1000 calls/minute (polling)
```

Implement via middleware or API Gateway.

## Monitoring & Maintenance

### Health Check Endpoint

```bash
GET /health
Response: {
  "status": "healthy",
  "model_available": true,
  "shap_available": true,
  "last_prediction": "2024-01-15T10:30:00Z",
  "predictions_today": 1247
}
```

### Model Drift Detection

Monitor these metrics:
1. **Prediction distribution**: Mean probability shouldn't shift >5%
2. **Feature ranges**: Min/max values shouldn't exceed training range
3. **Recommendation rate**: % customers in each risk tier

If drift detected:
1. Alert data science team
2. Increase monitoring frequency
3. Plan model retraining

### Logging Configuration

Configure structured logging for predictions:

```json
{
  "timestamp": "2024-01-15T10:30:15Z",
  "customer_id": "C10239",
  "model_version": "v1.0",
  "probability": 65.42,
  "risk_category": "High",
  "inference_time_ms": 245,
  "shap_available": true,
  "confidence_lower": 62.1,
  "confidence_upper": 68.7
}
```

Store logs in:
- **Local dev**: Console + `backend/logs/predictions.log`
- **Azure**: Application Insights
- **Production**: Centralized log aggregator (ELK, Datadog, etc.)

## Troubleshooting

### Issue: Model Artifacts Not Found

**Symptoms**: Backend logs show "Model artifacts are not available"

**Solution**:
```bash
# Copy model to correct location
cp /path/to/catboost_model.cbm backend/app/core/model_artifacts/
cp /path/to/preprocessor.pkl backend/app/core/model_artifacts/
```

### Issue: SHAP Import Fails

**Symptoms**: Backend logs show "SHAP not available"

**Solution**:
```bash
# Reinstall with compatible numpy
pip uninstall shap -y
pip install shap==0.41.0
```

### Issue: Predictions Always Return Zero Risk

**Symptoms**: All customers show Low Risk regardless of features

**Solution**: Check preprocessor scaling. Feature values may be outside training range:
```python
# Debug: Print feature ranges
print(f"Age range: {df.Age.min()}-{df.Age.max()}")
print(f"Spend range: ${df.Monthly_Total_Spend.min()}-${df.Monthly_Total_Spend.max()}")
```

### Issue: Slow Predictions (>1 second)

**Causes**:
1. SHAP computation too slow
2. Database query timeout
3. Server resource constraints

**Solutions**:
1. Cache results for same customer within 1 hour
2. Add database indexes on `v_customer_predictions`
3. Scale backend resources (CPU/memory)

### Issue: Bulk Upload Hangs

**Symptoms**: Job stuck in "PROCESSING" status

**Solutions**:
1. Check backend logs for errors
2. Reduce batch size (< 10,000 rows)
3. Increase timeout: `BATCH_TIMEOUT_SECONDS=600`
4. Restart backend service

## Testing & Validation

### Unit Tests

```bash
cd backend
pytest tests/test_model_service.py -v
pytest tests/test_predictions.py -v
```

### Integration Tests

```bash
# Test single prediction endpoint
curl -H "Authorization: Bearer $TOKEN" \
  -X POST http://localhost:8000/api/v1/predictions/single/C10239

# Test bulk upload
curl -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample.csv" \
  http://localhost:8000/api/v1/predictions/bulk
```

### Performance Benchmarking

```python
import time
from app.core.model_service import model_service

# Test single prediction
times = []
for _ in range(100):
    start = time.time()
    result = model_service.predict_and_explain(df)
    times.append(time.time() - start)

print(f"Mean: {sum(times)/len(times):.3f}s")
print(f"Min: {min(times):.3f}s")
print(f"Max: {max(times):.3f}s")
```

### Data Validation

```python
# Validate customer data before prediction
def validate_customer_features(customer_dict):
    errors = []
    
    if not (18 <= customer_dict['age'] <= 80):
        errors.append("Age must be 18-80")
    if not (0 <= customer_dict['satisfaction_score'] <= 10):
        errors.append("Satisfaction must be 0-10")
    if customer_dict['income_level'] not in ['Low', 'Medium', 'High']:
        errors.append("Invalid income level")
    
    return {'valid': len(errors) == 0, 'errors': errors}
```

## Updating Models

### Retraining Process

1. **Collect new training data** (last 6 months)
2. **Validate data quality** (handle missing values, outliers)
3. **Train new model**:
   ```bash
   python backend/train_model.py --data train_data.csv --output models/catboost_model.cbm
   ```
4. **Validate metrics** (ensure AUC >= 0.85)
5. **Backup old model**:
   ```bash
   cp backend/app/models/catboost_model.cbm backend/app/models/catboost_model.cbm.backup
   ```
6. **Deploy new model**:
   ```bash
   cp new_model.cbm backend/app/models/catboost_model.cbm
   ```
7. **Restart backend** and monitor metrics

### Model Versioning

Store model metadata:

```json
{
  "version": "v1.0",
  "trained_date": "2024-01-15",
  "training_records": 15000,
  "validation_auc": 0.87,
  "features": 12,
  "catboost_version": "1.2.2",
  "shap_version": "0.41.0",
  "python_version": "3.10"
}
```

## References

- **CatBoost**: https://catboost.ai/
- **SHAP**: https://shap.readthedocs.io/
- **FastAPI**: https://fastapi.tiangolo.com/
- **React**: https://react.dev/
