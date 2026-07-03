# backend/app/schemas.py
from pydantic import BaseModel, Field, validator

# This schema validates that any incoming customer data matches the dataset constraints
class CustomerValidationSchema(BaseModel):
    customer_id: str = Field(..., min_length=1, max_length=50)
    age: int = Field(..., ge=18, le=100, description="Age must be between 18 and 100")
    income_level: str = Field(..., description="Must be Low, Medium, or High")
    device_type: str = Field(..., description="Must be Mobile, Smart TV, Desktop, or Tablet")
    payment_mode: str = Field(..., description="Must be Credit Card, UPI, Debit Card, or Net Banking")
    
    number_of_subscriptions: int = Field(..., ge=1)
    tenure_months: int = Field(..., ge=0)
    monthly_total_spend: float = Field(..., ge=0.0)
    
    avg_usage_hours_per_week: float = Field(..., ge=0.0, le=168.0)
    app_switch_frequency: int = Field(..., ge=0)
    customer_support_interactions: int = Field(..., ge=0)
    satisfaction_score: int = Field(..., ge=1, le=5, description="Satisfaction must be 1 to 5")
    discount_used: bool

    # Custom validators to act as strict requirement checkpoints
    @validator('income_level')
    def validate_income(cls, v):
        if v not in ['Low', 'Medium', 'High']:
            raise ValueError("Income level must be 'Low', 'Medium', or 'High'")
        return v

    @validator('device_type')
    def validate_device(cls, v):
        if v not in ['Mobile', 'Smart TV', 'Desktop', 'Tablet']:
            raise ValueError("Device type must be 'Mobile', 'Smart TV', 'Desktop', or 'Tablet'")
        return v

    @validator('payment_mode')
    def validate_payment(cls, v):
        if v not in ['Credit Card', 'UPI', 'Debit Card', 'Net Banking']:
            raise ValueError("Payment mode must be 'Credit Card', 'UPI', 'Debit Card', or 'Net Banking'")
        return v