import csv
import os
from typing import Any

from passlib.context import CryptContext
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from .core.risk_score import build_risk_profile
from .models import ChurnPrediction, Customer
from .models.user import User


def initialize_database(engine: Engine, db: Session) -> None:
    create_customer_predictions_view(engine, db)
    create_indexes(db)
    seed_default_admin(db)
    seed_demo_customers(db)


def create_customer_predictions_view(engine: Engine, db: Session) -> None:
    if engine.dialect.name == "postgresql":
        db.execute(text("DROP VIEW IF EXISTS v_customer_predictions CASCADE"))
    else:
        db.execute(text("DROP VIEW IF EXISTS v_customer_predictions"))
    db.commit()

    db.execute(text("""
        CREATE VIEW v_customer_predictions AS
        WITH latest_predictions AS (
            SELECT
                p.*,
                ROW_NUMBER() OVER(PARTITION BY p.customer_id ORDER BY p.predicted_at DESC, p.prediction_id DESC) as rn
            FROM churn_predictions p
        )
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
            c.created_at,
            lp.prediction_id,
            lp.churn_probability,
            lp.risk_category,
            lp.will_cancel,
            lp.explainability_json,
            lp.recommendation_type,
            lp.recommendation_desc,
            lp.predicted_at,
            lp.model_version
        FROM customers c
        LEFT JOIN latest_predictions lp ON c.customer_id = lp.customer_id AND lp.rn = 1
    """))
    db.commit()


def create_indexes(db: Session) -> None:
    index_statements = [
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
        """
        CREATE INDEX IF NOT EXISTS idx_bulk_prediction_jobs_status_created
        ON bulk_prediction_jobs(status, created_at DESC)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_retention_interventions_customer_created
        ON retention_interventions(customer_id, created_at DESC)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_retention_interventions_status
        ON retention_interventions(status)
        """,
    ]

    for statement in index_statements:
        db.execute(text(statement))
    db.commit()


def seed_default_admin(db: Session) -> None:
    admin_exists = db.query(User).filter(User.username == "admin").first()
    if admin_exists:
        return

    pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
    db.add(User(
        username="admin",
        email="admin@company.com",
        full_name="Administrator",
        hashed_password=pwd_context.hash("admin123"),
        is_active=True,
    ))
    db.commit()
    print("Default admin user seeded successfully.")


def seed_demo_customers(db: Session) -> None:
    if db.query(Customer).count() > 0:
        return

    csv_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "Subscription Fatigue.csv",
    )
    if not os.path.exists(csv_path):
        return

    print(f"Seeding customer database from {csv_path} using ML model predictions...")
    import pandas as pd
    from .core.model_service import model_service
    from .core.risk_score import build_explainability

    df = pd.read_csv(csv_path)

    # 1. Extract raw features for prediction
    X_raw = df.drop(columns=["Customer_ID", "Will_Cancel_Next_3_Months"], errors="ignore")

    # 2. Compute predictions in a fast single batch call
    processed = model_service.preprocessor.transform(X_raw)
    probabilities = model_service.model.predict_proba(processed)[:, 1]

    customers_to_insert: list[dict[str, Any]] = []
    predictions_to_insert: list[dict[str, Any]] = []

    def get_risk_info(prob: float):
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

    for idx, row in df.iterrows():
        cust_id = str(row["Customer_ID"])
        support = int(row["Customer_Support_Interactions"])
        satisfaction = int(row["Satisfaction_Score"])
        spend = float(row["Monthly_Total_Spend"])
        usage = float(row["Avg_Usage_Hours_Per_Week"])

        customers_to_insert.append({
            "customer_id": cust_id,
            "age": int(row["Age"]),
            "income_level": row["Income_Level"],
            "number_of_subscriptions": int(row["Number_of_Subscriptions"]),
            "tenure_months": int(row["Tenure_Months"]),
            "monthly_total_spend": spend,
            "avg_usage_hours_per_week": usage,
            "app_switch_frequency": int(row["App_Switch_Frequency"]),
            "customer_support_interactions": support,
            "satisfaction_score": satisfaction,
            "discount_used": row["Discount_Used"] == 1 or str(row["Discount_Used"]).strip() == "1",
            "device_type": row["Device_Type"],
            "payment_mode": row["Payment_Mode"],
        })

        prob = float(probabilities[idx])
        risk_category, will_cancel, rec_type, rec_desc = get_risk_info(prob)
        explainability = build_explainability(support, satisfaction, spend, usage)

        predictions_to_insert.append({
            "customer_id": cust_id,
            "churn_probability": round(prob * 100.0, 2),
            "risk_category": risk_category,
            "will_cancel": will_cancel,
            "explainability_json": explainability,
            "recommendation_type": rec_type,
            "recommendation_desc": rec_desc,
        })

    db.bulk_insert_mappings(Customer, customers_to_insert)
    db.commit()
    db.bulk_insert_mappings(ChurnPrediction, predictions_to_insert)
    db.commit()
    print(f"Successfully seeded {len(customers_to_insert)} customer records and prediction history using CatBoost predictions.")
