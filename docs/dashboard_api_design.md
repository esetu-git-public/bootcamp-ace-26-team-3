# FastAPI Dashboard API Design Specification

This document provides the API architecture, route definitions, and data contracts (Pydantic models) for the **Subscription Cancellation Prediction System** backend.

All endpoints are versioned under the `/api/v1` prefix. Unless otherwise specified, all endpoints require a valid JSON Web Token (JWT) passed in the HTTP Authorization header.

## 1. Authentication & Security

The system uses JWT-based authentication for state management and route protection. 

* **Auth Scheme**: OAuth2 Password Bearer (Bearer Token).
* **Header Format**: `Authorization: Bearer <JWT_TOKEN>`

### Data Models
```python
from pydantic import BaseModel, Field
from typing import Optional

class LoginRequest(BaseModel):
    username: str = Field(..., example="admin")
    password: str = Field(..., example="SecurePassword123")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # Token duration in seconds
```

### Endpoints
#### `POST /api/v1/auth/login`
- **Description**: Authenticates administrator credentials and returns a JWT token.
- **Authentication**: None (Public)
- **Request Body**: `LoginRequest`
- **Responses**:
  - `200 OK`: Returns `TokenResponse`
  - `401 Unauthorized`: Invalid credentials

---

## 2. Executive Dashboard KPIs

### Data Models
```python
class DashboardKPIsResponse(BaseModel):
    total_customers: int = Field(..., description="Total count of active customer profiles")
    predicted_churn_customers: int = Field(..., description="Total customers flagged as likely to cancel (will_cancel = 1)")
    high_risk_customers: int = Field(..., description="Total customers in High Churn Risk category")
    average_churn_risk: float = Field(..., description="Mean churn probability score as percentage (0.0 - 100.0)")
    average_satisfaction: float = Field(..., description="Mean satisfaction score (1.0 - 5.0)")
    average_monthly_spend: float = Field(..., description="Mean monthly customer spend in USD")
    average_tenure_months: float = Field(..., description="Mean customer tenure in months")
    monthly_revenue_at_risk: float = Field(..., description="Total spend of all customers predicted to churn")
```

### Endpoints
#### `GET /api/v1/dashboard/kpis`
- **Description**: Retrieves high-level business analytics summaries. Used for the metric grid at the top of the dashboard.
- **Responses**:
  - `200 OK`: Returns `DashboardKPIsResponse`

---

## 3. Business Analytics & Visualizations

These endpoints provide aggregated statistics optimized for charting packages (Recharts, Chart.js).

### Data Models
```python
from typing import List

class RiskBucket(BaseModel):
    risk_category: str  # 'Low', 'Medium', 'High'
    customer_count: int
    percentage: float

class IncomeChurnRate(BaseModel):
    income_level: str  # 'Low', 'Medium', 'High'
    total_customers: int
    churn_customers: int
    churn_rate: float

class DeviceChurnRate(BaseModel):
    device_type: str  # 'Mobile', 'Tablet', 'Desktop', 'Smart TV'
    total_customers: int
    churn_customers: int
    churn_rate: float

class PaymentChurnRate(BaseModel):
    payment_mode: str  # 'Credit Card', 'Debit Card', 'Net Banking', 'UPI', 'Digital Wallet'
    total_customers: int
    churn_customers: int
    churn_rate: float

class SpendBucketChurn(BaseModel):
    spend_bucket: str  # e.g., 'Under $20', '$20 - $50', etc.
    total_customers: int
    churn_customers: int
    churn_rate: float

class TenureBucketChurn(BaseModel):
    tenure_bucket: str  # e.g., '0-3 Months (New)', '12+ Months (Loyal)', etc.
    total_customers: int
    churn_customers: int
    churn_rate: float

class SatisfactionChurnRate(BaseModel):
    satisfaction_score: int  # 1 to 5
    total_customers: int
    churn_customers: int
    churn_rate: float
    avg_support_interactions: float

class SegmentStats(BaseModel):
    segment: str  # 'High Risk', 'Loyal', 'Premium', 'Budget', 'Standard'
    customer_count: int
    percentage: float
    average_churn_risk: float
```

