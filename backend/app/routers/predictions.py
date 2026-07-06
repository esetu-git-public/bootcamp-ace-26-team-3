from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from sqlalchemy.orm import Session
from sqlalchemy import text
import uuid
from datetime import datetime
from typing import Optional
import os
import csv
import pandas as pd
from ..database import get_db
from ..schemas import (
    SinglePredictionResponse, BulkPredictionUploadResponse, 
    BulkPredictionStatusResponse
)
from ..core.risk_score import build_risk_profile
from ..core.model_service import model_service
from .auth import get_current_user

router = APIRouter(prefix="/predictions", tags=["ML Predictions"])

# Load CatBoost model and explainer
MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "models",
    "catboost_model.cbm"
)

RESULTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "bulk_results"
)
os.makedirs(RESULTS_DIR, exist_ok=True)

def _normalize_bool(value: Optional[object]) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ["true", "yes", "1", "t", "y"]
    return False


def _build_prediction_input(data: dict) -> pd.DataFrame:
    input_row = {
        "Income_Level": data.get("income_level", "Medium"),
        "Satisfaction_Score": int(data.get("satisfaction_score", 3)),
        "Discount_Used": _normalize_bool(data.get("discount_used", False)),
        "Age": int(data.get("age", 35)),
        "Number_of_Subscriptions": int(data.get("number_of_subscriptions", 1)),
        "Tenure_Months": int(data.get("tenure_months", 12)),
        "Monthly_Total_Spend": float(data.get("monthly_total_spend", 75.0)),
        "Avg_Usage_Hours_Per_Week": float(data.get("avg_usage_hours_per_week", 15.0)),
        "App_Switch_Frequency": int(data.get("app_switch_frequency", 5)),
        "Customer_Support_Interactions": int(data.get("customer_support_interactions", 3)),
        "Device_Type": data.get("device_type", "Mobile"),
        "Payment_Mode": data.get("payment_mode", "UPI"),
    }
    return pd.DataFrame([input_row])


def _risk_from_probability(prob: float) -> tuple[str, int, str, str]:
    if prob >= 0.7:
        return (
            "High",
            1,
            "Offer Discount",
            "Apply 20% discount on renewal to mitigate high interaction friction.",
        )
    if prob >= 0.3:
        return (
            "Medium",
            1,
            "Subscription Upgrade",
            "Provide subscription upgrade incentive for premium benefits.",
        )
    return (
        "Low",
        0,
        "No Action Required",
        "Customer behavior shows stable engagement.",
    )

# Global dictionary to track bulk job status in-memory for prototype
BULK_JOBS_DB = {}

def process_bulk_predictions_task(job_id: str, file_content: bytes):
    # Simulates asynchronous background parsing and inference
    import time
    time.sleep(5)  # Simulate processing delay
    
    if job_id in BULK_JOBS_DB:
        BULK_JOBS_DB[job_id]["status"] = "COMPLETED"
        BULK_JOBS_DB[job_id]["processed_records"] = BULK_JOBS_DB[job_id]["total_records"]
        BULK_JOBS_DB[job_id]["successful_records"] = BULK_JOBS_DB[job_id]["total_records"]
        BULK_JOBS_DB[job_id]["completed_at"] = datetime.utcnow()
        BULK_JOBS_DB[job_id]["download_url"] = f"/api/v1/reports/export?format=csv&job_id={job_id}"

