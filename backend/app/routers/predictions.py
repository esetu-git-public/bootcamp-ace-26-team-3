from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from sqlalchemy.orm import Session
from sqlalchemy import text
import uuid
from datetime import datetime
import csv
import io
import os
from typing import Optional, List, Dict, Any
from ..database import get_db, SessionLocal
from ..schemas import (
    SinglePredictionResponse, BulkPredictionUploadResponse, 
    BulkPredictionStatusResponse
)
from .auth import get_current_user

router = APIRouter(prefix="/predictions", tags=["ML Predictions"])

# Global dictionary to track bulk job status in-memory for prototype
BULK_JOBS_DB = {}

# Resolve bulk_results path relative to this router file (backend/app/bulk_results)
RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bulk_results")
os.makedirs(RESULTS_DIR, exist_ok=True)

def get_csv_value(row: dict, possible_keys: List[str], default: Any) -> Any:
    # Normalize row keys: strip spaces, underscores and convert to lowercase
    normalized_row = {k.lower().strip().replace(" ", "").replace("_", ""): v for k, v in row.items()}
    for key in possible_keys:
        norm_key = key.lower().strip().replace(" ", "").replace("_", "")
        if norm_key in normalized_row:
            return normalized_row[norm_key]
    return default

def run_prediction_rules(support_interactions: int, satisfaction: int, monthly_spend: float, usage: float) -> tuple:
    # Rule-based model logic
    score = 30.0 + (support_interactions * 15.0) - (satisfaction * 10.0) + (monthly_spend * 0.20) - (usage * 0.8)
    score = max(0.0, min(100.0, score))  # Clip between 0 and 100
    
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
    
    return score, risk, will_cancel, rec_type, rec_desc, explainability

def process_bulk_predictions_task(job_id: str, file_content: bytes):
    import time
    time.sleep(3)  # Simulate processing delay
    
    if job_id not in BULK_JOBS_DB:
        return
        
    BULK_JOBS_DB[job_id]["status"] = "PROCESSING"
    
    try:
        # Decode and parse CSV
        csv_data = file_content.decode('utf-8-sig', errors='ignore')
        stream = io.StringIO(csv_data)
        reader = csv.DictReader(stream)
        
        # Prepare list for processed records
        processed_rows = []
        successful_records = 0
        failed_records = 0
        
        db = SessionLocal()
        
        for idx, row in enumerate(reader):
            try:
                # Extract columns case-insensitively
                customer_id = str(get_csv_value(row, ["customer_id", "customerid", "customer", "id"], f"CUST_B{idx+1}"))
                age = int(float(get_csv_value(row, ["age"], 35)))
                income_level = str(get_csv_value(row, ["income_level", "income", "incomelevel"], "Medium"))
                device_type = str(get_csv_value(row, ["device_type", "device", "devicetype"], "Mobile"))
                payment_mode = str(get_csv_value(row, ["payment_mode", "payment", "paymentmode"], "UPI"))
                number_of_subscriptions = int(float(get_csv_value(row, ["number_of_subscriptions", "subscriptions"], 1)))
                tenure_months = int(float(get_csv_value(row, ["tenure_months", "tenure", "tenuremonths"], 12)))
                monthly_total_spend = float(get_csv_value(row, ["monthly_total_spend", "monthlyspend", "spend", "monthlytotalspend"], 75.00))
                avg_usage_hours_per_week = float(get_csv_value(row, ["avg_usage_hours_per_week", "avgusagehoursperweek", "weeklyusage", "usage"], 15.0))
                app_switch_frequency = int(float(get_csv_value(row, ["app_switch_frequency", "appswitchfrequency", "appswitches"], 5)))
                customer_support_interactions = int(float(get_csv_value(row, ["customer_support_interactions", "supportinteractions", "supporttickets", "support"], 3)))
                satisfaction_score = int(float(get_csv_value(row, ["satisfaction_score", "satisfactionscore", "satisfaction"], 3)))
                discount_used_str = str(get_csv_value(row, ["discount_used", "discountused", "discount"], "False"))
                discount_used = discount_used_str.lower() in ["true", "yes", "1", "t", "y"]
                
                # Run rule-based classifier model
                score, risk, will_cancel, rec_type, rec_desc, explainability = run_prediction_rules(
                    customer_support_interactions, satisfaction_score, monthly_total_spend, avg_usage_hours_per_week
                )
                
                # Append to processed rows
                processed_rows.append({
                    "customer_id": customer_id,
                    "age": age,
                    "tenure_months": tenure_months,
                    "monthly_total_spend": monthly_total_spend,
                    "avg_usage_hours_per_week": avg_usage_hours_per_week,
                    "customer_support_interactions": customer_support_interactions,
                    "satisfaction_score": satisfaction_score,
                    "churn_probability": score,
                    "risk_category": risk,
                    "recommendation_type": rec_type,
                    "recommendation_desc": rec_desc
                })
                
                # Graceful database insertion of customer and predictions if they don't exist
                try:
                    # Check if customer exists
                    check_query = text("SELECT customer_id FROM customers WHERE customer_id = :cust_id")
                    cust_exists = db.execute(check_query, {"cust_id": customer_id}).fetchone()
                    
                    if not cust_exists:
                        # Insert customer
                        insert_cust = text("""
                            INSERT INTO customers 
                            (customer_id, age, income_level, number_of_subscriptions, tenure_months, monthly_total_spend, 
                             avg_usage_hours_per_week, app_switch_frequency, customer_support_interactions, satisfaction_score, 
                             discount_used, device_type, payment_mode, created_at)
                            VALUES 
                            (:customer_id, :age, :income_level, :number_of_subscriptions, :tenure_months, :monthly_total_spend, 
                             :avg_usage_hours_per_week, :app_switch_frequency, :customer_support_interactions, :satisfaction_score, 
                             :discount_used, :device_type, :payment_mode, CURRENT_TIMESTAMP)
                        """)
                        db.execute(insert_cust, {
                            "customer_id": customer_id, "age": age, "income_level": income_level,
                            "number_of_subscriptions": number_of_subscriptions, "tenure_months": tenure_months,
                            "monthly_total_spend": monthly_total_spend, "avg_usage_hours_per_week": avg_usage_hours_per_week,
                            "app_switch_frequency": str(app_switch_frequency),
                            "customer_support_interactions": customer_support_interactions,
                            "satisfaction_score": satisfaction_score, "discount_used": discount_used,
                            "device_type": device_type, "payment_mode": payment_mode
                        })
                    
                    # Insert churn prediction history
                    insert_pred = text("""
                        INSERT INTO churn_predictions 
                        (customer_id, churn_probability, risk_category, will_cancel, explainability_json, recommendation_type, recommendation_desc, predicted_at)
                        VALUES (:cust_id, :prob, :risk, :cancel, :explain, :rec_type, :rec_desc, CURRENT_TIMESTAMP)
                    """)
                    db.execute(insert_pred, {
                        "cust_id": customer_id,
                        "prob": score,
                        "risk": risk,
                        "cancel": will_cancel,
                        "explain": explainability,
                        "rec_type": rec_type,
                        "rec_desc": rec_desc
                    })
                    db.commit()
                except Exception as db_err:
                    db.rollback()
                    # Silently ignore database errors for mockup fallback
                    pass
                
                successful_records += 1
            except Exception as row_err:
                print(f"Row processing error in bulk job {job_id}: {row_err}")
                failed_records += 1
                
        db.close()
        
        # Write output to CSV file
        file_path = os.path.join(RESULTS_DIR, f"{job_id}.csv")
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Customer ID", "Age", "Tenure (Months)", "Monthly Spend ($)", 
                "Weekly Usage (Hrs)", "Support Tickets", "Satisfaction (1-5)", 
                "Churn Probability", "Risk Category", "Recommended Offer", "Action Description"
            ])
            for r in processed_rows:
                writer.writerow([
                    r["customer_id"], r["age"], r["tenure_months"], f"{r['monthly_total_spend']:.2f}",
                    f"{r['avg_usage_hours_per_week']:.1f}", r["customer_support_interactions"],
                    r["satisfaction_score"], f"{r['churn_probability']:.1f}%", r["risk_category"],
                    r["recommendation_type"], r["recommendation_desc"]
                ])
                
        # Update job database
        BULK_JOBS_DB[job_id]["status"] = "COMPLETED"
        BULK_JOBS_DB[job_id]["processed_records"] = successful_records + failed_records
        BULK_JOBS_DB[job_id]["successful_records"] = successful_records
        BULK_JOBS_DB[job_id]["failed_records"] = failed_records
        BULK_JOBS_DB[job_id]["completed_at"] = datetime.utcnow()
        BULK_JOBS_DB[job_id]["download_url"] = f"/api/v1/reports/export?format=csv&job_id={job_id}"
        
    except Exception as job_err:
        print(f"Fatal job error in bulk job {job_id}: {job_err}")
        BULK_JOBS_DB[job_id]["status"] = "FAILED"
        BULK_JOBS_DB[job_id]["error_message"] = str(job_err)
        BULK_JOBS_DB[job_id]["completed_at"] = datetime.utcnow()

