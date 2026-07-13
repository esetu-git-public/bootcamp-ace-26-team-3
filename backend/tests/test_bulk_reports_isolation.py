import pytest
import io
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models import Customer, ChurnPrediction, BulkPredictionJob, BulkPredictionResult
from backend.app.routers.predictions import process_bulk_predictions_task

@pytest.fixture
def db_session():
    db = SessionLocal()
    yield db
    db.close()

def test_bulk_reports_isolation_and_insights(db_session):
    client = TestClient(app)
    
    # 1. Login to get token
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get current main dashboard customer count
    dashboard_res = client.get("/api/v1/dashboard/kpis", headers=headers)
    assert dashboard_res.status_code == 200
    initial_total_customers = dashboard_res.json()["total_customers"]
    
    # 2. Upload bulk predictions CSV file (isolated dataset)
    # Using customer IDs that do NOT exist in the main database
    upload_content = (
        "customer_id,age,income_level,device_type,payment_mode,number_of_subscriptions,"
        "tenure_months,monthly_total_spend,avg_usage_hours_per_week,app_switch_frequency,"
        "customer_support_interactions,satisfaction_score,discount_used\n"
        "ISOLATION_CUST_99901,34,Medium,Android,UPI,2,8,79.5,14.5,5,3,2,false\n"
        "ISOLATION_CUST_99902,45,High,iOS,Credit Card,1,20,120,25,2,1,8,true\n"
    ).encode("utf-8")
    
    # Upload via client
    response = client.post(
        "/api/v1/predictions/bulk",
        files={"file": ("test_isolation.csv", io.BytesIO(upload_content), "text/csv")},
        headers=headers
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    assert job_id is not None
    
    # Verify job completed successfully
    status_res = client.get(f"/api/v1/predictions/bulk/status/{job_id}", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "COMPLETED"
    
    # 3. VERIFY ISOLATION:
    # - Customer rows are NOT inserted into customers table
    cust1 = db_session.query(Customer).filter(Customer.customer_id == "ISOLATION_CUST_99901").first()
    cust2 = db_session.query(Customer).filter(Customer.customer_id == "ISOLATION_CUST_99902").first()
    assert cust1 is None
    assert cust2 is None
    
    # - Prediction records are NOT inserted into churn_predictions
    pred1 = db_session.query(ChurnPrediction).filter(ChurnPrediction.customer_id == "ISOLATION_CUST_99901").first()
    assert pred1 is None
    
    # - Main dashboard KPIs are UNCHANGED
    dashboard_res_after = client.get("/api/v1/dashboard/kpis", headers=headers)
    assert dashboard_res_after.status_code == 200
    assert dashboard_res_after.json()["total_customers"] == initial_total_customers
    
    # 4. VERIFY RESULTS PERSISTENCE:
    # - Bulk prediction results exist in bulk_prediction_results table
    bulk_results = db_session.query(BulkPredictionResult).filter(BulkPredictionResult.job_id == job_id).all()
    assert len(bulk_results) == 2
    assert {r.customer_id for r in bulk_results} == {"ISOLATION_CUST_99901", "ISOLATION_CUST_99902"}
    
    # 5. VERIFY ENDPOINTS:
    # - GET /api/v1/predictions/bulk/jobs
    jobs_res = client.get("/api/v1/predictions/bulk/jobs", headers=headers)
    assert jobs_res.status_code == 200
    job_ids = [j["job_id"] for j in jobs_res.json()]
    assert job_id in job_ids
    
    # - GET /api/v1/predictions/bulk/jobs/{job_id}/results
    results_res = client.get(f"/api/v1/predictions/bulk/jobs/{job_id}/results", headers=headers)
    assert results_res.status_code == 200
    assert results_res.json()["total"] == 2
    assert len(results_res.json()["results"]) == 2
    
    # - GET /api/v1/predictions/bulk/jobs/{job_id}/insights
    insights_res = client.get(f"/api/v1/predictions/bulk/jobs/{job_id}/insights", headers=headers)
    assert insights_res.status_code == 200
    insights_data = insights_res.json()
    assert insights_data["kpis"]["total_customers"] == 2
    assert insights_data["kpis"]["predicted_churn_customers"] >= 0
    assert len(insights_data["risk_distribution"]) == 3
    
    # - GET /api/v1/reports/bulk/{job_id}/pdf
    pdf_res = client.get(f"/api/v1/reports/bulk/{job_id}/pdf", headers=headers)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    
    # Clean up bulk prediction job & results
    db_session.query(BulkPredictionResult).filter(BulkPredictionResult.job_id == job_id).delete()
    db_session.query(BulkPredictionJob).filter(BulkPredictionJob.job_id == job_id).delete()
    db_session.commit()