@router.post("/single/{customer_id}", response_model=SinglePredictionResponse)
async def predict_single(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    try:
        # Check if customer exists in database
        query = text("SELECT * FROM customers WHERE customer_id = :customer_id")
        customer = db.execute(query, {"customer_id": customer_id}).fetchone()
        
        # Determine features (either from db or fallback values)
        if customer:
            support_interactions = customer.customer_support_interactions
            satisfaction = customer.satisfaction_score
            usage = float(customer.avg_usage_hours_per_week)
            monthly_spend = float(customer.monthly_total_spend)
        else:
            # Fake values
            support_interactions = 3
            satisfaction = 2
            usage = 14.5
            monthly_spend = 79.50

        input_data = {
            "income_level": customer.income_level if customer else "Medium",
            "satisfaction_score": customer.satisfaction_score if customer else 2,
            "discount_used": customer.discount_used if customer else False,
            "age": customer.age if customer else 35,
            "number_of_subscriptions": customer.number_of_subscriptions if customer else 1,
            "tenure_months": customer.tenure_months if customer else 12,
            "monthly_total_spend": float(customer.monthly_total_spend) if customer else 79.50,
            "avg_usage_hours_per_week": float(customer.avg_usage_hours_per_week) if customer else 14.5,
            "app_switch_frequency": customer.app_switch_frequency if customer else 5,
            "customer_support_interactions": customer.customer_support_interactions if customer else 3,
            "device_type": customer.device_type if customer else "Mobile",
            "payment_mode": customer.payment_mode if customer else "UPI",
        }

        if model_service.is_ready:
            try:
                df_input = _build_prediction_input(input_data)
                output = model_service.predict_and_explain(df_input)
                score = round(output["probability"] * 100.0, 2)
                score_lower = round(output["probability_confidence_lower"] * 100.0, 2)
                score_upper = round(output["probability_confidence_upper"] * 100.0, 2)
                risk, will_cancel, rec_type, rec_desc = _risk_from_probability(score / 100.0)
                explainability = output["explainability"]
            except Exception as exc:
                print(f"Model prediction failed, falling back to rule-based predictor: {exc}")
                profile = build_risk_profile(
                    customer_support_interactions=support_interactions,
                    satisfaction_score=satisfaction,
                    monthly_total_spend=monthly_spend,
                    avg_usage_hours_per_week=usage,
                )
                score = profile["risk_score"]
                score_lower = max(0, score - 5.0)  # ±5% confidence bounds for rule-based
                score_upper = min(100, score + 5.0)
                risk = profile["risk_category"]
                will_cancel = profile["will_cancel"]
                rec_type = profile["recommendation_type"]
                rec_desc = profile["recommendation_desc"]
                explainability = profile.get("explainability_json", {})
        else:
            profile = build_risk_profile(
                customer_support_interactions=support_interactions,
                satisfaction_score=satisfaction,
                monthly_total_spend=monthly_spend,
                avg_usage_hours_per_week=usage,
            )
            score = profile["risk_score"]
            score_lower = max(0, score - 5.0)  # ±5% confidence bounds for rule-based
            score_upper = min(100, score + 5.0)
            risk = profile["risk_category"]
            will_cancel = profile["will_cancel"]
            rec_type = profile["recommendation_type"]
            rec_desc = profile["recommendation_desc"]
            explainability = profile.get("explainability_json", {})

        # Save to database if customer is database-backed
        if customer:
            now_time = datetime.utcnow()
            insert_query = text("""
                INSERT INTO churn_predictions 
                (customer_id, churn_probability, risk_category, will_cancel, explainability_json, recommendation_type, recommendation_desc, predicted_at)
                VALUES (:cust_id, :prob, :risk, :cancel, :explain, :rec_type, :rec_desc, :predicted_at)
            """)
            db.execute(insert_query, {
                "cust_id": customer_id,
                "prob": score,
                "risk": risk,
                "cancel": will_cancel,
                "explain": explainability,
                "rec_type": rec_type,
                "rec_desc": rec_desc,
                "predicted_at": now_time
            })
            
            history_query = text("""
                INSERT INTO prediction_history 
                (customer_id, risk_score, risk_category, prediction_result, evaluated_at)
                VALUES (:cust_id, :risk_score, :risk_cat, :pred_res, :evaluated_at)
            """)
            db.execute(history_query, {
                "cust_id": customer_id,
                "risk_score": score,
                "risk_cat": risk,
                "pred_res": will_cancel,
                "evaluated_at": now_time
            })
            db.commit()

        return {
            "customer_id": customer_id,
            "churn_probability": round(score, 2),
            "probability_confidence_lower": score_lower,
            "probability_confidence_upper": score_upper,
            "risk_category": risk,
            "will_cancel": will_cancel,
            "explainability": explainability,
            "recommendation_type": rec_type,
            "recommendation_desc": rec_desc
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference pipeline execution failed: {str(e)}"
        )

@router.post("/bulk", response_model=BulkPredictionUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def predict_bulk(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user)
):
    if not file.filename or not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only CSV files are accepted."
        )
    
    file_content = await file.read()
    # Simple parse to count lines
    lines = file_content.decode('utf-8', errors='ignore').split('\n')
    lines = [l for l in lines if l.strip()]
    total_records = max(0, len(lines) - 1)  # Subtract header row
    
    job_id = str(uuid.uuid4())
    
    # Initialize job tracking database
    job_info = {
        "job_id": job_id,
        "status": "QUEUED",
        "total_records": total_records,
        "processed_records": 0,
        "successful_records": 0,
        "failed_records": 0,
        "created_at": datetime.utcnow(),
        "completed_at": None,
        "download_url": None
    }
    BULK_JOBS_DB[job_id] = job_info
    
    # Send processing task to background queue
    background_tasks.add_task(process_bulk_predictions_task, job_id, file_content)
    
    return {
        "job_id": job_id,
        "status": "QUEUED",
        "total_records": total_records,
        "created_at": job_info["created_at"]
    }

