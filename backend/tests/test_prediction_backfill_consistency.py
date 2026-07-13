import pytest
from datetime import datetime, timezone
from sqlalchemy import text
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models import ChurnPrediction, Customer, PredictionHistory

@pytest.fixture
def test_context():
    client = TestClient(app)
    db = SessionLocal()
    
    # Get auth token using seeded admin
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create test customer with no prediction
    cust_id = "BACKFILL_TEST_CUST_1"
    db.query(ChurnPrediction).filter(ChurnPrediction.customer_id == cust_id).delete()
    db.query(PredictionHistory).filter(PredictionHistory.customer_id == cust_id).delete()
    db.query(Customer).filter(Customer.customer_id == cust_id).delete()
    db.commit()
    
    customer = Customer(
        customer_id=cust_id,
        age=30,
        income_level="High",
        number_of_subscriptions=1,
        tenure_months=24,
        monthly_total_spend=120.00,
        avg_usage_hours_per_week=20.0,
        app_switch_frequency=2,
        customer_support_interactions=0,
        satisfaction_score=9,
        discount_used=True,
        device_type="iOS",
        payment_mode="Credit Card"
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    yield client, db, cust_id, headers
    
    # Cleanup after test
    db.query(ChurnPrediction).filter(ChurnPrediction.customer_id == cust_id).delete()
    db.query(PredictionHistory).filter(PredictionHistory.customer_id == cust_id).delete()
    db.query(Customer).filter(Customer.customer_id == cust_id).delete()
    db.commit()
    db.close()


def test_customer_list_auto_ensures_prediction(test_context):
    client, db, cust_id, headers = test_context
    
    # Verify customer does not have any prediction initially
    pred_count = db.query(ChurnPrediction).filter(ChurnPrediction.customer_id == cust_id).count()
    assert pred_count == 0
    
    # 1. Fetching list of customers should trigger on-the-fly calculation and save it
    response = client.get(f"/api/v1/customers?search_id={cust_id}", headers=headers)
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) > 0
    row = next(r for r in results if r["customer_id"] == cust_id)
    
    # Verify it returned a valid prediction instead of Pending
    assert row["risk_category"] != "Pending"
    assert row["churn_probability"] is not None
    assert row["churn_probability"] >= 0
    
    # Verify it has actually saved it in the database
    db.expire_all()
    saved_pred = db.query(ChurnPrediction).filter(ChurnPrediction.customer_id == cust_id).first()
    assert saved_pred is not None
    assert float(saved_pred.churn_probability) == row["churn_probability"]


