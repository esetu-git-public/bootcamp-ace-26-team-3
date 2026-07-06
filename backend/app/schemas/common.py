from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


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


class DashboardKPIsResponse(BaseModel):
    total_customers: int
    predicted_churn_customers: int
    high_risk_customers: int
    average_churn_risk: float
    average_satisfaction: float
    average_monthly_spend: float
    average_tenure_months: float
    monthly_revenue_at_risk: float


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

    model_config = ConfigDict(from_attributes=True)


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
    history_id: int
    risk_score: float
    risk_category: str
    prediction_result: int
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerProfileResponse(CustomerBase):
    created_at: datetime
    churn_probability: Optional[float] = None
    probability_confidence_lower: Optional[float] = None
    probability_confidence_upper: Optional[float] = None
    risk_category: Optional[str] = None
    will_cancel: Optional[int] = None
    explainability: Optional[Dict[str, float]] = Field(None, description="SHAP feature importance scores")
    recommendation_type: Optional[str] = None
    recommendation_desc: Optional[str] = None
    predicted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SinglePredictionResponse(BaseModel):
    customer_id: str
    churn_probability: float
    probability_confidence_lower: float = Field(..., description="Lower bound of probability confidence interval (0.0-100.0)")
    probability_confidence_upper: float = Field(..., description="Upper bound of probability confidence interval (0.0-100.0)")
    risk_category: str
    will_cancel: int
    explainability: Optional[Dict[str, float]] = Field(None, description="SHAP feature importance scores")
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
    created_at: datetime
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None
    download_url: Optional[str] = None


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

    model_config = ConfigDict(from_attributes=True)


class CustomerValidationSchema(BaseModel):
    customer_id: str = Field(..., min_length=1, max_length=50)
    age: int = Field(..., ge=18, le=100, description="Age must be between 18 and 100")
    income_level: str = Field(..., description="Must be Low, Medium, or High")
    device_type: str = Field(..., description="Must be Android, iOS, or Web")
    payment_mode: str = Field(..., description="Must be Credit Card, UPI, Debit Card, or Wallet")
    number_of_subscriptions: int = Field(..., ge=1)
    tenure_months: int = Field(..., ge=0)
    monthly_total_spend: float = Field(..., ge=0.0)
    avg_usage_hours_per_week: float = Field(..., ge=0.0, le=168.0)
    app_switch_frequency: int = Field(..., ge=0)
    customer_support_interactions: int = Field(..., ge=0)
    satisfaction_score: int = Field(..., ge=1, le=10, description="Satisfaction must be 1 to 10")
    discount_used: bool

    @field_validator("income_level")
    @classmethod
    def validate_income(cls, v: str) -> str:
        if v not in ["Low", "Medium", "High"]:
            raise ValueError("Income level must be 'Low', 'Medium', or 'High'")
        return v

    @field_validator("device_type")
    @classmethod
    def validate_device(cls, v: str) -> str:
        if v not in ["Android", "iOS", "Web"]:
            raise ValueError("Device type must be 'Android', 'iOS', or 'Web'")
        return v

    @field_validator("payment_mode")
    @classmethod
    def validate_payment(cls, v: str) -> str:
        if v not in ["Credit Card", "UPI", "Debit Card", "Wallet"]:
            raise ValueError("Payment mode must be 'Credit Card', 'UPI', 'Debit Card', or 'Wallet'")
        return v
