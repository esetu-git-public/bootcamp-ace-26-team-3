from typing import Any, Dict, Tuple


def _normalize_score(score: float) -> float:
    return round(max(0.0, min(100.0, float(score))), 2)


def calculate_default_risk_score(
    customer_support_interactions: Any,
    satisfaction_score: Any,
    monthly_total_spend: Any,
    avg_usage_hours_per_week: Any,
) -> float:
    support = float(customer_support_interactions or 0.0)
    satisfaction = float(satisfaction_score or 0.0)
    spend = float(monthly_total_spend or 0.0)
    usage = float(avg_usage_hours_per_week or 0.0)

    score = 30.0 + (support * 15.0) - (satisfaction * 10.0) + (spend * 0.02) - (usage * 0.8)
    return _normalize_score(score)


def derive_risk_category(score: float) -> str:
    if score >= 70.0:
        return "High"
    if score >= 30.0:
        return "Medium"
    return "Low"


def derive_recommendation(score: float) -> Tuple[str, str, int]:
    if score >= 70.0:
        return (
            "Offer Discount",
            "Apply 20% discount on renewal to mitigate high interaction friction.",
            1,
        )
    if score >= 30.0:
        return (
            "Subscription Upgrade",
            "Provide subscription upgrade incentive for premium benefits.",
            1,
        )
    return (
        "No Action Required",
        "Customer behavior shows stable engagement.",
        0,
    )


def build_explainability(
    customer_support_interactions: Any,
    satisfaction_score: Any,
    monthly_total_spend: Any,
    avg_usage_hours_per_week: Any,
) -> Dict[str, float]:
    support = float(customer_support_interactions or 0.0)
    satisfaction = float(satisfaction_score or 0.0)
    spend = float(monthly_total_spend or 0.0)
    usage = float(avg_usage_hours_per_week or 0.0)

    return {
        "Customer_Support_Interactions": round(support * 0.1, 2),
        "Satisfaction_Score": round((6.0 - satisfaction) * 0.1, 2),
        "Avg_Usage_Hours_Per_Week": round(-usage * 0.02, 2),
        "Monthly_Total_Spend": round(spend * 0.002, 2),
    }


def build_risk_profile(
    customer_support_interactions: Any,
    satisfaction_score: Any,
    monthly_total_spend: Any,
    avg_usage_hours_per_week: Any,
) -> Dict[str, Any]:
    score = calculate_default_risk_score(
        customer_support_interactions,
        satisfaction_score,
        monthly_total_spend,
        avg_usage_hours_per_week,
    )
    risk_category = derive_risk_category(score)
    recommendation_type, recommendation_desc, will_cancel = derive_recommendation(score)
    explainability_json = build_explainability(
        customer_support_interactions,
        satisfaction_score,
        monthly_total_spend,
        avg_usage_hours_per_week,
    )

    return {
        "risk_score": score,
        "risk_category": risk_category,
        "will_cancel": will_cancel,
        "recommendation_type": recommendation_type,
        "recommendation_desc": recommendation_desc,
        "explainability_json": explainability_json,
    }
