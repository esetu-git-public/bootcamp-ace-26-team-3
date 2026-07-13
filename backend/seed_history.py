import os
import sys
import datetime
from sqlalchemy import text

# Add the parent directory to Python path to import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import PredictionHistory, ChurnPrediction

def seed_prediction_history():
    db = SessionLocal()
    try:
        print("Clearing existing prediction history...")
        db.execute(text("DELETE FROM prediction_history"))
        db.commit()

        print("Fetching current predictions...")
        # Get all current predictions to base history off
        current_preds = db.query(ChurnPrediction).all()
        total_customers = len(current_preds)
        print(f"Found {total_customers} customers. Generating history...")

        # We will generate monthly history snapshots for 5 historical months:
        # Months: Feb, Mar, Apr, May, Jun 2026 (plus the current July 2026 data in predictions)
        months_offsets = [
            (5, datetime.datetime(2026, 2, 11, 12, 0, 0)),
            (4, datetime.datetime(2026, 3, 11, 12, 0, 0)),
            (3, datetime.datetime(2026, 4, 11, 12, 0, 0)),
            (2, datetime.datetime(2026, 5, 11, 12, 0, 0)),
            (1, datetime.datetime(2026, 6, 11, 12, 0, 0)),
        ]

        history_records = []
        batch_size = 10000

        for pred in current_preds:
            current_prob = float(pred.churn_probability)
            
            # For each historical month, we apply a small drift:
            # Let's say risk was higher in the past (retention actions improved it over time)
            for idx, (month_ago, eval_time) in enumerate(months_offsets):
                # Monthly drifts: older records have higher risk.
                # Adding some slight noise per customer so it's not a uniform shift.
                hash_val = hash(pred.customer_id) % 100
                noise = (hash_val - 50) / 10.0 # -5 to +5% noise
                
                # Drift: risk increases as we go backward in time
                # e.g., Month 1: +1.5%, Month 2: +3.0%, Month 3: +4.5%, Month 4: +6.0%, Month 5: +7.5%
                drift = month_ago * 1.5
                
                hist_prob = min(100.0, max(0.0, current_prob + drift + noise))
                
                if hist_prob >= 70.0:
                    cat = "High"
                    res = 1
                elif hist_prob >= 30.0:
                    cat = "Medium"
                    res = 1
                else:
                    cat = "Low"
                    res = 0

                history_records.append({
                    "customer_id": pred.customer_id,
                    "risk_score": round(hist_prob, 2),
                    "risk_category": cat,
                    "prediction_result": res,
                    "evaluated_at": eval_time
                })

            # Check if we should insert a batch
            if len(history_records) >= batch_size:
                db.execute(
                    text("""
                        INSERT INTO prediction_history (customer_id, risk_score, risk_category, prediction_result, evaluated_at)
                        VALUES (:customer_id, :risk_score, :risk_category, :prediction_result, :evaluated_at)
                    """),
                    history_records
                )
                db.commit()
                history_records = []

        # Insert remaining records
        if history_records:
            db.execute(
                text("""
                    INSERT INTO prediction_history (customer_id, risk_score, risk_category, prediction_result, evaluated_at)
                    VALUES (:customer_id, :risk_score, :risk_category, :prediction_result, :evaluated_at)
                """),
                history_records
            )
            db.commit()

        # Let's verify total records in history
        history_count = db.query(PredictionHistory).count()
        print(f"Seeding completed successfully! Inserted {history_count} history records.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding prediction history: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_prediction_history()
