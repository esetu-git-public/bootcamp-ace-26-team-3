import json
import pandas as pd
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.models import ChurnPrediction, PredictionHistory, Customer
from backend.app.core.risk_score import build_risk_profile
from backend.app.core.model_service import model_service

def risk_from_probability(prob: float) -> tuple[str, int]:
    if prob >= 0.7:
        return "High", 1
    if prob >= 0.3:
        return "Medium", 1
    return "Low", 0

def generate_recommendation_details(
    prob: float,
    risk_category: str,
    satisfaction_score: int,
    monthly_total_spend: float,
    tenure_months: int,
    customer_support_interactions: int,
    avg_usage_hours_per_week: float,
    app_switch_frequency: int
) -> tuple[str, str]:
    if risk_category == "High":
        if customer_support_interactions >= 5 and satisfaction_score <= 3:
            rec_type = "High Touch Intervention"
            rec_desc = (
                f"Why this customer is at risk: Customer is experiencing severe friction with "
                f"{customer_support_interactions} support interactions and a low satisfaction score of {satisfaction_score}/10.\n"
                f"Recommended action: Schedule a direct follow-up call from a senior customer success lead to address open tickets.\n"
                f"Priority: High (Urgent)\n"
                f"Expected impact: Resolves underlying support issues and restores trust.\n"
                f"Next step: Personal support outreach"
            )
        elif tenure_months <= 3:
            rec_type = "Early-Stage Retainer"
            rec_desc = (
                f"Why this customer is at risk: New customer showing early warning signs of churn with "
                f"high spend (${monthly_total_spend:.2f}) and low initial engagement.\n"
                f"Recommended action: Send a personalized onboarding assistance email with a guide to key features.\n"
                f"Priority: High (Urgent)\n"
                f"Expected impact: Boosts early usage and customer confidence.\n"
                f"Next step: Send onboarding guidance"
            )
        else:
            rec_type = "Contract Win-back Offer"
            rec_desc = (
                f"Why this customer is at risk: High churn risk score driven by elevated usage switch behavior "
                f"({app_switch_frequency} app switches) and declining interaction patterns.\n"
                f"Recommended action: Offer a 20% discount on renewal or a complimentary month to secure contract extension.\n"
                f"Priority: High (Urgent)\n"
                f"Expected impact: Lowers immediate exit probability.\n"
                f"Next step: Send discount offer"
            )
    elif risk_category == "Medium":
        if satisfaction_score <= 5:
            rec_type = "Feedback Loop & Nudge"
            rec_desc = (
                f"Why this customer is at risk: Moderate churn risk with a low satisfaction score of {satisfaction_score}/10.\n"
                f"Recommended action: Send a feedback survey to identify primary complaints, accompanied by a plan comparison check.\n"
                f"Priority: Medium (Proactive)\n"
                f"Expected impact: Flags areas of dissatisfaction before they escalate.\n"
                f"Next step: Send feedback survey"
            )
        elif monthly_total_spend > 100:
            rec_type = "Premium Account Review"
            rec_desc = (
                f"Why this customer is at risk: Premium high-spending customer (${monthly_total_spend:.2f}) "
                f"showing moderate engagement decline.\n"
                f"Recommended action: Offer a proactive account check-in to optimize subscription tier benefits.\n"
                f"Priority: Medium (Proactive)\n"
                f"Expected impact: Protects high-value contract revenue.\n"
                f"Next step: Monitor and review account"
            )
        else:
            rec_type = "Proactive Engagement Plan"
            rec_desc = (
                f"Why this customer is at risk: Customer showing moderate churn signs, potentially due to low "
                f"weekly usage ({avg_usage_hours_per_week} hrs/week).\n"
                f"Recommended action: Trigger a usage-based email campaign highlighting new feature releases and benefits.\n"
                f"Priority: Medium (Proactive)\n"
                f"Expected impact: Increases product adoption and weekly engagement.\n"
                f"Next step: Trigger feature updates newsletter"
            )
    else:  # Low risk
        rec_type = "Loyalty Reinforcement"
        rec_desc = (
            f"Why this customer is at risk: Customer exhibits stable engagement patterns, high satisfaction "
            f"({satisfaction_score}/10), and a healthy tenure ({tenure_months} months).\n"
            f"Recommended action: Continue monitoring behavioral metrics; keep enrolled in standard newsletters without aggressive discounts.\n"
            f"Priority: Low\n"
            f"Expected impact: Maintained stable retention and baseline satisfaction.\n"
            f"Next step: Monitor metrics"
        )
    return rec_type, rec_desc

