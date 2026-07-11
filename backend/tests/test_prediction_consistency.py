import pytest
from sqlalchemy import text
from datetime import datetime, timezone, timedelta
from backend.app.models import ChurnPrediction, Customer, PredictionHistory

@pytest.fixture
def test_client_and_db():
    # Setup test client and DB session
    from fastapi.testclient import TestClient
    from backend.app.main import app
    from backend.app.database import SessionLocal
    
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
    
    # Create a test customer if not exists
    cust_id = "CONSISTENCY_TEST_CUSTOMER"
    customer = db.query(Customer).filter(Customer.customer_id == cust_id).first()
    if not customer:
        customer = Customer(
            customer_id=cust_id,
            age=40,
            income_level="Medium",
            number_of_subscriptions=2,
            tenure_months=12,
            monthly_total_spend=80.00,
            avg_usage_hours_per_week=15.0,
            app_switch_frequency=5,
            customer_support_interactions=2,
            satisfaction_score=3,
            discount_used=False,
            device_type="Desktop",
            payment_mode="Credit Card"
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        
    yield client, db, cust_id, headers
    
    # Cleanup predictions
    db.query(ChurnPrediction).filter(ChurnPrediction.customer_id == cust_id).delete()
    db.query(PredictionHistory).filter(PredictionHistory.customer_id == cust_id).delete()
    db.query(Customer).filter(Customer.customer_id == cust_id).delete()
    db.commit()
    db.close()


def test_prediction_consistency_and_ordering(test_client_and_db):
    client, db, cust_id, headers = test_client_and_db
    
    # Ensure there are no prior predictions for the customer
    db.query(ChurnPrediction).filter(ChurnPrediction.customer_id == cust_id).delete()
    db.query(PredictionHistory).filter(PredictionHistory.customer_id == cust_id).delete()
    db.commit()
    
    # Create prediction 1 (older, lower probability)
    pred_1_time = datetime.now(timezone.utc) - timedelta(hours=1)
    pred_1 = ChurnPrediction(
        customer_id=cust_id,
        churn_probability=15.50,
        risk_category="Low",
        will_cancel=0,
        explainability_json={},
        recommendation_type="No Action Required",
        recommendation_desc="Stable",
        predicted_at=pred_1_time,
        model_version="v1.0.0"
    )
    db.add(pred_1)
    db.commit()
    
    # Create prediction 2 (same timestamp, higher ID, higher probability)
    pred_2 = ChurnPrediction(
        customer_id=cust_id,
        churn_probability=85.00,
        risk_category="High",
        will_cancel=1,
        explainability_json={},
        recommendation_type="Offer Discount",
        recommendation_desc="High risk",
        predicted_at=pred_1_time,  # Identical timestamp to test tiebreaker
        model_version="v1.0.0"
    )
    db.add(pred_2)
    db.commit()
    db.refresh(pred_2)
    
    # Create prediction 3 (latest timestamp, medium probability)
    pred_3_time = datetime.now(timezone.utc)
    pred_3 = ChurnPrediction(
        customer_id=cust_id,
        churn_probability=45.00,
        risk_category="Medium",
        will_cancel=1,
        explainability_json={},
        recommendation_type="Upgrade Plan",
        recommendation_desc="Moderate risk",
        predicted_at=pred_3_time,
        model_version="v1.0.0"
    )
    db.add(pred_3)
    db.commit()
    db.refresh(pred_3)
    
    # 1. Query the v_customer_predictions view directly to verify ranking ordering
    # It must select pred_3 (since pred_3 has the latest predicted_at timestamp)
    view_query = text("SELECT * FROM v_customer_predictions WHERE customer_id = :customer_id")
    view_res = db.execute(view_query, {"customer_id": cust_id}).fetchone()
    assert view_res is not None
    assert float(view_res.churn_probability) == 45.00
    assert view_res.risk_category == "Medium"
    assert view_res.prediction_id == pred_3.prediction_id
    
    # 2. Verify via GET /customers endpoint
    list_response = client.get(f"/api/v1/customers?search_id={cust_id}", headers=headers)
    assert list_response.status_code == 200
    list_results = list_response.json()["results"]
    assert len(list_results) > 0
    cust_row = next(r for r in list_results if r["customer_id"] == cust_id)
    assert cust_row["churn_probability"] == 45.00
    assert cust_row["risk_category"] == "Medium"
    
    # 3. Verify via GET /customers/{customer_id} profile endpoint
    profile_response = client.get(f"/api/v1/customers/{cust_id}", headers=headers)
    assert profile_response.status_code == 200
    profile_data = profile_response.json()
    assert profile_data["churn_probability"] == 45.00
    assert profile_data["risk_category"] == "Medium"
    
    # 4. Trigger prediction recalculation via POST /predictions/single/{customer_id}
    predict_response = client.post(f"/api/v1/predictions/single/{cust_id}", headers=headers)
    assert predict_response.status_code == 200
    predict_data = predict_response.json()
    
    new_prob = predict_data["churn_probability"]
    new_risk = predict_data["risk_category"]
    
    # Verify it returned prediction_id, predicted_at, and model_version
    assert "prediction_id" in predict_data
    assert predict_data["prediction_id"] is not None
    assert "predicted_at" in predict_data
    assert "model_version" in predict_data
    
    # 5. Verify that GET /customers/{customer_id} and GET /customers now both return the recalculated values consistently
    updated_profile_response = client.get(f"/api/v1/customers/{cust_id}", headers=headers)
    assert updated_profile_response.status_code == 200
    updated_profile_data = updated_profile_response.json()
    assert updated_profile_data["churn_probability"] == new_prob
    assert updated_profile_data["risk_category"] == new_risk
    
    updated_list_response = client.get(f"/api/v1/customers?search_id={cust_id}", headers=headers)
    assert updated_list_response.status_code == 200
    updated_list_results = updated_list_response.json()["results"]
    updated_cust_row = next(r for r in updated_list_results if r["customer_id"] == cust_id)
    assert updated_cust_row["churn_probability"] == new_prob
    assert updated_cust_row["risk_category"] == new_risk


def test_customer_list_can_sort_by_risk_desc(test_client_and_db):
    client, db, _cust_id, headers = test_client_and_db
    customer_ids = ["990001", "990002", "990003", "990004"]
    risk_rows = [
        ("990001", "Low", 12.0),
        ("990002", "High", 80.0),
        ("990003", "Medium", 60.0),
        ("990004", "High", 90.0),
    ]

    try:
        db.query(ChurnPrediction).filter(ChurnPrediction.customer_id.in_(customer_ids)).delete(synchronize_session=False)
        db.query(PredictionHistory).filter(PredictionHistory.customer_id.in_(customer_ids)).delete(synchronize_session=False)
        db.query(Customer).filter(Customer.customer_id.in_(customer_ids)).delete(synchronize_session=False)
        db.commit()

        for customer_id, _risk_category, _probability in risk_rows:
            db.add(Customer(
                customer_id=customer_id,
                age=35,
                income_level="Medium",
                number_of_subscriptions=2,
                tenure_months=10,
                monthly_total_spend=75.00,
                avg_usage_hours_per_week=12.0,
                app_switch_frequency=4,
                customer_support_interactions=1,
                satisfaction_score=4,
                discount_used=False,
                device_type="Desktop",
                payment_mode="Credit Card"
            ))
        db.commit()

        for customer_id, risk_category, probability in risk_rows:
            db.add(ChurnPrediction(
                customer_id=customer_id,
                churn_probability=probability,
                risk_category=risk_category,
                will_cancel=1 if risk_category in ["High", "Medium"] else 0,
                explainability_json={},
                recommendation_type="Offer Discount" if risk_category == "High" else "No Action Required",
                recommendation_desc="Risk sort test",
                predicted_at=datetime.now(timezone.utc),
                model_version="test"
            ))
        db.commit()

        response = client.get("/api/v1/customers?search_id=99000&limit=4&sort_by=risk_desc", headers=headers)
        assert response.status_code == 200
        ordered_ids = [row["customer_id"] for row in response.json()["results"]]
        assert ordered_ids == ["990004", "990002", "990003", "990001"]
    finally:
        db.query(ChurnPrediction).filter(ChurnPrediction.customer_id.in_(customer_ids)).delete(synchronize_session=False)
        db.query(PredictionHistory).filter(PredictionHistory.customer_id.in_(customer_ids)).delete(synchronize_session=False)
        db.query(Customer).filter(Customer.customer_id.in_(customer_ids)).delete(synchronize_session=False)
        db.commit()
