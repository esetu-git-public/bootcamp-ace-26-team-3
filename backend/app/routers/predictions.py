from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from sqlalchemy.orm import Session
from sqlalchemy import text
import uuid
import json
from datetime import datetime, timezone
from typing import Any, Optional, cast
from io import StringIO
import os
import csv
import re
import pandas as pd
from ..database import SessionLocal, get_db
from ..schemas import (
    SinglePredictionResponse, BulkPredictionUploadResponse, 
    BulkPredictionStatusResponse, SimulationRequest
)
from ..core.risk_score import build_risk_profile
from ..models import BulkPredictionJob
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
        if value is None:
            return default
        return int(float(cast(Any, value)))
    except (TypeError, ValueError):
        return default


def _to_float(value: Optional[object], default: float) -> float:
    try:
        if value is None:
            return default
        return float(cast(Any, value))
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

# Compatibility mirror for older tests/utilities. API state is persisted in bulk_prediction_jobs.
BULK_JOBS_DB = {}


def _job_to_dict(job: BulkPredictionJob) -> dict:
    return {
        "job_id": job.job_id,
        "status": job.status,
        "total_records": job.total_records,
        "processed_records": job.processed_records,
        "successful_records": job.successful_records,
        "failed_records": job.failed_records,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
        "download_url": job.download_url,
        "error_message": job.error_message,
    }


def _mirror_job(job_data: dict) -> None:
    BULK_JOBS_DB[job_data["job_id"]] = dict(job_data)


def _get_job(db: Session, job_id: str) -> Optional[BulkPredictionJob]:
    return db.query(BulkPredictionJob).filter(BulkPredictionJob.job_id == job_id).first()


def _set_job_fields(db: Session, job_id: str, **fields) -> Optional[BulkPredictionJob]:
    job = _get_job(db, job_id)
    if not job:
        return None
    for key, value in fields.items():
        setattr(job, key, value)
    db.commit()
    db.refresh(job)
    _mirror_job(_job_to_dict(job))
    return job


