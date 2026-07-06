"""
SHAP Explainability Usage Examples

Demonstrates how to use the SHAP explainability features
in the subscription churn prediction system.
"""

import pandas as pd
import numpy as np
from typing import Dict, List

# Example 1: Basic Local Explanation
def example_local_explanation():
    """
    Generate SHAP explanation for a single customer prediction.
    """
    from backend.app.core.model_service import model_service
    
    # Customer data
    customer_data = {
        "income_level": "Medium",
        "satisfaction_score": 2,
        "discount_used": False,
        "age": 35,
        "number_of_subscriptions": 1,
        "tenure_months": 12,
        "monthly_total_spend": 75.0,
        "avg_usage_hours_per_week": 15.0,
        "app_switch_frequency": 5,
        "customer_support_interactions": 3,
        "device_type": "Mobile",
        "payment_mode": "UPI",
    }
    
    # Create DataFrame
    df = pd.DataFrame([customer_data])
    
    # Get advanced explanation
    explanation = model_service.predict_with_advanced_explanation(df)
    
    # Print results
    print("=" * 60)
    print("LOCAL EXPLANATION EXAMPLE")
    print("=" * 60)
    print(f"\nChurn Probability: {explanation['probability']:.2%}")
    print(f"Prediction Class: {'CHURN' if explanation['probability'] >= 0.5 else 'NO CHURN'}")
    print(f"Base Value (Expected): {explanation['base_value']:.2%}")
    print(f"\nTop Contributing Factors:")
    
    # Show top 5 factors
    for i, contrib in enumerate(explanation['feature_contributions'][:5], 1):
        direction = "↑ INCREASES" if contrib['direction'] == 'positive' else "↓ DECREASES" if contrib['direction'] == 'negative' else "—"
        print(f"  {i}. {contrib['feature']:.<35} {direction:.<15} {contrib['shap_value']:>+.4f} ({contrib['original_value']})")
    
    return explanation


# Example 2: Feature Importance Analysis
def example_feature_importance():
    """
    Get global feature importance based on mean absolute SHAP values.
    """
    from backend.app.core.model_service import model_service
    
    # Note: This requires data preprocessing
    print("\n" + "=" * 60)
    print("GLOBAL FEATURE IMPORTANCE EXAMPLE")
    print("=" * 60)
    
    # This would be called with processed features in production
    print("\nGlobal Feature Importance (Mean Absolute SHAP):")
    print("Feature".ljust(30) + "Importance")
    print("-" * 45)
    
    # Example output
    importance_data = [
        ("Satisfaction_Score", 0.18),
        ("Monthly_Total_Spend", 0.14),
        ("Customer_Support_Interactions", 0.12),
        ("Tenure_Months", 0.08),
        ("Age", 0.06),
    ]
    
    for feature, importance in importance_data:
        bar = "█" * int(importance * 100)
        print(f"{feature:<30} {bar:<20} {importance:.4f}")


# Example 3: Force Plot Data
def example_force_plot():
    """
    Create force plot visualization data (for web display).
    """
    from backend.app.core.shap_visualizer import SHAPVisualizer
    
    print("\n" + "=" * 60)
    print("FORCE PLOT DATA EXAMPLE")
    print("=" * 60)
    
    # Example SHAP values
    base_value = 0.45
    shap_values = np.array([-0.10, 0.08, 0.12, -0.05, 0.15, 0.03, -0.02, 0.10, 0.08, 0.06, 0.02, -0.01])
    feature_names = [
        "Satisfaction_Score", "Monthly_Total_Spend", "Customer_Support_Interactions",
        "Tenure_Months", "Age", "App_Switch_Frequency",
        "Discount_Used", "Number_of_Subscriptions", "Avg_Usage_Hours_Per_Week",
        "Income_Level_Medium", "Income_Level_High", "Device_Type_Web"
    ]
    
    # Create example features DataFrame
    features = pd.DataFrame([[0] * len(feature_names)], columns=feature_names)
    
    # Generate force plot data
    force_data = SHAPVisualizer.create_force_plot_data(
        base_value, shap_values, features, feature_names
    )
    
    print(f"\nBase Value: {force_data['base_value']:.2%}")
    print(f"Prediction Value: {force_data['prediction_value']:.2%}")
    print(f"\nPush UP (Positive SHAP - Increase Churn Risk):")
    for feat in force_data['positive_features'][:3]:
        print(f"  + {feat['feature']:.<30} {feat['shap_value']:>+.4f}")
    
    print(f"\nPush DOWN (Negative SHAP - Decrease Churn Risk):")
    for feat in force_data['negative_features'][:3]:
        print(f"  - {feat['feature']:.<30} {feat['shap_value']:>+.4f}")


# Example 4: Decision Path Visualization
def example_decision_path():
    """
    Create decision path visualization data.
    """
    from backend.app.core.shap_visualizer import SHAPVisualizer
    
    print("\n" + "=" * 60)
    print("DECISION PATH EXAMPLE")
    print("=" * 60)
    
    # Example data
    base_value = 0.45
    shap_values = np.array([0.08, 0.12, -0.05, 0.15])
    feature_names = ["Satisfaction_Score", "Support_Interactions", "Tenure", "Age"]
    
    # Generate decision path
    decision_data = SHAPVisualizer.create_decision_plot_data(
        base_value, shap_values, feature_names
    )
    
    print(f"\nDecision Path from {base_value:.2%} to {decision_data['final_value']:.2%}:")
    print(f"{'Step':<6} {'Feature':<35} {'SHAP Value':<15} {'Cumulative':<15}")
    print("-" * 75)
    
    print(f"{'0':<6} {'Base Value':<35} {'':<15} {decision_data['base_value']:.2%}")
    
    for step in decision_data['decision_path']:
        print(f"{step['step']:<6} {step['feature']:<35} {step['shap_value']:>+.4f}         {step['cumulative_value']:.2%}")


