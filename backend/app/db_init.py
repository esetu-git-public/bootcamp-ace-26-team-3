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
        ) p ON c.customer_id = p.customer_id
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

    print(f"Seeding customer database from {csv_path}...")
    customers_to_insert: list[dict[str, Any]] = []
    predictions_to_insert: list[dict[str, Any]] = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= 1000:
                break

            support = int(row["Customer_Support_Interactions"])
            satisfaction = int(row["Satisfaction_Score"])
            spend = float(row["Monthly_Total_Spend"])
            usage = float(row["Avg_Usage_Hours_Per_Week"])
            cust_id = row["Customer_ID"]

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
                "discount_used": row["Discount_Used"] == "1",
                "device_type": row["Device_Type"],
                "payment_mode": row["Payment_Mode"],
            })

            profile = build_risk_profile(
                customer_support_interactions=support,
                satisfaction_score=satisfaction,
                monthly_total_spend=spend,
                avg_usage_hours_per_week=usage,
            )
            predictions_to_insert.append({
                "customer_id": cust_id,
                "churn_probability": profile["risk_score"],
                "risk_category": profile["risk_category"],
                "will_cancel": profile["will_cancel"],
                "explainability_json": profile["explainability_json"],
                "recommendation_type": profile["recommendation_type"],
                "recommendation_desc": profile["recommendation_desc"],
            })

    db.bulk_insert_mappings(Customer, customers_to_insert)
    db.commit()
    db.bulk_insert_mappings(ChurnPrediction, predictions_to_insert)
    db.commit()
    print(f"Successfully seeded {len(customers_to_insert)} customer records and prediction history.")
