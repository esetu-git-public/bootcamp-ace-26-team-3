import os
import json
import pytest
import pandas as pd
from backend.app.core.model_service import ModelService

def test_model_comparison_reports_exist():
    """Verify that all model comparison reports and visual charts were successfully generated."""
    reports_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "reports"))
    
    expected_files = [
        "model_comparison_results.csv",
        "model_comparison_results.json",
        "best_model.txt",
        "model_overfitting_report.json",
        "model_comparison_summary.md",
        "model_comparison_metrics.png",
        "confusion_matrix_best_model.png",
        "roc_curve_comparison.png",
        "feature_importance_best_model.png"
    ]
    
    for filename in expected_files:
        filepath = os.path.join(reports_dir, filename)
        assert os.path.exists(filepath), f"Expected report file {filename} is missing."
        assert os.path.getsize(filepath) > 0, f"Report file {filename} is empty."


def test_model_overfitting_report_contents():
    """Verify the overfitting report format and content."""
    reports_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "reports"))
    report_path = os.path.join(reports_dir, "model_overfitting_report.json")
    
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)
        
    # Expect overfitting flags for trained models
    assert "logreg" in report
    assert "rf" in report
    assert "accuracy_gap" in report["logreg"]
    assert "is_overfitted" in report["logreg"]
    assert "potential_data_leakage" in report["logreg"]


def test_model_service_load_and_predict():
    """Verify that the backend ModelService successfully loads the best model and makes predictions."""
    service = ModelService()
    # Ensure a model version is active
    assert service.champion_version is not None
    assert service.is_ready
    
    # Run test prediction
    test_raw_features = pd.DataFrame([{
        "Age": 45,
        "Income_Level": "Medium",
        "Number_of_Subscriptions": 3,
        "Avg_Usage_Hours_Per_Week": 15.5,
        "App_Switch_Frequency": 4,
        "Discount_Used": 0,
        "Customer_Support_Interactions": 2,
        "Payment_Mode": "Credit Card",
        "Tenure_Months": 12,
        "Device_Type": "Desktop",
        "Satisfaction_Score": 4,
        "Monthly_Total_Spend": 85.0
    }])
    
    result = service.predict_and_explain(test_raw_features)
    assert "probability" in result
    assert "probability_confidence_lower" in result
    assert "probability_confidence_upper" in result
    assert "explainability" in result
    
    assert 0.0 <= result["probability"] <= 1.0
    assert 0.0 <= result["probability_confidence_lower"] <= 1.0
    assert 0.0 <= result["probability_confidence_upper"] <= 1.0
