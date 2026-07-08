from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from sqlalchemy.orm import Session
from sqlalchemy import text
import uuid
import json
from datetime import datetime
from typing import Optional
from io import StringIO
import os
import csv
import re
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


def _get_first(data: dict, *keys: str, default: Optional[object] = None) -> Optional[object]:
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return default


def _to_int(value: Optional[object], default: int) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _to_float(value: Optional[object], default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _build_prediction_input(data: dict) -> pd.DataFrame:
    input_row = {
        "Income_Level": _get_first(data, "income_level", "Income_Level", "Income Level", default="Medium"),
        "Satisfaction_Score": _to_int(_get_first(data, "satisfaction_score", "Satisfaction_Score", "Satisfaction (1-5)", default=3), 3),
        "Discount_Used": _normalize_bool(_get_first(data, "discount_used", "Discount_Used", "Discount Used", default=False)),
        "Age": _to_int(_get_first(data, "age", "Age", default=35), 35),
        "Number_of_Subscriptions": _to_int(_get_first(data, "number_of_subscriptions", "Number_of_Subscriptions", "Number of Subscriptions", default=1), 1),
        "Tenure_Months": _to_int(_get_first(data, "tenure_months", "Tenure_Months", "Tenure (Months)", default=12), 12),
        "Monthly_Total_Spend": _to_float(_get_first(data, "monthly_total_spend", "Monthly_Total_Spend", "Monthly Spend ($)", default=75.0), 75.0),
        "Avg_Usage_Hours_Per_Week": _to_float(_get_first(data, "avg_usage_hours_per_week", "Avg_Usage_Hours_Per_Week", "Weekly Usage (Hrs)", default=15.0), 15.0),
        "App_Switch_Frequency": _to_int(_get_first(data, "app_switch_frequency", "App_Switch_Frequency", default=5), 5),
        "Customer_Support_Interactions": _to_int(_get_first(data, "customer_support_interactions", "Customer_Support_Interactions", "Support Tickets", default=3), 3),
        "Device_Type": _get_first(data, "device_type", "Device_Type", "Device Type", default="Mobile"),
        "Payment_Mode": _get_first(data, "payment_mode", "Payment_Mode", "Payment Mode", default="UPI"),
    }
    return pd.DataFrame([input_row], dtype=object)


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


def _is_valid_job_id(job_id: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_-]+", job_id))


def _score_prediction_row(row: dict) -> dict:
    df_input = _build_prediction_input(row)
    try:
        if not model_service.is_ready:
            raise RuntimeError("Model artifacts are not available.")

        output = model_service.predict_and_explain(df_input)
        score = round(output["probability"] * 100.0, 2)
        score_lower = round(output["probability_confidence_lower"] * 100.0, 2)
        score_upper = round(output["probability_confidence_upper"] * 100.0, 2)
        risk, will_cancel, rec_type, rec_desc = _risk_from_probability(score / 100.0)
    except Exception as exc:
        print(f"Bulk model prediction failed, falling back to rule-based predictor: {exc}")
        profile = build_risk_profile(
            customer_support_interactions=_to_int(_get_first(row, "customer_support_interactions", "Customer_Support_Interactions", "Support Tickets", default=3), 3),
            satisfaction_score=_to_int(_get_first(row, "satisfaction_score", "Satisfaction_Score", "Satisfaction (1-5)", default=3), 3),
            monthly_total_spend=_to_float(_get_first(row, "monthly_total_spend", "Monthly_Total_Spend", "Monthly Spend ($)", default=75.0), 75.0),
            avg_usage_hours_per_week=_to_float(_get_first(row, "avg_usage_hours_per_week", "Avg_Usage_Hours_Per_Week", "Weekly Usage (Hrs)", default=15.0), 15.0),
        )
        score = round(float(profile["risk_score"]), 2)
        score_lower = round(max(0, score - 5.0), 2)
        score_upper = round(min(100, score + 5.0), 2)
        risk = profile["risk_category"]
        will_cancel = profile["will_cancel"]
        rec_type = profile["recommendation_type"]
        rec_desc = profile["recommendation_desc"]

    return {
        "customer_id": str(_get_first(row, "customer_id", "Customer ID", "Customer_ID", default="")).strip() or "UNKNOWN",
        "age": _to_int(_get_first(row, "age", "Age", default=35), 35),
        "tenure_months": _to_int(_get_first(row, "tenure_months", "Tenure_Months", "Tenure (Months)", default=12), 12),
        "monthly_total_spend": _to_float(_get_first(row, "monthly_total_spend", "Monthly_Total_Spend", "Monthly Spend ($)", default=75.0), 75.0),
        "avg_usage_hours_per_week": _to_float(_get_first(row, "avg_usage_hours_per_week", "Avg_Usage_Hours_Per_Week", "Weekly Usage (Hrs)", default=15.0), 15.0),
        "customer_support_interactions": _to_int(_get_first(row, "customer_support_interactions", "Customer_Support_Interactions", "Support Tickets", default=3), 3),
        "satisfaction_score": _to_int(_get_first(row, "satisfaction_score", "Satisfaction_Score", "Satisfaction (1-5)", default=3), 3),
        "churn_probability": score,
        "probability_confidence_lower": score_lower,
        "probability_confidence_upper": score_upper,
        "risk_category": risk,
        "will_cancel": will_cancel,
        "recommendation_type": rec_type,
        "recommendation_desc": rec_desc,
    }


def process_bulk_predictions_task(job_id: str, file_content: bytes):
    if job_id not in BULK_JOBS_DB or not _is_valid_job_id(job_id):
        return

    BULK_JOBS_DB[job_id]["status"] = "PROCESSING"
    output_path = os.path.join(RESULTS_DIR, f"{job_id}.csv")

    try:
        decoded = file_content.decode("utf-8-sig", errors="ignore")
        reader = csv.DictReader(StringIO(decoded))
        if not reader.fieldnames:
            raise ValueError("CSV file must include a header row.")

        fieldnames = [
            "Customer ID", "Age", "Tenure (Months)", "Monthly Spend ($)",
            "Weekly Usage (Hrs)", "Support Tickets", "Satisfaction (1-5)",
            "Churn Probability", "Confidence Lower", "Confidence Upper",
            "Will Cancel", "Risk Category", "Recommended Offer", "Action Description"
        ]

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                if not any(str(value).strip() for value in row.values() if value is not None):
                    continue

                try:
                    result = _score_prediction_row(row)
                    writer.writerow({
                        "Customer ID": result["customer_id"],
                        "Age": result["age"],
                        "Tenure (Months)": result["tenure_months"],
                        "Monthly Spend ($)": result["monthly_total_spend"],
                        "Weekly Usage (Hrs)": result["avg_usage_hours_per_week"],
                        "Support Tickets": result["customer_support_interactions"],
                        "Satisfaction (1-5)": result["satisfaction_score"],
                        "Churn Probability": f"{result['churn_probability']}%",
                        "Confidence Lower": f"{result['probability_confidence_lower']}%",
                        "Confidence Upper": f"{result['probability_confidence_upper']}%",
                        "Will Cancel": result["will_cancel"],
                        "Risk Category": result["risk_category"],
                        "Recommended Offer": result["recommendation_type"],
                        "Action Description": result["recommendation_desc"],
                    })
                    BULK_JOBS_DB[job_id]["successful_records"] += 1
                except Exception as row_exc:
                    print(f"Failed to process bulk row for job {job_id}: {row_exc}")
                    BULK_JOBS_DB[job_id]["failed_records"] += 1
                finally:
                    BULK_JOBS_DB[job_id]["processed_records"] += 1

        BULK_JOBS_DB[job_id]["status"] = "COMPLETED"
        BULK_JOBS_DB[job_id]["completed_at"] = datetime.utcnow()
        BULK_JOBS_DB[job_id]["download_url"] = f"/api/v1/reports/export?format=csv&job_id={job_id}"
    except Exception as exc:
        BULK_JOBS_DB[job_id]["status"] = "FAILED"
        BULK_JOBS_DB[job_id]["error_message"] = str(exc)
        BULK_JOBS_DB[job_id]["completed_at"] = datetime.utcnow()

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
            
            input_data = {
                "income_level": customer.income_level,
                "satisfaction_score": customer.satisfaction_score,
                "discount_used": customer.discount_used,
                "age": customer.age,
                "number_of_subscriptions": customer.number_of_subscriptions,
                "tenure_months": customer.tenure_months,
                "monthly_total_spend": float(customer.monthly_total_spend),
                "avg_usage_hours_per_week": float(customer.avg_usage_hours_per_week),
                "app_switch_frequency": customer.app_switch_frequency,
                "customer_support_interactions": customer.customer_support_interactions,
                "device_type": customer.device_type,
                "payment_mode": customer.payment_mode,
            }
        else:
            # Check if valid mock ID
            mock_rows = [
                {"customer_id": "1", "age": 34, "income_level": "Medium", "tenure_months": 8, "monthly_total_spend": 79.50, "satisfaction_score": 2, "device_type": "Android", "payment_mode": "UPI", "churn_probability": 89.00, "risk_category": "High", "will_cancel": 1, "recommendation_type": "Offer Discount"},
                {"customer_id": "2", "age": 45, "income_level": "Low", "tenure_months": 2, "monthly_total_spend": 35.00, "satisfaction_score": 1, "device_type": "Web", "payment_mode": "Wallet", "churn_probability": 84.50, "risk_category": "High", "will_cancel": 1, "recommendation_type": "Provide Free Trial"},
                {"customer_id": "3", "age": 22, "income_level": "High", "tenure_months": 15, "monthly_total_spend": 120.00, "satisfaction_score": 4, "device_type": "iOS", "payment_mode": "Credit Card", "churn_probability": 15.30, "risk_category": "Low", "will_cancel": 0, "recommendation_type": "No Action Required"},
                {"customer_id": "4", "age": 58, "income_level": "Medium", "tenure_months": 24, "monthly_total_spend": 55.00, "satisfaction_score": 5, "device_type": "Android", "payment_mode": "Debit Card", "churn_probability": 4.10, "risk_category": "Low", "will_cancel": 0, "recommendation_type": "No Action Required"},
                {"customer_id": "5", "age": 29, "income_level": "Low", "tenure_months": 5, "monthly_total_spend": 45.00, "satisfaction_score": 3, "device_type": "iOS", "payment_mode": "Wallet", "churn_probability": 52.40, "risk_category": "Medium", "will_cancel": 1, "recommendation_type": "Subscription Upgrade"}
            ]
            row = next((r for r in mock_rows if str(r["customer_id"]) == str(customer_id)), None)
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Customer with ID {customer_id} not found."
                )
            
            support_interactions = 3 if row["risk_category"] == "High" else 1
            satisfaction = row["satisfaction_score"]
            usage = 14.5
            monthly_spend = row["monthly_total_spend"]
            
            input_data = {
                "income_level": row["income_level"],
                "satisfaction_score": row["satisfaction_score"],
                "discount_used": False,
                "age": row["age"],
                "number_of_subscriptions": 2,
                "tenure_months": row["tenure_months"],
                "monthly_total_spend": float(row["monthly_total_spend"]),
                "avg_usage_hours_per_week": 14.5,
                "app_switch_frequency": 15,
                "customer_support_interactions": support_interactions,
                "device_type": row["device_type"],
                "payment_mode": row["payment_mode"],
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
                "explain": json.dumps(explainability) if isinstance(explainability, dict) else explainability,
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
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only CSV files are accepted."
        )
    
    file_content = await file.read()
    decoded = file_content.decode("utf-8-sig", errors="ignore")
    reader = csv.DictReader(StringIO(decoded))
    if not reader.fieldnames:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file must include a header row."
        )
    total_records = sum(
        1
        for row in reader
        if any(str(value).strip() for value in row.values() if value is not None)
    )
    if total_records == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file must include at least one customer record."
        )
    
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
        "download_url": None,
        "error_message": None,
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
    if not _is_valid_job_id(job_id) or job_id not in BULK_JOBS_DB:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bulk prediction job not found."
        )
    return BULK_JOBS_DB[job_id]

