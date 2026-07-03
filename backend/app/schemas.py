from pydantic import BaseModel, Field, EmailStr
from typing import List, Dict, Any, Optional
from datetime import datetime

# ==========================================
# Authentication & Security Schemas
# ==========================================

class LoginRequest(BaseModel):
    username: str = Field(..., example="admin")
    password: str = Field(..., example="SecurePassword123")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class UserBase(BaseModel):
    username: str
    role: str

# ==========================================
# Dashboard & KPI Schemas
# ==========================================

class DashboardKPIsResponse(BaseModel):
    total_customers: int
    predicted_churn_customers: int
    high_risk_customers: int
    average_churn_risk: float
    average_satisfaction: float
    average_monthly_spend: float
    average_tenure_months: float
    monthly_revenue_at_risk: float

# ==========================================
# Business Analytics & Visualization Schemas
# ==========================================

class RiskBucket(BaseModel):
    risk_category: str
    customer_count: int
    percentage: float

class IncomeChurnRate(BaseModel):
    income_level: str
    total_customers: int
    churn_customers: int
    churn_rate: float

class DeviceChurnRate(BaseModel):
    device_type: str
    total_customers: int
    churn_customers: int
    churn_rate: float

class PaymentChurnRate(BaseModel):
    payment_mode: str
    total_customers: int
    churn_customers: int
    churn_rate: float

class SpendBucketChurn(BaseModel):
    spend_bucket: str
    total_customers: int
    churn_customers: int
    churn_rate: float

class TenureBucketChurn(BaseModel):
    tenure_bucket: str
    total_customers: int
    churn_customers: int
    churn_rate: float

class SatisfactionChurnRate(BaseModel):
    satisfaction_score: int
    total_customers: int
    churn_customers: int
    churn_rate: float
    avg_support_interactions: float

class SegmentStats(BaseModel):
    segment: str
    customer_count: int
    percentage: float
    average_churn_risk: float

# ==========================================
# Customer Profile & Directory Schemas
# ==========================================

class CustomerBase(BaseModel):
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

class CustomerCreate(CustomerBase):
    pass

class CustomerResponse(CustomerBase):
    created_at: datetime

    class Config:
        from_attributes = True

class CustomerListRow(BaseModel):
    customer_id: str
    age: int
    income_level: str
    tenure_months: int
    monthly_total_spend: float
    satisfaction_score: int
    device_type: str
    payment_mode: str
    churn_probability: Optional[float] = None
    risk_category: Optional[str] = None
    will_cancel: Optional[int] = None
    recommendation_type: Optional[str] = None

class PaginatedCustomersResponse(BaseModel):
    total: int
    page: int
    limit: int
    results: List[CustomerListRow]

class PredictionHistoryItem(BaseModel):
    prediction_id: int
    churn_probability: float
    risk_category: str
    will_cancel: int
    recommendation_type: str
    predicted_at: datetime

    class Config:
        from_attributes = True

class CustomerProfileResponse(CustomerBase):
    created_at: datetime
    
    # Prediction details
    churn_probability: Optional[float] = None
    risk_category: Optional[str] = None
    will_cancel: Optional[int] = None
    explainability_json: Optional[Dict[str, float]] = None
    recommendation_type: Optional[str] = None
    recommendation_desc: Optional[str] = None
    predicted_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# ==========================================
# ML Prediction Schemas
# ==========================================

class SinglePredictionResponse(BaseModel):
    customer_id: str
    churn_probability: float
    risk_category: str
    will_cancel: int
    explainability_json: Optional[Dict[str, float]] = None
    recommendation_type: str
    recommendation_desc: str

class BulkPredictionUploadResponse(BaseModel):
    job_id: str
    status: str
    total_records: int
    created_at: datetime

class BulkPredictionStatusResponse(BaseModel):
    job_id: str
    status: str
    total_records: int
    processed_records: int
    successful_records: int
    failed_records: int
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None
    download_url: Optional[str] = None

# ==========================================
# Model Evaluation Schemas
# ==========================================

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
    feature_importance: Dict[str, float]
    evaluated_at: datetime

    class Config:
        from_attributes = True