def _update_legacy_job(job_id: str, **fields) -> None:
    if job_id in BULK_JOBS_DB:
        BULK_JOBS_DB[job_id].update(fields)


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
        
        from ..core.prediction_service import risk_from_probability, generate_recommendation_details
        risk, will_cancel = risk_from_probability(score / 100.0)
        
        support_interactions = _to_int(_get_first(row, "customer_support_interactions", "Customer_Support_Interactions", "Support Tickets", default=3), 3)
        satisfaction = _to_int(_get_first(row, "satisfaction_score", "Satisfaction_Score", "Satisfaction (1-5)", default=3), 3)
        monthly_spend = _to_float(_get_first(row, "monthly_total_spend", "Monthly_Total_Spend", "Monthly Spend ($)", default=75.0), 75.0)
        usage = _to_float(_get_first(row, "avg_usage_hours_per_week", "Avg_Usage_Hours_Per_Week", "Weekly Usage (Hrs)", default=15.0), 15.0)
        tenure = _to_int(_get_first(row, "tenure_months", "Tenure_Months", "Tenure (Months)", default=12), 12)
        app_switch = _to_int(_get_first(row, "app_switch_frequency", "App_Switch_Frequency", default=5), 5)
        
        rec_type, rec_desc = generate_recommendation_details(
            prob=score,
            risk_category=risk,
            satisfaction_score=satisfaction,
            monthly_total_spend=monthly_spend,
            tenure_months=tenure,
            customer_support_interactions=support_interactions,
            avg_usage_hours_per_week=usage,
            app_switch_frequency=app_switch
        )
    except Exception as exc:
        print(f"Bulk model prediction failed, falling back to rule-based predictor: {exc}")
        support_interactions = _to_int(_get_first(row, "customer_support_interactions", "Customer_Support_Interactions", "Support Tickets", default=3), 3)
        satisfaction = _to_int(_get_first(row, "satisfaction_score", "Satisfaction_Score", "Satisfaction (1-5)", default=3), 3)
        monthly_spend = _to_float(_get_first(row, "monthly_total_spend", "Monthly_Total_Spend", "Monthly Spend ($)", default=75.0), 75.0)
        usage = _to_float(_get_first(row, "avg_usage_hours_per_week", "Avg_Usage_Hours_Per_Week", "Weekly Usage (Hrs)", default=15.0), 15.0)
        tenure = _to_int(_get_first(row, "tenure_months", "Tenure_Months", "Tenure (Months)", default=12), 12)
        app_switch = _to_int(_get_first(row, "app_switch_frequency", "App_Switch_Frequency", default=5), 5)
        
        profile = build_risk_profile(
            customer_support_interactions=support_interactions,
            satisfaction_score=satisfaction,
            monthly_total_spend=monthly_spend,
            avg_usage_hours_per_week=usage,
        )
        score = round(float(profile["risk_score"]), 2)
        score_lower = round(max(0, score - 5.0), 2)
        score_upper = round(min(100, score + 5.0), 2)
        risk = profile["risk_category"]
        will_cancel = profile["will_cancel"]
        
        from ..core.prediction_service import generate_recommendation_details
        rec_type, rec_desc = generate_recommendation_details(
            prob=score,
            risk_category=risk,
            satisfaction_score=satisfaction,
            monthly_total_spend=monthly_spend,
            tenure_months=tenure,
            customer_support_interactions=support_interactions,
            avg_usage_hours_per_week=usage,
            app_switch_frequency=app_switch
        )

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
    if not _is_valid_job_id(job_id):
        return

    db = SessionLocal()
    use_db = True
    try:
        try:
            job = _get_job(db, job_id)
        except Exception as lookup_exc:
            print(f"Bulk job database lookup failed, using legacy tracker: {lookup_exc}")
            job = None
            use_db = False

        if not job:
            use_db = False
            if job_id not in BULK_JOBS_DB:
                return

        if use_db:
            _set_job_fields(db, job_id, status="PROCESSING")
        _update_legacy_job(job_id, status="PROCESSING")

        output_path = os.path.join(RESULTS_DIR, f"{job_id}.csv")
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

        processed_records = 0
        successful_records = 0
        failed_records = 0

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
                    successful_records += 1
                except Exception as row_exc:
                    print(f"Failed to process bulk row for job {job_id}: {row_exc}")
                    failed_records += 1
                finally:
                    processed_records += 1
                    if use_db:
                        _set_job_fields(
                            db,
                            job_id,
                            processed_records=processed_records,
                            successful_records=successful_records,
                            failed_records=failed_records,
                        )
                    _update_legacy_job(
                        job_id,
                        processed_records=processed_records,
                        successful_records=successful_records,
                        failed_records=failed_records,
                    )

        completed_at = datetime.now(timezone.utc)
        download_url = f"/api/v1/reports/export?format=csv&job_id={job_id}"
        if use_db:
            _set_job_fields(
                db,
                job_id,
                status="COMPLETED",
                completed_at=completed_at,
                download_url=download_url,
                error_message=None,
            )
        _update_legacy_job(
            job_id,
            status="COMPLETED",
            completed_at=completed_at,
            download_url=download_url,
            error_message=None,
        )
    except Exception as exc:
        completed_at = datetime.now(timezone.utc)
        if use_db:
            _set_job_fields(
                db,
                job_id,
                status="FAILED",
                error_message=str(exc),
                completed_at=completed_at,
            )
        _update_legacy_job(
            job_id,
            status="FAILED",
            error_message=str(exc),
            completed_at=completed_at,
        )
    finally:
        db.close()