### Endpoints
#### `GET /api/v1/analytics/churn-risk-distribution`
- **Description**: Returns the breakdown of customers across Churn Risk Categories.
- **Responses**:
  - `200 OK`: `List[RiskBucket]`

#### `GET /api/v1/analytics/churn-by-income`
- **Description**: Returns churn rates grouped by Income Level.
- **Responses**:
  - `200 OK`: `List[IncomeChurnRate]`

#### `GET /api/v1/analytics/churn-by-device`
- **Description**: Returns churn rates and count breakdown grouped by Device Type.
- **Responses**:
  - `200 OK`: `List[DeviceChurnRate]`

#### `GET /api/v1/analytics/churn-by-payment`
- **Description**: Returns churn rates and count breakdown grouped by Payment Mode.
- **Responses**:
  - `200 OK`: `List[PaymentChurnRate]`

#### `GET /api/v1/analytics/churn-by-spend`
- **Description**: Returns churn rates grouped by spend brackets.
- **Responses**:
  - `200 OK`: `List[SpendBucketChurn]`

#### `GET /api/v1/analytics/churn-by-tenure`
- **Description**: Returns churn rates grouped by tenure duration categories.
- **Responses**:
  - `200 OK`: `List[TenureBucketChurn]`

#### `GET /api/v1/analytics/churn-by-satisfaction`
- **Description**: Returns churn rates and average support interactions grouped by Customer Satisfaction Score.
- **Responses**:
  - `200 OK`: `List[SatisfactionChurnRate]`

#### `GET /api/v1/analytics/customer-segmentation`
- **Description**: Returns business segmentation categorization with count and average churn probability.
- **Responses**:
  - `200 OK`: `List[SegmentStats]`

---

## 4. Customer Directory (Search & Filter)

### Data Models
```python
class CustomerListRow(BaseModel):
    customer_id: str
    age: int
    income_level: str
    tenure_months: int
    monthly_total_spend: float
    satisfaction_score: int
    device_type: str
    payment_mode: str
    churn_probability: float
    risk_category: str
    will_cancel: int
    recommendation_type: str

class PaginatedCustomersResponse(BaseModel):
    total: int
    page: int
    limit: int
    results: List[CustomerListRow]
```

### Endpoints
#### `GET /api/v1/customers`
- **Description**: Fetches a paginated, filterable list of customers for the datagrid.
- **Query Parameters**:
  - `page`: `int = 1`
  - `limit`: `int = 20`
  - `search_id`: `Optional[str] = None` (Prefix search by customer ID)
  - `income_levels`: `Optional[List[str]] = None` (Multi-select)
  - `device_types`: `Optional[List[str]] = None` (Multi-select)
  - `payment_modes`: `Optional[List[str]] = None` (Multi-select)
  - `risk_categories`: `Optional[List[str]] = None` (Multi-select)
  - `will_cancel`: `Optional[int] = None` (0 or 1)
- **Responses**:
  - `200 OK`: Returns `PaginatedCustomersResponse`

---

## 5. Customer Profile & Retention Recommendations

### Data Models
```python
class PredictionHistoryItem(BaseModel):
    prediction_id: int
    churn_probability: float
    risk_category: str
    will_cancel: int
    recommendation_type: str
    predicted_at: str  # ISO timestamp

class CustomerProfileResponse(BaseModel):
    customer_id: str
    age: int
    income_level: str
    number_of_subscriptions: int
    tenure_months: int
    monthly_total_spend: float
    avg_usage_hours_per_week: float
    app_switch_frequency: str
    customer_support_interactions: int
    satisfaction_score: int
    discount_used: bool
    device_type: str
    payment_mode: str
    created_at: str
    
    # Latest Prediction Data
    churn_probability: Optional[float] = None
    risk_category: Optional[str] = None
    will_cancel: Optional[int] = None
    explainability_json: Optional[dict] = None  # Key-value SHAP weights
    recommendation_type: Optional[str] = None
    recommendation_desc: Optional[str] = None
    predicted_at: Optional[str] = None
```