# Example 5: Waterfall Plot Data
def example_waterfall():
    """
    Create waterfall visualization data.
    """
    from backend.app.core.shap_visualizer import SHAPVisualizer
    
    print("\n" + "=" * 60)
    print("WATERFALL PLOT EXAMPLE")
    print("=" * 60)
    
    # Example data
    base_value = 0.45
    shap_values = np.array([-0.10, 0.08, 0.12, -0.05, 0.15, 0.03, -0.02, 0.10, 0.08, 0.06, 0.02, -0.01])
    feature_names = ["f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12"]
    
    # Generate waterfall data
    waterfall_data = SHAPVisualizer.create_waterfall_plot_data(
        base_value, shap_values, feature_names, top_n=5
    )
    
    print("\nWaterfall Path (Top 5 Features by Impact):")
    print(f"{'Step':<35} {'Value':<15} {'Cumulative':<15}")
    print("-" * 70)
    
    for step in waterfall_data['waterfall_steps']:
        color = "▲" if step['type'] == 'positive' else "▼" if step['type'] == 'negative' else "●"
        print(f"{color} {step['step']:<32} {step['value']:>+.4f}         {step['cumulative']:.2%}")
    
    print(f"\nFinal Prediction: {waterfall_data['final_value']:.2%}")


# Example 6: Explanation Summary
def example_explanation_summary():
    """
    Generate human-readable explanation summary.
    """
    from backend.app.core.shap_visualizer import SHAPVisualizer
    
    print("\n" + "=" * 60)
    print("EXPLANATION SUMMARY EXAMPLE")
    print("=" * 60)
    
    # Example data
    probability = 0.75
    shap_values = np.array([0.12, -0.10, 0.15, 0.08, 0.05])
    feature_names = ["Support_Interactions", "Satisfaction", "Age", "Spend", "Tenure"]
    
    summary = SHAPVisualizer.create_explanation_summary(probability, shap_values, feature_names)
    
    print(f"\n{summary}")


# Example 7: Using in API Response
def example_api_response():
    """
    Show how SHAP explanations are used in API responses.
    """
    print("\n" + "=" * 60)
    print("API RESPONSE EXAMPLE")
    print("=" * 60)
    
    # Simulated API response
    response = {
        "customer_id": "CUST_001",
        "probability": 0.75,
        "prediction": "churn",
        "base_value": 0.45,
        "feature_contributions": [
            {
                "feature": "Satisfaction_Score",
                "shap_value": -0.10,
                "abs_shap_value": 0.10,
                "direction": "negative",
                "original_value": 2
            },
            {
                "feature": "Customer_Support_Interactions",
                "shap_value": 0.15,
                "abs_shap_value": 0.15,
                "direction": "positive",
                "original_value": 4
            },
            {
                "feature": "Monthly_Total_Spend",
                "shap_value": 0.12,
                "abs_shap_value": 0.12,
                "direction": "positive",
                "original_value": 45.0
            }
        ]
    }
    
    print(f"\nCustomer ID: {response['customer_id']}")
    print(f"Churn Probability: {response['probability']:.2%}")
    print(f"Prediction: {response['prediction'].upper()}")
    print(f"\nShaping Factors:")
    
    import json
    print(json.dumps(response, indent=2))


# Example 8: Batch Processing
def example_batch_processing():
    """
    Show how to process multiple customers for explanations.
    """
    print("\n" + "=" * 60)
    print("BATCH PROCESSING EXAMPLE")
    print("=" * 60)
    
    # Sample customer data
    customers = [
        {"id": "CUST_001", "satisfaction": 2, "support_calls": 5, "spend": 45},
        {"id": "CUST_002", "satisfaction": 4, "support_calls": 1, "spend": 120},
        {"id": "CUST_003", "satisfaction": 3, "support_calls": 3, "spend": 75},
    ]
    
    print(f"\n{'Customer':<12} {'Satisfaction':<15} {'Support Calls':<18} {'Monthly Spend':<15} {'Churn Risk':<15}")
    print("-" * 75)
    
    # Simulate explanations
    for customer in customers:
        # Mock churn risk based on satisfaction and support calls
        churn_risk = (6 - customer['satisfaction']) * 0.15 + customer['support_calls'] * 0.08
        churn_risk = min(max(churn_risk, 0), 1)
        
        risk_level = "🔴 HIGH" if churn_risk > 0.6 else "🟡 MEDIUM" if churn_risk > 0.3 else "🟢 LOW"
        
        print(f"{customer['id']:<12} {customer['satisfaction']:<15} {customer['support_calls']:<18} ${customer['spend']:<14.2f} {risk_level:<15}")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("SHAP EXPLAINABILITY EXAMPLES")
    print("=" * 60)
    
    # Note: Examples 1 and 2 require actual model artifacts
    # For demonstration, we'll skip them and show data structure examples
    
    # Show force plot data structure
    example_force_plot()
    
    # Show decision path
    example_decision_path()
    
    # Show waterfall plot
    example_waterfall()
    
    # Show explanation summary
    example_explanation_summary()
    
    # Show API response format
    example_api_response()
    
    # Show batch processing
    example_batch_processing()
    
    print("\n" + "=" * 60)
    print("EXAMPLES COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
