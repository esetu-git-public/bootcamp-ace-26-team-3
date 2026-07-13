from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base
from .user import User

class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String(50), primary_key=True, index=True)
    age = Column(Integer, nullable=False)
    income_level = Column(String(10), nullable=False)
    number_of_subscriptions = Column(Integer, nullable=False, default=1)
    tenure_months = Column(Integer, nullable=False)
    monthly_total_spend = Column(Numeric(10, 2), nullable=False)
    avg_usage_hours_per_week = Column(Numeric(5, 2), nullable=False)
    app_switch_frequency = Column(Integer, nullable=False)
    customer_support_interactions = Column(Integer, nullable=False, default=0)
    satisfaction_score = Column(Integer, nullable=False)
    discount_used = Column(Boolean, nullable=False, default=False)
    device_type = Column(String(20), nullable=False)
    payment_mode = Column(String(30), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    predictions = relationship("ChurnPrediction", back_populates="customer", cascade="all, delete-orphan")
    history = relationship("PredictionHistory", back_populates="customer", cascade="all, delete-orphan")
    retention_interventions = relationship("RetentionIntervention", back_populates="customer", cascade="all, delete-orphan")

class ChurnPrediction(Base):
    __tablename__ = "churn_predictions"

    prediction_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False)
    churn_probability = Column(Numeric(5, 2), nullable=False)
    risk_category = Column(String(10), nullable=False)
    will_cancel = Column(Integer, nullable=False)
    explainability_json = Column(JSON, nullable=True)  # Stores SHAP values
    recommendation_type = Column(String(50), nullable=False)
    recommendation_desc = Column(Text, nullable=False)
    predicted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    model_version = Column(String(20), nullable=True)

    # Relationships
    customer = relationship("Customer", back_populates="predictions")

class ModelMetric(Base):
    __tablename__ = "model_metrics"

    metric_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    model_version = Column(String(20), nullable=False)
    accuracy = Column(Numeric(5, 4), nullable=False)
    precision = Column(Numeric(5, 4), nullable=False)
    recall = Column(Numeric(5, 4), nullable=False)
    f1_score = Column(Numeric(5, 4), nullable=False)
    roc_auc = Column(Numeric(5, 4), nullable=False)
    confusion_matrix = Column(JSON, nullable=False)
    feature_importance = Column(JSON, nullable=False)
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class PredictionHistory(Base):
    __tablename__ = "prediction_history"

    history_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False)
    risk_score = Column(Numeric(5, 2), nullable=False)
    risk_category = Column(String(20), nullable=False)
    prediction_result = Column(Integer, nullable=False)
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    customer = relationship("Customer", back_populates="history")

class BulkPredictionJob(Base):
    __tablename__ = "bulk_prediction_jobs"

    job_id = Column(String(64), primary_key=True, index=True)
    status = Column(String(20), nullable=False, default="QUEUED")
    total_records = Column(Integer, nullable=False, default=0)
    processed_records = Column(Integer, nullable=False, default=0)
    successful_records = Column(Integer, nullable=False, default=0)
    failed_records = Column(Integer, nullable=False, default=0)
    download_url = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class RetentionIntervention(Base):
    __tablename__ = "retention_interventions"

    intervention_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False)
    prediction_id = Column(Integer, ForeignKey("churn_predictions.prediction_id", ondelete="SET NULL"), nullable=True)
    offer_type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default="planned")
    notes = Column(Text, nullable=True)
    created_by = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    outcome_at = Column(DateTime(timezone=True), nullable=True)

    customer = relationship("Customer", back_populates="retention_interventions")
    prediction = relationship("ChurnPrediction")