def test_customer_profile_auto_ensures_prediction(test_context):
    client, db, cust_id, headers = test_context
    
    # Verify customer does not have any prediction initially
    pred_count = db.query(ChurnPrediction).filter(ChurnPrediction.customer_id == cust_id).count()
    assert pred_count == 0
    
    # 2. Fetching single profile should trigger auto-ensure on-the-fly and return it
    response = client.get(f"/api/v1/customers/{cust_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    
    assert data["risk_category"] != "Pending"
    assert data["churn_probability"] is not None
    assert data["predicted_at"] is not None
    
    db.expire_all()
    saved_pred = db.query(ChurnPrediction).filter(ChurnPrediction.customer_id == cust_id).first()
    assert saved_pred is not None



def test_prediction_backfill_and_recalculate_endpoints(test_context):
    client, db, cust_id, headers = test_context
    
    # Verify customer does not have any prediction initially
    pred_count = db.query(ChurnPrediction).filter(ChurnPrediction.customer_id == cust_id).count()
    assert pred_count == 0
    
    # 3. Call backfill endpoint
    backfill_res = client.post("/api/v1/predictions/backfill-missing", headers=headers)
    assert backfill_res.status_code == 200
    backfill_data = backfill_res.json()
    assert backfill_data["status"] == "success"
    
    # Check that a prediction was created for our test customer
    db.expire_all()
    saved_pred1 = db.query(ChurnPrediction).filter(ChurnPrediction.customer_id == cust_id).first()
    assert saved_pred1 is not None
    pred_id_original = saved_pred1.prediction_id
    
    # 4. Call backfill again - verify it does NOT overwrite or recreate predictions for existing customers
    backfill_res2 = client.post("/api/v1/predictions/backfill-missing", headers=headers)
    assert backfill_res2.status_code == 200
    # Our test customer already has a prediction, so it shouldn't create a new one
    db.expire_all()
    saved_pred2 = db.query(ChurnPrediction).filter(ChurnPrediction.customer_id == cust_id).order_by(ChurnPrediction.prediction_id.desc()).first()
    assert saved_pred2.prediction_id == pred_id_original
    
    # 5. Call recalculate-all - verify it calculates a new prediction
    recalc_res = client.post(f"/api/v1/predictions/recalculate-all?customer_id={cust_id}", headers=headers)
    assert recalc_res.status_code == 200
    
    db.expire_all()
    # Check if there is now a newer prediction row for the customer
    predictions = db.query(ChurnPrediction).filter(ChurnPrediction.customer_id == cust_id).order_by(ChurnPrediction.prediction_id.desc()).all()
    assert len(predictions) > 1
    assert predictions[0].prediction_id > pred_id_original


def test_customers_list_risk_desc_sorting(test_context):
    client, db, cust_id, headers = test_context
    
    # Seed 10 customers with IDs 'SORT_99901' to 'SORT_99910'.
    test_ids = [f"SORT_999{i:02d}" for i in range(1, 11)]
    for tid in test_ids:
        db.query(ChurnPrediction).filter(ChurnPrediction.customer_id == tid).delete()
        db.query(PredictionHistory).filter(PredictionHistory.customer_id == tid).delete()
        db.query(Customer).filter(Customer.customer_id == tid).delete()
    db.commit()
    
    # First 6 customers ('SORT_99901' to 'SORT_99906') are low risk
    for tid in test_ids[:6]:
        c = Customer(
            customer_id=tid,
            age=30,
            income_level="High",
            number_of_subscriptions=1,
            tenure_months=24,
            monthly_total_spend=120.00,
            avg_usage_hours_per_week=20.0,
            app_switch_frequency=2,
            customer_support_interactions=0,
            satisfaction_score=9,
            discount_used=True,
            device_type="iOS",
            payment_mode="Credit Card"
        )
        db.add(c)
    
    # Last 4 customers ('SORT_99907' to 'SORT_99910') are high risk
    for tid in test_ids[6:]:
        c = Customer(
            customer_id=tid,
            age=30,
            income_level="Low",
            number_of_subscriptions=1,
            tenure_months=1,
            monthly_total_spend=120.00,
            avg_usage_hours_per_week=20.0,
            app_switch_frequency=2,
            customer_support_interactions=10,
            satisfaction_score=1,
            discount_used=False,
            device_type="iOS",
            payment_mode="Credit Card"
        )
        db.add(c)
    db.commit()
    
    # Calculate predictions for all of them
    for tid in test_ids:
        from backend.app.core.prediction_service import ensure_customer_has_prediction
        ensure_customer_has_prediction(db, tid)
        
    db.expire_all()
    
    # Query /api/v1/customers?limit=6&sort_by=risk_desc&search_id=SORT_999
    # The true top 4 risky customers (SORT_99907-SORT_99910) must be in the first 4 results.
    response = client.get("/api/v1/customers?limit=6&sort_by=risk_desc&search_id=SORT_999", headers=headers)
    assert response.status_code == 200
    results = response.json()["results"]
    
    returned_ids = [r["customer_id"] for r in results]
    
    # Assert high risk IDs are present first
    for high_risk_id in test_ids[6:]:
        assert high_risk_id in returned_ids
        
    assert returned_ids[0] in test_ids[6:]
    assert returned_ids[1] in test_ids[6:]
    assert returned_ids[2] in test_ids[6:]
    assert returned_ids[3] in test_ids[6:]
    
    # Clean up test data
    for tid in test_ids:
        db.query(ChurnPrediction).filter(ChurnPrediction.customer_id == tid).delete()
        db.query(PredictionHistory).filter(PredictionHistory.customer_id == tid).delete()
        db.query(Customer).filter(Customer.customer_id == tid).delete()
    db.commit()


def test_recommendation_classification_rules(test_context, monkeypatch):
    client, db, cust_id, headers = test_context
    from backend.app.core.prediction_service import calculate_prediction_for_customer
    from backend.app.core.model_service import model_service
    
    # Force rule-based prediction to verify recommendation engine mappings deterministically
    monkeypatch.setattr(model_service, "champion_version", None)

    
    # 1. High risk customer case: low satisfaction, high support
    high_risk_cust = Customer(
        customer_id="REC_TEST_HIGH",
        age=30,
        income_level="Low",
        number_of_subscriptions=1,
        tenure_months=12,
        monthly_total_spend=50.00,
        avg_usage_hours_per_week=10.0,
        app_switch_frequency=15,
        customer_support_interactions=8,
        satisfaction_score=1,
        discount_used=False,
        device_type="Android",
        payment_mode="UPI"
    )
    res_high = calculate_prediction_for_customer(db, high_risk_cust)
    assert res_high["risk_category"] == "High"
    assert "High (Urgent)" in res_high["recommendation_desc"]
    assert "Schedule a direct follow-up call" in res_high["recommendation_desc"]
    
    # 2. Medium risk customer case
    med_risk_cust = Customer(
        customer_id="REC_TEST_MED",
        age=30,
        income_level="Medium",
        number_of_subscriptions=1,
        tenure_months=12,
        monthly_total_spend=50.00,
        avg_usage_hours_per_week=10.0,
        app_switch_frequency=2,
        customer_support_interactions=4,
        satisfaction_score=4,
        discount_used=False,
        device_type="Android",
        payment_mode="UPI"
    )
    res_med = calculate_prediction_for_customer(db, med_risk_cust)

    assert res_med["risk_category"] == "Medium"
    assert "Medium (Proactive)" in res_med["recommendation_desc"]
    assert "feedback survey" in res_med["recommendation_desc"]
    
    # 3. Low risk customer case: high satisfaction, low support
    low_risk_cust = Customer(
        customer_id="REC_TEST_LOW",
        age=30,
        income_level="High",
        number_of_subscriptions=1,
        tenure_months=24,
        monthly_total_spend=50.00,
        avg_usage_hours_per_week=20.0,
        app_switch_frequency=1,
        customer_support_interactions=0,
        satisfaction_score=9,
        discount_used=False,
        device_type="iOS",
        payment_mode="Credit Card"
    )
    res_low = calculate_prediction_for_customer(db, low_risk_cust)
    assert res_low["risk_category"] == "Low"
    assert "Loyalty Reinforcement" in res_low["recommendation_type"]
    assert "aggressive discount" in res_low["recommendation_desc"]