def build_customer_prediction_input(customer) -> pd.DataFrame:
    if isinstance(customer, dict):
        def get_first(*keys, default=None):
            for key in keys:
                if key in customer and customer[key] not in (None, ""):
                    return customer[key]
            return default
            
        def to_int(val, default):
            try:
                return int(float(val)) if val is not None else default
            except:
                return default
                
        def to_float(val, default):
            try:
                return float(val) if val is not None else default
            except:
                return default

        input_row = {
            "Income_Level": get_first("income_level", "Income_Level", "Income Level", default="Medium"),
            "Satisfaction_Score": to_int(get_first("satisfaction_score", "Satisfaction_Score", "Satisfaction (1-5)", default=3), 3),
            "Discount_Used": bool(get_first("discount_used", "Discount_Used", "Discount Used", default=False)),
            "Age": to_int(get_first("age", "Age", default=35), 35),
            "Number_of_Subscriptions": to_int(get_first("number_of_subscriptions", "Number_of_Subscriptions", "Number of Subscriptions", default=1), 1),
            "Tenure_Months": to_int(get_first("tenure_months", "Tenure_Months", "Tenure (Months)", default=12), 12),
            "Monthly_Total_Spend": to_float(get_first("monthly_total_spend", "Monthly_Total_Spend", "Monthly Spend ($)", default=75.0), 75.0),
            "Avg_Usage_Hours_Per_Week": to_float(get_first("avg_usage_hours_per_week", "Avg_Usage_Hours_Per_Week", "Weekly Usage (Hrs)", default=15.0), 15.0),
            "App_Switch_Frequency": to_int(get_first("app_switch_frequency", "App_Switch_Frequency", default=5), 5),
            "Customer_Support_Interactions": to_int(get_first("customer_support_interactions", "Customer_Support_Interactions", "Support Tickets", default=3), 3),
            "Device_Type": get_first("device_type", "Device_Type", "Device Type", default="Mobile"),
            "Payment_Mode": get_first("payment_mode", "Payment_Mode", "Payment Mode", default="UPI"),
        }
    else:
        # Customer ORM object
        input_row = {
            "Income_Level": customer.income_level or "Medium",
            "Satisfaction_Score": int(customer.satisfaction_score or 3),
            "Discount_Used": bool(customer.discount_used),
            "Age": int(customer.age or 35),
            "Number_of_Subscriptions": int(customer.number_of_subscriptions or 1),
            "Tenure_Months": int(customer.tenure_months or 12),
            "Monthly_Total_Spend": float(customer.monthly_total_spend or 75.0),
            "Avg_Usage_Hours_Per_Week": float(customer.avg_usage_hours_per_week or 15.0),
            "App_Switch_Frequency": int(customer.app_switch_frequency or 5),
            "Customer_Support_Interactions": int(customer.customer_support_interactions or 3),
            "Device_Type": customer.device_type or "Mobile",
            "Payment_Mode": customer.payment_mode or "UPI",
        }
    return pd.DataFrame([input_row], dtype=object)

