import pytest
from backend.app.models import ChurnPrediction, Customer, PredictionHistory

@pytest.fixture
def sim_test_context():
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
    cust_id = "SIMULATION_TEST_CUSTOMER"
    customer = db.query(Customer).filter(Customer.customer_id == cust_id).first()
    if not customer:
        customer = Customer(
            customer_id=cust_id,
            age=38,
            income_level="Medium",
            number_of_subscriptions=3,
            tenure_months=24,
            monthly_total_spend=120.00,
            avg_usage_hours_per_week=20.0,
            app_switch_frequency=4,
            customer_support_interactions=5,
            satisfaction_score=2, # high support interactions and low satisfaction = high risk
            discount_used=False,
            device_type="iOS",
            payment_mode="Debit Card"
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        
    yield client, db, cust_id, headers
    
    # Cleanup temporary test customer details
    db.query(ChurnPrediction).filter(ChurnPrediction.customer_id == cust_id).delete()
    db.query(PredictionHistory).filter(PredictionHistory.customer_id == cust_id).delete()
    db.query(Customer).filter(Customer.customer_id == cust_id).delete()
    db.commit()
    db.close()


def test_what_if_simulation_endpoint(sim_test_context):
    client, db, cust_id, headers = sim_test_context
    
    # 1. Run baseline prediction first to establish a prediction baseline in the database
    baseline_response = client.post(f"/api/v1/predictions/single/{cust_id}", headers=headers)
    assert baseline_response.status_code == 200
    baseline_data = baseline_response.json()
    baseline_prob = baseline_data["churn_probability"]
    
    # Verify baseline is stored
    db_predictions_count_before = db.query(ChurnPrediction).filter(ChurnPrediction.customer_id == cust_id).count()
    assert db_predictions_count_before > 0
    
    # Record database state of customer details
    cust_before = db.query(Customer).filter(Customer.customer_id == cust_id).first()
    assert cust_before.satisfaction_score == 2
    assert cust_before.customer_support_interactions == 5
    
    # 2. Trigger What-If Simulation API with overrides (e.g. increase satisfaction to 10, support tickets to 0)
    overrides = {
        "satisfaction_score": 10,
        "customer_support_interactions": 0,
        "monthly_total_spend": 50.0,
        "discount_used": True
      }
      
    sim_response = client.post(f"/api/v1/predictions/simulate/{cust_id}", json=overrides, headers=headers)
    assert sim_response.status_code == 200
    sim_data = sim_response.json()
    
    # Simulated risk should be significantly lower than the baseline high-risk scenario
    assert "churn_probability" in sim_data
    assert sim_data["churn_probability"] < baseline_prob
    assert sim_data["risk_category"] == "Low"
    assert sim_data["explainability"] is not None
    
    # 3. CRITICAL CONSTRAINT: Verify database was NOT changed
    # A. Number of stored prediction rows must be unchanged
    db_predictions_count_after = db.query(ChurnPrediction).filter(ChurnPrediction.customer_id == cust_id).count()
    assert db_predictions_count_after == db_predictions_count_before
    
    # B. Customer record details in DB must be untouched
    cust_after = db.query(Customer).filter(Customer.customer_id == cust_id).first()
    assert cust_after.satisfaction_score == 2
    assert cust_after.customer_support_interactions == 5
    assert cust_after.monthly_total_spend == 120.00
    assert cust_after.discount_used is False
