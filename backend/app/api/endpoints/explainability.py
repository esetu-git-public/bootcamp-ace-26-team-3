"""
SHAP Explainability API Endpoints

Provides endpoints for generating detailed SHAP explanations,
feature importance, and interactive visualizations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
import pandas as pd
from typing import Optional, Dict, List

from ..database import get_db
from ..core.model_service import model_service
from ..schemas.common import DashboardKPIsResponse
from .auth import get_current_user

# Try to import SHAP visualization utilities
try:
    from ..core.shap_visualizer import SHAPVisualizer, InteractiveExplainationGenerator
    SHAP_AVAILABLE = True
except Exception as e:
    print(f"Warning: SHAP visualization utilities not available: {e}")
    SHAPVisualizer = None
    InteractiveExplainationGenerator = None
    SHAP_AVAILABLE = False


router = APIRouter(prefix="/explainability", tags=["SHAP Explainability"])


# Schemas for SHAP endpoints
class ShapExplanationResponse:
    """Response model for SHAP explanation."""
    pass


class GlobalFeatureImportanceResponse:
    """Response model for global feature importance."""
    pass


def _build_prediction_input(data: dict) -> pd.DataFrame:
    """Build prediction input DataFrame from dictionary."""
    def _normalize_bool(value: Optional[object]) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            return value.strip().lower() in ["true", "yes", "1", "t", "y"]
        return False

    input_row = {
        "Income_Level": data.get("income_level", "Medium"),
        "Satisfaction_Score": int(data.get("satisfaction_score", 3)),
        "Discount_Used": _normalize_bool(data.get("discount_used", False)),
        "Age": int(data.get("age", 35)),
        "Number_of_Subscriptions": int(data.get("number_of_subscriptions", 1)),
        "Tenure_Months": int(data.get("tenure_months", 12)),
        "Monthly_Total_Spend": float(data.get("monthly_total_spend", 75.0)),
        "Avg_Usage_Hours_Per_Week": float(data.get("avg_usage_hours_per_week", 15.0)),
        "App_Switch_Frequency": int(data.get("app_switch_frequency", 5)),
        "Customer_Support_Interactions": int(data.get("customer_support_interactions", 3)),
        "Device_Type": data.get("device_type", "Mobile"),
        "Payment_Mode": data.get("payment_mode", "UPI"),
    }
    return pd.DataFrame([input_row])


@router.post("/explain-prediction/{customer_id}")
async def explain_prediction(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Get detailed SHAP explanation for a customer's churn prediction.
    
    Args:
        customer_id: Customer ID to explain
        
    Returns:
        Dictionary with SHAP values, contributions, and visualization data
    """
    if not model_service.is_ready:
        raise HTTPException(status_code=503, detail="Model service not ready")
    
    try:
        # Fetch customer data
        query = text("SELECT * FROM customers WHERE customer_id = :customer_id")
        customer = db.execute(query, {"customer_id": customer_id}).fetchone()
        
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # Build input
        input_data = {
            "income_level": customer.income_level,
            "satisfaction_score": customer.satisfaction_score,
            "discount_used": customer.discount_used,
            "age": customer.age,
            "number_of_subscriptions": customer.number_of_subscriptions,
            "tenure_months": customer.tenure_months,
            "monthly_total_spend": float(customer.monthly_total_spend),
            "avg_usage_hours_per_week": float(customer.avg_usage_hours_per_week),
            "app_switch_frequency": customer.app_switch_frequency,
            "customer_support_interactions": customer.customer_support_interactions,
            "device_type": customer.device_type,
            "payment_mode": customer.payment_mode,
        }
        
        df_input = _build_prediction_input(input_data)
        
        # Get advanced explanation
        explanation = model_service.predict_with_advanced_explanation(df_input)
        
        return {
            "customer_id": customer_id,
            "probability": explanation["probability"],
            "prediction": "churn" if explanation["probability"] >= 0.5 else "no_churn",
            "base_value": explanation.get("base_value"),
            "feature_contributions": explanation["feature_contributions"],
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Explanation failed: {str(e)}")


@router.get("/feature-importance")
async def get_feature_importance(
    top_n: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Get global feature importance based on mean absolute SHAP values.
    
    Args:
        top_n: Number of top features to return
        
    Returns:
        Dictionary with global feature importance rankings
    """
    if not model_service.is_ready or model_service.shap_explainer is None:
        raise HTTPException(status_code=503, detail="SHAP explainer not initialized")
    
    try:
        # Get all customers for feature importance calculation
        query = text("""
            SELECT 
                income_level, satisfaction_score, discount_used, age,
                number_of_subscriptions, tenure_months, monthly_total_spend,
                avg_usage_hours_per_week, app_switch_frequency,
                customer_support_interactions, device_type, payment_mode
            FROM customers
            LIMIT 1000
        """)
        
        results = db.execute(query).fetchall()
        
        if not results:
            # Return empty importance if no data
            return model_service.get_global_importance(None)
        
        # Convert to DataFrame
        columns = [
            "income_level", "satisfaction_score", "discount_used", "age",
            "number_of_subscriptions", "tenure_months", "monthly_total_spend",
            "avg_usage_hours_per_week", "app_switch_frequency",
            "customer_support_interactions", "device_type", "payment_mode"
        ]
        df = pd.DataFrame(results, columns=columns)
        
        # Process features
        processed_df = model_service.preprocessor.transform(df)
        
        # Get importance
        importance = model_service.get_global_importance(processed_df)
        
        return importance
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feature importance calculation failed: {str(e)}")


@router.get("/feature-interaction")
async def get_feature_interaction(
    feature1: str = Query(..., description="First feature name"),
    feature2: str = Query(..., description="Second feature name"),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Analyze interaction between two features using SHAP.
    
    Args:
        feature1: Name of first feature
        feature2: Name of second feature
        
    Returns:
        Dictionary with interaction analysis
    """
    if not model_service.is_ready or model_service.shap_explainer is None:
        raise HTTPException(status_code=503, detail="SHAP explainer not initialized")
    
    try:
        # Get sample customer data for interaction analysis
        query = text("""
            SELECT 
                income_level, satisfaction_score, discount_used, age,
                number_of_subscriptions, tenure_months, monthly_total_spend,
                avg_usage_hours_per_week, app_switch_frequency,
                customer_support_interactions, device_type, payment_mode
            FROM customers
            LIMIT 500
        """)
        
        results = db.execute(query).fetchall()
        
        if not results:
            raise HTTPException(status_code=400, detail="Insufficient customer data for analysis")
        
        columns = [
            "income_level", "satisfaction_score", "discount_used", "age",
            "number_of_subscriptions", "tenure_months", "monthly_total_spend",
            "avg_usage_hours_per_week", "app_switch_frequency",
            "customer_support_interactions", "device_type", "payment_mode"
        ]
        df = pd.DataFrame(results, columns=columns)
        
        # Get interaction
        interaction = model_service.get_feature_interaction(df, feature1, feature2)
        
        return interaction
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feature interaction analysis failed: {str(e)}")


@router.post("/interactive-explanation/{customer_id}")
async def get_interactive_explanation(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Generate comprehensive interactive explanation with multiple visualization formats.
    
    Args:
        customer_id: Customer ID
        
    Returns:
        Dictionary with force plot, decision plot, waterfall plot, and feature importance
    """
    if not model_service.is_ready or model_service.shap_explainer is None:
        raise HTTPException(status_code=503, detail="Model service not ready")
    
    try:
        # Fetch customer data
        query = text("SELECT * FROM customers WHERE customer_id = :customer_id")
        customer = db.execute(query, {"customer_id": customer_id}).fetchone()
        
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # Build input
        input_data = {
            "income_level": customer.income_level,
            "satisfaction_score": customer.satisfaction_score,
            "discount_used": customer.discount_used,
            "age": customer.age,
            "number_of_subscriptions": customer.number_of_subscriptions,
            "tenure_months": customer.tenure_months,
            "monthly_total_spend": float(customer.monthly_total_spend),
            "avg_usage_hours_per_week": float(customer.avg_usage_hours_per_week),
            "app_switch_frequency": customer.app_switch_frequency,
            "customer_support_interactions": customer.customer_support_interactions,
            "device_type": customer.device_type,
            "payment_mode": customer.payment_mode,
        }
        
        df_input = _build_prediction_input(input_data)
        
        # Get explanation
        explanation = model_service.predict_with_advanced_explanation(df_input)
        probability = explanation["probability"]
        
        # Extract SHAP values from feature contributions
        feature_names = model_service.feature_names
        shap_values = [contrib["shap_value"] for contrib in explanation["feature_contributions"]]
        base_value = explanation.get("base_value", 0.0)
        
        # Generate interactive explanation
        interactive_explanation = InteractiveExplainationGenerator.generate_full_explanation(
            probability=probability,
            shap_values=import_numpy_values(shap_values),
            feature_names=feature_names,
            features=df_input,
            explainer_base_value=base_value
        )
        
        return {
            "customer_id": customer_id,
            "explanation": interactive_explanation
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Interactive explanation generation failed: {str(e)}")


def import_numpy_values(values: List) -> List:
    """Convert values to numpy array for SHAP visualization."""
    import numpy as np
    return np.array(values)


@router.get("/available-features")
async def get_available_features(
    current_user: str = Depends(get_current_user)
):
    """
    Get list of available features for interaction analysis.
    
    Returns:
        Dictionary with feature names and data types
    """
    if not model_service.is_ready:
        raise HTTPException(status_code=503, detail="Model service not ready")
    
    feature_info = []
    for feature_name in model_service.feature_names:
        feature_info.append({
            "name": feature_name,
            "available_for_interaction": True
        })
    
    return {
        "features": feature_info,
        "total_features": len(model_service.feature_names)
    }
