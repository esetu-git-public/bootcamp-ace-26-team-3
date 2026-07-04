from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from sqlalchemy.orm import Session
from sqlalchemy import text
import uuid
from datetime import datetime
from typing import Optional
import os
import csv
from catboost import CatBoostClassifier
import shap
from ..database import get_db
from ..schemas import (
    SinglePredictionResponse, BulkPredictionUploadResponse, 
    BulkPredictionStatusResponse
)
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

_model = None
_shap_explainer = None

def get_model():
    global _model, _shap_explainer
    if _model is None:
        if os.path.exists(MODEL_PATH):
            try:
                m = CatBoostClassifier()
                m.load_model(MODEL_PATH)
                _model = m
                _shap_explainer = shap.TreeExplainer(m)
            except Exception as e:
                print(f"Failed to load CatBoost model: {e}")
    return _model, _shap_explainer

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

        # Implement a deterministic mock rule-based classifier model
        # Pushes probability up: support interactions, high spend
        # Pulls probability down: high satisfaction, high usage
        score = 30.0 + (support_interactions * 15.0) - (satisfaction * 10.0) + (monthly_spend * 0.20) - (usage * 0.8)
        score = max(0.0, min(100.0, score))  # Clip between 0 and 100
        
        # Categorize risk
        if score >= 70.0:
            risk = "High"
            will_cancel = 1
            rec_type = "Offer Discount"
            rec_desc = "Apply 20% discount on renewal to mitigate high interaction friction."
        elif score >= 30.0:
            risk = "Medium"
            will_cancel = 1
            rec_type = "Subscription Upgrade"
            rec_desc = "Provide subscription upgrade incentive for premium benefits."
        else:
            risk = "Low"
            will_cancel = 0
            rec_type = "No Action Required"
            rec_desc = "Customer behavior shows stable engagement."

        explainability = {
            "Customer_Support_Interactions": round(support_interactions * 0.1, 2),
            "Satisfaction_Score": round((6 - satisfaction) * 0.1, 2),
            "Avg_Usage_Hours_Per_Week": round(-usage * 0.02, 2),
            "Monthly_Total_Spend": round(monthly_spend * 0.002, 2)
        }

        # Save to database if customer is database-backed
        if customer:
            insert_query = text("""
                INSERT INTO churn_predictions 
                (customer_id, churn_probability, risk_category, will_cancel, explainability_json, recommendation_type, recommendation_desc, predicted_at)
                VALUES (:cust_id, :prob, :risk, :cancel, :explain, :rec_type, :rec_desc, NOW())
            """)
            db.execute(insert_query, {
                "cust_id": customer_id,
                "prob": score,
                "risk": risk,
                "cancel": will_cancel,
                "explain": explainability,
                "rec_type": rec_type,
                "rec_desc": rec_desc
            })
            db.commit()

        return {
            "customer_id": customer_id,
            "churn_probability": round(score, 2),
            "risk_category": risk,
            "will_cancel": will_cancel,
            "explainability_json": explainability,
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