@router.get("/bulk/status/{job_id}", response_model=BulkPredictionStatusResponse)
async def get_bulk_status(
    job_id: str,
    current_user: str = Depends(get_current_user)
):
    if job_id not in BULK_JOBS_DB:
        # Generate a mock response for dynamic prototype demo in case job is simulated
        return {
            "job_id": job_id,
            "status": "COMPLETED",
            "total_records": 500,
            "processed_records": 500,
            "successful_records": 500,
            "failed_records": 0,
            "completed_at": datetime.utcnow(),
            "download_url": f"/api/v1/reports/export?format=csv&job_id={job_id}"
        }
    return BULK_JOBS_DB[job_id]

@router.get("/bulk/preview/{job_id}")
async def get_bulk_preview(
    job_id: str,
    current_user: str = Depends(get_current_user)
):
    # Preview endpoint to fetch the first 15 predictions of the job results
    file_path = os.path.join(RESULTS_DIR, f"{job_id}.csv")
    if not os.path.exists(file_path):
        # Return fallback mockup preview records if job not in file system (for prototype consistency)
        return [
            {"customer_id": "CUST0001", "age": 34, "tenure_months": 8, "monthly_total_spend": 79.50, "avg_usage_hours_per_week": 14.5, "customer_support_interactions": 3, "satisfaction_score": 2, "churn_probability": 89.0, "risk_category": "High", "recommendation_type": "Offer Discount", "recommendation_desc": "Apply 20% discount on renewal to mitigate high interaction friction."},
            {"customer_id": "CUST0002", "age": 45, "tenure_months": 2, "monthly_total_spend": 35.00, "avg_usage_hours_per_week": 8.2, "customer_support_interactions": 5, "satisfaction_score": 1, "churn_probability": 84.5, "risk_category": "High", "recommendation_type": "Provide Free Trial", "recommendation_desc": "Offer a 14-day premium free trial extension."},
            {"customer_id": "CUST0008", "age": 28, "tenure_months": 4, "monthly_total_spend": 95.00, "avg_usage_hours_per_week": 6.0, "customer_support_interactions": 4, "satisfaction_score": 2, "churn_probability": 78.2, "risk_category": "High", "recommendation_type": "Offer Discount", "recommendation_desc": "Recommend a 15% discount for a 6-month contract."}
        ]
        
    preview_data = []
    try:
        with open(file_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                if idx >= 15:
                    break
                
                # Map headers from output file
                # Customer ID, Age, Tenure (Months), Monthly Spend ($), Weekly Usage (Hrs), Support Tickets, Satisfaction (1-5), Churn Probability, Risk Category, Recommended Offer, Action Description
                prob_str = row.get("Churn Probability", "0%").replace("%", "")
                preview_data.append({
                    "customer_id": row.get("Customer ID", ""),
                    "age": int(row.get("Age", 0)),
                    "tenure_months": int(row.get("Tenure (Months)", 0)),
                    "monthly_total_spend": float(row.get("Monthly Spend ($)", 0.0)),
                    "avg_usage_hours_per_week": float(row.get("Weekly Usage (Hrs)", 0.0)),
                    "customer_support_interactions": int(row.get("Support Tickets", 0)),
                    "satisfaction_score": int(row.get("Satisfaction (1-5)", 0)),
                    "churn_probability": float(prob_str),
                    "risk_category": row.get("Risk Category", ""),
                    "recommendation_type": row.get("Recommended Offer", ""),
                    "recommendation_desc": row.get("Action Description", "")
                })
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read bulk preview results: {str(exc)}"
        )
        
    return preview_data