@router.post("/single/{customer_id}", response_model=SinglePredictionResponse)
async def predict_single(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    try:
        from ..models import Customer
        from ..core.prediction_service import calculate_prediction_for_customer, save_customer_prediction
        
        # Check if customer exists in database
        customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
        
        if customer:
            pred_data = calculate_prediction_for_customer(db, customer)
            db_prediction = save_customer_prediction(db, customer_id, pred_data)
            
            return {
                "customer_id": customer_id,
                "churn_probability": round(pred_data["churn_probability"], 2),
                "probability_confidence_lower": pred_data["probability_confidence_lower"],
                "probability_confidence_upper": pred_data["probability_confidence_upper"],
                "risk_category": pred_data["risk_category"],
                "will_cancel": pred_data["will_cancel"],
                "explainability": pred_data["explainability"],
                "recommendation_type": pred_data["recommendation_type"],
                "recommendation_desc": pred_data["recommendation_desc"],
                "prediction_id": db_prediction.prediction_id,
                "predicted_at": db_prediction.predicted_at,
                "model_version": db_prediction.model_version
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
            
            row["customer_id"] = customer_id
            pred_data = calculate_prediction_for_customer(db, row)
            
            return {
                "customer_id": customer_id,
                "churn_probability": round(pred_data["churn_probability"], 2),
                "probability_confidence_lower": pred_data["probability_confidence_lower"],
                "probability_confidence_upper": pred_data["probability_confidence_upper"],
                "risk_category": pred_data["risk_category"],
                "will_cancel": pred_data["will_cancel"],
                "explainability": pred_data["explainability"],
                "recommendation_type": pred_data["recommendation_type"],
                "recommendation_desc": pred_data["recommendation_desc"],
                "prediction_id": None,
                "predicted_at": datetime.now(timezone.utc),
                "model_version": pred_data["model_version"]
            }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference pipeline execution failed: {str(e)}"
        )

@router.post("/backfill-missing", status_code=status.HTTP_200_OK)
async def backfill_missing_predictions(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    try:
        from ..core.prediction_service import ensure_all_customers_have_predictions
        res = ensure_all_customers_have_predictions(db)
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backfill execution failed: {str(e)}"
        )

@router.post("/recalculate-all", status_code=status.HTTP_200_OK)
async def recalculate_all_predictions(
    customer_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    try:
        from ..models import Customer
        from ..core.prediction_service import calculate_prediction_for_customer, save_customer_prediction

        query = db.query(Customer)
        if customer_id:
            query = query.filter(Customer.customer_id == customer_id)
        customers = query.all()

        created_count = 0
        failed_ids = []

        for customer in customers:
            try:
                pred_data = calculate_prediction_for_customer(db, customer)
                save_customer_prediction(db, customer.customer_id, pred_data)
                created_count += 1
            except Exception:
                failed_ids.append(customer.customer_id)

        return {
            "total_checked": len(customers),
            "predictions_created": created_count,
            "failed_customers": failed_ids,
            "status": "success" if not failed_ids else "partial_success"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Recalculation failed: {str(e)}"
        )
@router.post("/bulk", response_model=BulkPredictionUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def predict_bulk(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
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
    job = BulkPredictionJob(
        job_id=job_id,
        status="QUEUED",
        total_records=total_records,
        processed_records=0,
        successful_records=0,
        failed_records=0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    _mirror_job(_job_to_dict(job))
    
    # Send processing task to background queue
    background_tasks.add_task(process_bulk_predictions_task, job_id, file_content)
    
    return {
        "job_id": job.job_id,
        "status": job.status,
        "total_records": job.total_records,
        "created_at": job.created_at
    }
@router.get("/bulk/status/{job_id}", response_model=BulkPredictionStatusResponse)
async def get_bulk_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    if not _is_valid_job_id(job_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bulk prediction job not found."
        )

    job = _get_job(db, job_id) if isinstance(db, Session) else None
    if job:
        job_data = _job_to_dict(job)
        _mirror_job(job_data)
        return job_data

    if job_id in BULK_JOBS_DB:
        return BULK_JOBS_DB[job_id]

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Bulk prediction job not found."
    )
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


@router.post("/simulate/{customer_id}")
async def simulate_prediction(
    customer_id: str,
    payload: SimulationRequest,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    try:
        from ..models import Customer
        from ..core.prediction_service import calculate_prediction_for_customer
        from .customers import is_valid_mock_id, get_mock_customer_profile
        
        # 1. Check if customer exists in database
        customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
        
        if customer:
            # Convert to dictionary representation
            cust_dict = {
                "customer_id": customer.customer_id,
                "age": customer.age,
                "income_level": customer.income_level,
                "number_of_subscriptions": customer.number_of_subscriptions,
                "tenure_months": customer.tenure_months,
                "monthly_total_spend": customer.monthly_total_spend,
                "avg_usage_hours_per_week": customer.avg_usage_hours_per_week,
                "app_switch_frequency": customer.app_switch_frequency,
                "customer_support_interactions": customer.customer_support_interactions,
                "satisfaction_score": customer.satisfaction_score,
                "discount_used": customer.discount_used,
                "device_type": customer.device_type,
                "payment_mode": customer.payment_mode
            }
        else:
            # Check if it's a valid mock ID
            if is_valid_mock_id(customer_id):
                cust_dict = get_mock_customer_profile(customer_id)
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Customer with ID {customer_id} not found."
                )
                
        # 2. Overlay simulation overrides
        if payload.satisfaction_score is not None:
            cust_dict["satisfaction_score"] = payload.satisfaction_score
        if payload.customer_support_interactions is not None:
            cust_dict["customer_support_interactions"] = payload.customer_support_interactions
        if payload.monthly_total_spend is not None:
            cust_dict["monthly_total_spend"] = payload.monthly_total_spend
        if payload.discount_used is not None:
            cust_dict["discount_used"] = payload.discount_used

        # 3. Calculate prediction on-the-fly using the shared helper
        # Note: We do NOT call save_customer_prediction, keeping database records untouched
        pred_data = calculate_prediction_for_customer(db, cust_dict)
        
        return {
            "customer_id": customer_id,
            "churn_probability": round(pred_data["churn_probability"], 2),
            "probability_confidence_lower": pred_data["probability_confidence_lower"],
            "probability_confidence_upper": pred_data["probability_confidence_upper"],
            "risk_category": pred_data["risk_category"],
            "will_cancel": pred_data["will_cancel"],
            "explainability": pred_data["explainability"],
            "recommendation_type": pred_data["recommendation_type"],
            "recommendation_desc": pred_data["recommendation_desc"],
            "model_version": pred_data["model_version"]
        }
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation failed: {str(e)}"
        )

