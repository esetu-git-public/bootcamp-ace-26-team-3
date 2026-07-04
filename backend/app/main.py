# backend/app/main.py
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
from app.schemas import CustomerValidationSchema # Imports our validator from Step 2

app = FastAPI(
    title="Subscription Churn Prediction API",
    description="APIs for Customer Management and Churn Prediction",
    version="1.0"
)

# Enable CORS so your React frontend can talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Temporary in-memory database for testing
mock_db: Dict[str, dict] = {}
prediction_history_db: List[dict] = []

@app.get("/")
def read_root():
    return {"message": "Welcome to the Subscription Cancellation Prediction API"}

# --- CUSTOMER CRUD ENDPOINTS ---

@app.post("/api/v1/customers", status_code=status.HTTP_201_CREATED)
def create_customer(customer: CustomerValidationSchema):
    """
    Creates a new customer record. Automatically runs validation.
    """
    if customer.customer_id in mock_db:
        raise HTTPException(status_code=400, detail="Customer already exists")
    
    # Store in memory
    mock_db[customer.customer_id] = customer.dict()
    return {"status": "success", "message": f"Customer {customer.customer_id} saved successfully."}

@app.get("/api/v1/customers/{customer_id}")
def get_customer(customer_id: str):
    """
    Retrieves a single customer profile.
    """
    if customer_id not in mock_db:
        raise HTTPException(status_code=404, detail="Customer not found")
    return mock_db[customer_id]

# --- CHURN PREDICTION ENDPOINT ---

@app.post("/api/v1/predict/{customer_id}")
def predict_churn(customer_id: str):
    """
    Runs prediction for a customer and logs it to Prediction History.
    """
    if customer_id not in mock_db:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    customer_data = mock_db[customer_id]
    
    # Simple rule-based logic representing our model output for now
    # If satisfaction is low and spend is high, they are likely to churn
    satisfaction = customer_data["satisfaction_score"]
    spend = customer_data["monthly_total_spend"]
    
    if satisfaction <= 2 or spend > 100:
        risk_score = 85.50
        risk_category = "HIGH"
        prediction_result = 1 # Likely to cancel
    else:
        risk_score = 15.20
        risk_category = "LOW"
        prediction_result = 0 # Not likely to cancel
        
    # LOG TO PREDICTION HISTORY
    history_log = {
        "history_id": len(prediction_history_db) + 1,
        "customer_id": customer_id,
        "risk_score": risk_score,
        "risk_category": risk_category,
        "prediction_result": prediction_result
    }
    prediction_history_db.append(history_log)
    
    return {
        "customer_id": customer_id,
        "prediction": prediction_result,
        "risk_score": risk_score,
        "risk_category": risk_category,
        "reasons": ["Low satisfaction score" if satisfaction <= 2 else "Optimal engagement"]
    }

# --- PREDICTION HISTORY ENDPOINT ---

@app.get("/api/v1/predictions/history/{customer_id}")
def get_prediction_history(customer_id: str):
    """
    Retrieves past prediction logs for a specific customer.
    """
    history = [log for log in prediction_history_db if log["customer_id"] == customer_id]
    return {"customer_id": customer_id, "history": history}