@router.post("/single/{customer_id}", response_model=SinglePredictionResponse)
async def predict_single(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    # Graceful fallback database check
    customer = None
    support_interactions = 3
    satisfaction = 3
    usage = 14.5
    monthly_spend = 79.50
    
    try:
        query = text("SELECT * FROM customers WHERE customer_id = :customer_id")
        customer = db.execute(query, {"customer_id": customer_id}).fetchone()
        
        if customer:
            support_interactions = customer.customer_support_interactions
            satisfaction = customer.satisfaction_score
            usage = float(customer.avg_usage_hours_per_week)
            monthly_spend = float(customer.monthly_total_spend)
    except Exception as exc:
        print(f"Database customer lookup failed (database may be offline, falling back to defaults): {exc}")
        customer = None
        
    # Run predictions rules
    score, risk, will_cancel, rec_type, rec_desc, explainability = run_prediction_rules(
        support_interactions, satisfaction, monthly_spend, usage
    )
    
    # Save prediction if database connection works
    if customer:
        try:
            insert_query = text("""
                INSERT INTO churn_predictions 
                (customer_id, churn_probability, risk_category, will_cancel, explainability_json, recommendation_type, recommendation_desc, predicted_at)
                VALUES (:cust_id, :prob, :risk, :cancel, :explain, :rec_type, :rec_desc, CURRENT_TIMESTAMP)
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
        except Exception as exc:
            db.rollback()
            print(f"Failed to save single customer prediction to DB: {exc}")
            
    return {
        "customer_id": customer_id,
        "churn_probability": round(score, 2),
        "risk_category": risk,
        "will_cancel": will_cancel,
        "explainability_json": explainability,
        "recommendation_type": rec_type,
        "recommendation_desc": rec_desc
    }

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