### Endpoints
#### `GET /api/v1/customers/{customer_id}`
- **Description**: Retrieves full demographic, transactional, and churn prediction details for an individual customer.
- **Responses**:
  - `200 OK`: `CustomerProfileResponse`
  - `404 Not Found`: Customer does not exist

#### `GET /api/v1/customers/{customer_id}/history`
- **Description**: Returns historical prediction entries for a customer to display risk trends over time.
- **Responses**:
  - `200 OK`: `List[PredictionHistoryItem]`
  - `404 Not Found`: Customer does not exist

---

## 6. Churn Prediction & Model Inference

### Data Models
```python
class SinglePredictionResponse(BaseModel):
    customer_id: str
    churn_probability: float
    risk_category: str
    will_cancel: int
    explainability: dict
    recommendation_type: str
    recommendation_desc: str

class BulkPredictionUploadResponse(BaseModel):
    job_id: str
    status: str  # 'QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED'
    total_records: int
    created_at: str

class BulkPredictionStatusResponse(BaseModel):
    job_id: str
    status: str
    total_records: int
    processed_records: int
    successful_records: int
    failed_records: int
    error_message: Optional[str] = None
    completed_at: Optional[str] = None
    download_url: Optional[str] = None  # URL to fetch predictions CSV
```

### Endpoints
#### `POST /api/v1/predictions/single/{customer_id}`
- **Description**: Triggers ML model prediction manually for an individual customer based on current attributes. Saves the output in the DB.
- **Responses**:
  - `200 OK`: Returns `SinglePredictionResponse`
  - `404 Not Found`: Customer does not exist

#### `POST /api/v1/predictions/bulk`
- **Description**: Uploads a CSV file containing raw customer columns to perform batch prediction. Runs asynchronously in a background task queue.
- **Request Format**: `multipart/form-data` with `file: UploadFile`
- **Responses**:
  - `202 Accepted`: Returns `BulkPredictionUploadResponse`
  - `400 Bad Request`: Invalid CSV headers or data format

#### `GET /api/v1/predictions/bulk/status/{job_id}`
- **Description**: Monitors the status, progress, and download link of an asynchronous bulk prediction job.
- **Responses**:
  - `200 OK`: Returns `BulkPredictionStatusResponse`
  - `404 Not Found`: Job ID does not exist

---

## 7. Reports & File Exports

### Endpoints
#### `GET /api/v1/reports/export`
- **Description**: Generates and downloads a report containing predictions and recommended offers.
- **Query Parameters**:
  - `format`: `str = "csv"` (Accepted values: `"csv"`, `"pdf"`, `"xlsx"`)
  - `risk_category`: `Optional[str] = "High"` (Filter rows)
  - `recommendation_type`: `Optional[str] = None`
- **Responses**:
  - `200 OK`: Binary file stream (with proper MIME type: `text/csv`, `application/pdf`, or `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`) and header `Content-Disposition: attachment; filename="report.<extension>"`

---

## 8. Model Evaluation & Performance

### Data Models
```python
class ConfusionMatrix(BaseModel):
    tp: int
    fp: int
    tn: int
    fn: int

class ModelMetricsResponse(BaseModel):
    model_version: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    roc_auc: float
    confusion_matrix: ConfusionMatrix
    feature_importance: dict  # Feature name keys with importance weight values
    evaluated_at: str
```

### Endpoints
#### `GET /api/v1/model/metrics`
- **Description**: Retrieves performance metrics, confusion matrix, and feature importances of the currently deployed prediction model.
- **Responses**:
  - `200 OK`: Returns `ModelMetricsResponse`