def calculate_prediction_for_customer(db: Session, customer) -> dict:
    customer_id = customer.customer_id if hasattr(customer, "customer_id") else customer.get("customer_id")
    
    # A/B Testing Logic
    model_version_to_use = model_service.get_model_version_for_request(customer_id)
    if not model_version_to_use:
        model_version_to_use = "v1.3.0-model-comparison"
        
    support_interactions = int(customer.customer_support_interactions or 3) if hasattr(customer, "customer_support_interactions") else int(customer.get("customer_support_interactions", 3))
    satisfaction = int(customer.satisfaction_score or 3) if hasattr(customer, "satisfaction_score") else int(customer.get("satisfaction_score", 3))
    monthly_spend = float(customer.monthly_total_spend or 75.0) if hasattr(customer, "monthly_total_spend") else float(customer.get("monthly_total_spend", 75.0))
    usage = float(customer.avg_usage_hours_per_week or 15.0) if hasattr(customer, "avg_usage_hours_per_week") else float(customer.get("avg_usage_hours_per_week", 15.0))
    tenure = int(customer.tenure_months or 12) if hasattr(customer, "tenure_months") else int(customer.get("tenure_months", 12))
    app_switch = int(customer.app_switch_frequency or 5) if hasattr(customer, "app_switch_frequency") else int(customer.get("app_switch_frequency", 5))

    if model_service.is_ready:
        try:
            df_input = build_customer_prediction_input(customer)
            output = model_service.predict_and_explain(df_input, model_version=model_version_to_use)
            score = round(output["probability"] * 100.0, 2)
            score_lower = round(output["probability_confidence_lower"] * 100.0, 2)
            score_upper = round(output["probability_confidence_upper"] * 100.0, 2)
            risk, will_cancel = risk_from_probability(score / 100.0)
            
            rec_type, rec_desc = generate_recommendation_details(
                prob=score,
                risk_category=risk,
                satisfaction_score=satisfaction,
                monthly_total_spend=monthly_spend,
                tenure_months=tenure,
                customer_support_interactions=support_interactions,
                avg_usage_hours_per_week=usage,
                app_switch_frequency=app_switch
            )
            explainability = output["explainability"]
        except Exception as exc:
            print(f"Model prediction failed, falling back to rule-based predictor: {exc}")
            profile = build_risk_profile(
                customer_support_interactions=support_interactions,
                satisfaction_score=satisfaction,
                monthly_total_spend=monthly_spend,
                avg_usage_hours_per_week=usage,
            )
            score = float(profile["risk_score"])
            score_lower = max(0.0, score - 5.0)
            score_upper = min(100.0, score + 5.0)
            risk = profile["risk_category"]
            will_cancel = int(profile["will_cancel"])
            
            rec_type, rec_desc = generate_recommendation_details(
                prob=score,
                risk_category=risk,
                satisfaction_score=satisfaction,
                monthly_total_spend=monthly_spend,
                tenure_months=tenure,
                customer_support_interactions=support_interactions,
                avg_usage_hours_per_week=usage,
                app_switch_frequency=app_switch
            )
            explainability = profile.get("explainability_json", {})
    else:
        profile = build_risk_profile(
            customer_support_interactions=support_interactions,
            satisfaction_score=satisfaction,
            monthly_total_spend=monthly_spend,
            avg_usage_hours_per_week=usage,
        )
        score = float(profile["risk_score"])
        score_lower = max(0.0, score - 5.0)
        score_upper = min(100.0, score + 5.0)
        risk = profile["risk_category"]
        will_cancel = int(profile["will_cancel"])
        
        rec_type, rec_desc = generate_recommendation_details(
            prob=score,
            risk_category=risk,
            satisfaction_score=satisfaction,
            monthly_total_spend=monthly_spend,
            tenure_months=tenure,
            customer_support_interactions=support_interactions,
            avg_usage_hours_per_week=usage,
            app_switch_frequency=app_switch
        )
        explainability = profile.get("explainability_json", {})
        
    return {
        "churn_probability": score,
        "probability_confidence_lower": score_lower,
        "probability_confidence_upper": score_upper,
        "risk_category": risk,
        "will_cancel": will_cancel,
        "explainability": explainability,
        "recommendation_type": rec_type,
        "recommendation_desc": rec_desc,
        "model_version": model_version_to_use
    }

def save_customer_prediction(db: Session, customer_id: str, prediction_data: dict) -> ChurnPrediction:
    now_time = datetime.now(timezone.utc)
    db_prediction = ChurnPrediction(
        customer_id=customer_id,
        churn_probability=prediction_data["churn_probability"],
        risk_category=prediction_data["risk_category"],
        will_cancel=prediction_data["will_cancel"],
        explainability_json=prediction_data["explainability"],
        recommendation_type=prediction_data["recommendation_type"],
        recommendation_desc=prediction_data["recommendation_desc"],
        predicted_at=now_time,
        model_version=prediction_data["model_version"]
    )
    db.add(db_prediction)
    db.flush()
    
    db_history = PredictionHistory(
        customer_id=customer_id,
        risk_score=prediction_data["churn_probability"],
        risk_category=prediction_data["risk_category"],
        prediction_result=prediction_data["will_cancel"],
        evaluated_at=now_time
    )
    db.add(db_history)
    db.commit()
    return db_prediction

def ensure_customer_has_prediction(db: Session, customer_id: str) -> ChurnPrediction:
    prediction = db.query(ChurnPrediction).filter(ChurnPrediction.customer_id == customer_id).first()
    if prediction:
        return prediction
        
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise ValueError(f"Customer with ID {customer_id} not found.")
        
    pred_data = calculate_prediction_for_customer(db, customer)
    return save_customer_prediction(db, customer_id, pred_data)

def ensure_all_customers_have_predictions(db: Session, limit: int = None) -> dict:
    stmt = text("""
        SELECT customer_id FROM customers 
        WHERE customer_id NOT IN (SELECT DISTINCT customer_id FROM churn_predictions)
    """)
    rows = db.execute(stmt).fetchall()
    missing_ids = [r.customer_id for r in rows]
    
    if limit is not None:
        missing_ids = missing_ids[:limit]
        
    created_count = 0
    failed_ids = []
    
    for cust_id in missing_ids:
        try:
            customer = db.query(Customer).filter(Customer.customer_id == cust_id).first()
            if customer:
                pred_data = calculate_prediction_for_customer(db, customer)
                save_customer_prediction(db, cust_id, pred_data)
                created_count += 1
        except Exception as e:
            print(f"Failed to generate prediction for customer {cust_id} during backfill: {e}")
            failed_ids.append(cust_id)
            
    return {
        "total_checked": len(missing_ids),
        "predictions_created": created_count,
        "failed_customers": failed_ids,
        "status": "success" if not failed_ids else "partial_success"
    }
