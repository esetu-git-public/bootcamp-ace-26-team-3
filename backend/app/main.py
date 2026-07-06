from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .models.user import User
from .core.risk_score import build_risk_profile
from . import models
from .routers import analytics, auth, customers, dashboard, model, predictions, reports
from .api.endpoints import explainability

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    Base.metadata.create_all(bind=engine)
    
    from .database import SessionLocal
    from passlib.context import CryptContext
    from sqlalchemy import text
    import csv
    import os
    from .models import Customer, ChurnPrediction

    db = SessionLocal()
    try:
        # 1. Create v_customer_predictions view (compatible with SQLite & Postgres)
        try:
            db.execute(text("DROP VIEW IF EXISTS v_customer_predictions CASCADE"))
            db.commit()
        except Exception:
            db.rollback()
            try:
                db.execute(text("DROP VIEW IF EXISTS v_customer_predictions"))
                db.commit()
            except Exception:
                db.rollback()

        db.execute(text("""
            CREATE VIEW v_customer_predictions AS
            SELECT
                c.customer_id,
                c.age,
                c.income_level,
                c.number_of_subscriptions,
                c.tenure_months,
                c.monthly_total_spend,
                c.avg_usage_hours_per_week,
                c.app_switch_frequency,
                c.customer_support_interactions,
                c.satisfaction_score,
                c.discount_used,
                c.device_type,
                c.payment_mode,
                p.prediction_id,
                p.churn_probability,
                p.risk_category,
                p.will_cancel,
                p.explainability_json,
                p.recommendation_type,
                p.recommendation_desc,
                p.predicted_at
            FROM customers c
            LEFT JOIN (
                SELECT * FROM churn_predictions
                WHERE prediction_id IN (
                    SELECT MAX(prediction_id) FROM churn_predictions GROUP BY customer_id
                )
            ) p ON c.customer_id = p.customer_id;
        """))
        db.commit()

        # Create supporting indexes for common analytics and search patterns
        for index_statement in [
            """
            CREATE INDEX IF NOT EXISTS idx_customers_lower_customer_id
            ON customers(LOWER(customer_id))
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_predictions_customer_predicted_at
            ON churn_predictions(customer_id, predicted_at DESC)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_predictions_risk_will
            ON churn_predictions(risk_category, will_cancel)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_prediction_history_customer_at
            ON prediction_history(customer_id, evaluated_at DESC)
            """,
        ]:
            db.execute(text(index_statement))
        db.commit()
        print("Database index recommendations created/verified.")

        # 2. Seed default admin user if none exists
        admin_exists = db.query(User).filter(User.username == "admin").first()
        if not admin_exists:
            pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
            default_admin = User(
                username="admin",
                email="admin@company.com",
                full_name="Administrator",
                hashed_password=pwd_context.hash("admin123"),
                is_active=True
            )
            db.add(default_admin)
            db.commit()
            print("Default admin user seeded successfully.")

        # 3. Seed customer and predictions from Subscription Fatigue.csv if empty
        if db.query(Customer).count() == 0:
            csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Subscription Fatigue.csv")
            if os.path.exists(csv_path):
                print(f"Seeding customer database from {csv_path}...")
                customers_to_insert = []
                predictions_to_insert = []
                
                with open(csv_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for i, row in enumerate(reader):
                        if i >= 1000:
                            break
                        
                        cust_id = row["Customer_ID"]
                        age = int(row["Age"])
                        income = row["Income_Level"]
                        subs = int(row["Number_of_Subscriptions"])
                        usage = float(row["Avg_Usage_Hours_Per_Week"])
                        switch = int(row["App_Switch_Frequency"])
                        discount = row["Discount_Used"] == "1"
                        support = int(row["Customer_Support_Interactions"])
                        pay = row["Payment_Mode"]
                        tenure = int(row["Tenure_Months"])
                        device = row["Device_Type"]
                        sat = int(row["Satisfaction_Score"])
                        spend = float(row["Monthly_Total_Spend"])
                        
                        customers_to_insert.append({
                            "customer_id": cust_id,
                            "age": age,
                            "income_level": income,
                            "number_of_subscriptions": subs,
                            "tenure_months": tenure,
                            "monthly_total_spend": spend,
                            "avg_usage_hours_per_week": usage,
                            "app_switch_frequency": switch,
                            "customer_support_interactions": support,
                            "satisfaction_score": sat,
                            "discount_used": discount,
                            "device_type": device,
                            "payment_mode": pay
                        })
                        
                        # Generate deterministic churn prediction score using centralized helper
                        profile = build_risk_profile(
                            customer_support_interactions=support,
                            satisfaction_score=sat,
                            monthly_total_spend=spend,
                            avg_usage_hours_per_week=usage,
                        )
                        score = profile["risk_score"]
                        risk = profile["risk_category"]
                        will_cancel = profile["will_cancel"]
                        rec_type = profile["recommendation_type"]
                        rec_desc = profile["recommendation_desc"]
                        explainability = profile["explainability_json"]
                        
                        predictions_to_insert.append({
                            "customer_id": cust_id,
                            "churn_probability": score,
                            "risk_category": risk,
                            "will_cancel": will_cancel,
                            "explainability_json": explainability,
                            "recommendation_type": rec_type,
                            "recommendation_desc": rec_desc
                        })
                
                db.bulk_insert_mappings(Customer, customers_to_insert)
                db.commit()
                db.bulk_insert_mappings(ChurnPrediction, predictions_to_insert)
                db.commit()
                print(f"Successfully seeded {len(customers_to_insert)} customer records and prediction history.")
    finally:
        db.close()
except Exception as exc:
    print(f"Database initialization/seeding failed: {exc}")

app.include_router(auth.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(customers.router, prefix="/api/v1")
app.include_router(predictions.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(model.router, prefix="/api/v1")
app.include_router(explainability.router, prefix="/api/v1")


@app.get("/")
def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