@router.get("/bulk/preview/{job_id}")
async def get_bulk_preview(
    job_id: str,
    current_user: str = Depends(get_current_user)
):
    if not _is_valid_job_id(job_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bulk prediction job not found."
        )

    # Preview endpoint to fetch the first 15 predictions of the job results
    file_path = os.path.join(RESULTS_DIR, f"{job_id}.csv")
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bulk prediction results are not available."
        )
        
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
                lower_str = row.get("Confidence Lower", "0%").replace("%", "")
                upper_str = row.get("Confidence Upper", "0%").replace("%", "")
                preview_data.append({
                    "customer_id": row.get("Customer ID", ""),
                    "age": int(row.get("Age", 0)),
                    "tenure_months": int(row.get("Tenure (Months)", 0)),
                    "monthly_total_spend": float(row.get("Monthly Spend ($)", 0.0)),
                    "avg_usage_hours_per_week": float(row.get("Weekly Usage (Hrs)", 0.0)),
                    "customer_support_interactions": int(row.get("Support Tickets", 0)),
                    "satisfaction_score": int(row.get("Satisfaction (1-5)", 0)),
                    "churn_probability": float(prob_str),
                    "probability_confidence_lower": float(lower_str),
                    "probability_confidence_upper": float(upper_str),
                    "will_cancel": int(row.get("Will Cancel", 0)),
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
