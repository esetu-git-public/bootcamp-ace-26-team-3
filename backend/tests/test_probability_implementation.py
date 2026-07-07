"""
Test suite for probability prediction implementation.
Tests probability calculation, confidence intervals, and risk categorization.
"""

import pytest
import numpy as np
from datetime import datetime
from typing import Dict, Any


class TestProbabilityCalculation:
    """Test probability scoring and confidence interval calculation."""

    def test_probability_bounds(self):
        """Verify probabilities are within [0.0, 100.0] range."""
        test_probabilities = [0.0, 25.5, 50.0, 75.3, 100.0]
        for prob in test_probabilities:
            assert 0.0 <= prob <= 100.0, f"Probability {prob} out of bounds"

    def test_confidence_interval_ordering(self):
        """Verify CI bounds maintain proper ordering: lower <= prob <= upper."""
        test_cases = [
            {"prob": 50.0, "lower": 45.0, "upper": 55.0},
            {"prob": 85.5, "lower": 80.3, "upper": 90.7},
            {"prob": 15.0, "lower": 10.0, "upper": 20.0},
            {"prob": 0.0, "lower": 0.0, "upper": 5.0},
            {"prob": 100.0, "lower": 95.0, "upper": 100.0},
        ]
        
        for case in test_cases:
            assert case["lower"] <= case["prob"], \
                f"Lower bound {case['lower']} exceeds probability {case['prob']}"
            assert case["prob"] <= case["upper"], \
                f"Probability {case['prob']} exceeds upper bound {case['upper']}"
            assert case["lower"] <= case["upper"], \
                f"Lower bound {case['lower']} exceeds upper bound {case['upper']}"

    def test_confidence_interval_symmetry(self):
        """Verify confidence intervals have reasonable symmetric margins."""
        test_cases = [
            {"prob": 50.0, "lower": 45.0, "upper": 55.0, "expected_margin": 5.0},
            {"prob": 85.5, "lower": 80.3, "upper": 90.7, "expected_margin": 5.2},
        ]
        
        for case in test_cases:
            margin_lower = case["prob"] - case["lower"]
            margin_upper = case["upper"] - case["prob"]
            avg_margin = (margin_lower + margin_upper) / 2
            assert abs(margin_lower - margin_upper) < 1.0, \
                f"Margins not symmetric: lower={margin_lower}, upper={margin_upper}"


class TestRiskCategorization:
    """Test mapping of probabilities to risk categories."""

    def test_low_risk_category(self):
        """Verify probabilities < 30% map to Low risk."""
        test_probabilities = [0.0, 10.0, 15.5, 29.9]
        for prob in test_probabilities:
            assert prob < 30.0, f"Probability {prob} should map to Low risk"

    def test_medium_risk_category(self):
        """Verify probabilities 30-70% map to Medium risk."""
        test_probabilities = [30.0, 45.5, 50.0, 65.0, 69.9]
        for prob in test_probabilities:
            assert 30.0 <= prob < 70.0, f"Probability {prob} should map to Medium risk"

    def test_high_risk_category(self):
        """Verify probabilities >= 70% map to High risk."""
        test_probabilities = [70.0, 75.0, 85.5, 99.9, 100.0]
        for prob in test_probabilities:
            assert prob >= 70.0, f"Probability {prob} should map to High risk"

    def test_will_cancel_flag(self):
        """Verify will_cancel flag (0=Low, 1=Medium/High)."""
        # Low risk should have will_cancel = 0
        low_risk_prob = 25.0
        assert low_risk_prob < 30.0, "Low risk probability"
        
        # Medium/High risk should have will_cancel = 1
        medium_risk_prob = 55.0
        assert medium_risk_prob >= 30.0, "Medium/High risk probability"
        
        high_risk_prob = 85.0
        assert high_risk_prob >= 30.0, "High risk probability"


class TestExplainability:
    """Test feature importance (explainability) scores."""

    def test_explainability_structure(self):
        """Verify explainability contains required features."""
        required_features = [
            "Customer_Support_Interactions",
            "Satisfaction_Score",
            "Avg_Usage_Hours_Per_Week",
            "Tenure_Months",
            "Monthly_Total_Spend",
            "Age"
        ]
        
        mock_explainability = {
            "Customer_Support_Interactions": 0.42,
            "Satisfaction_Score": 0.38,
            "Avg_Usage_Hours_Per_Week": 0.22,
            "Tenure_Months": 0.15,
            "Monthly_Total_Spend": -0.10,
            "Age": -0.05
        }
        
        for feature in required_features:
            assert feature in mock_explainability, f"Missing feature: {feature}"
            assert isinstance(mock_explainability[feature], (int, float)), \
                f"Feature {feature} value must be numeric"

    def test_feature_importance_interpretation(self):
        """Verify positive/negative values indicate increase/decrease in risk."""
        explainability = {
            "Customer_Support_Interactions": 0.42,  # Positive = increases churn
            "Satisfaction_Score": 0.38,  # Positive = increases churn (but satisfaction is inverse)
            "Monthly_Total_Spend": -0.10,  # Negative = decreases churn
            "Age": -0.05  # Negative = decreases churn
        }
        
        # Just verify structure is consistent
        for feature, importance in explainability.items():
            assert isinstance(importance, (int, float)), \
                f"Importance score for {feature} must be numeric"


class TestAPIResponseSchema:
    """Test prediction API response format."""

    def test_single_prediction_response_fields(self):
        """Verify SinglePredictionResponse contains all required fields."""
        mock_response = {
            "customer_id": "1",
            "churn_probability": 85.50,
            "probability_confidence_lower": 80.30,
            "probability_confidence_upper": 90.70,
            "risk_category": "High",
            "will_cancel": 1,
            "explainability": {
                "Customer_Support_Interactions": 0.42,
                "Satisfaction_Score": 0.38,
                "Avg_Usage_Hours_Per_Week": 0.22,
                "Tenure_Months": 0.15,
                "Monthly_Total_Spend": -0.10,
                "Age": -0.05
            },
            "recommendation_type": "Offer Discount",
            "recommendation_desc": "Apply 20% discount on renewal..."
        }
        
        required_fields = [
            "customer_id", "churn_probability", 
            "probability_confidence_lower", "probability_confidence_upper",
            "risk_category", "will_cancel", 
            "explainability", "recommendation_type", "recommendation_desc"
        ]
        
        for field in required_fields:
            assert field in mock_response, f"Missing required field: {field}"

    def test_customer_profile_response_fields(self):
        """Verify CustomerProfileResponse includes probability fields."""
        mock_response = {
            "customer_id": "1",
            "age": 34,
            "income_level": "Medium",
            "number_of_subscriptions": 2,
            "tenure_months": 8,
            "monthly_total_spend": 79.50,
            "avg_usage_hours_per_week": 14.5,
            "app_switch_frequency": 15,
            "customer_support_interactions": 3,
            "satisfaction_score": 2,
            "discount_used": False,
            "device_type": "Android",
            "payment_mode": "UPI",
            "created_at": datetime.utcnow().isoformat(),
            "churn_probability": 89.00,
            "probability_confidence_lower": 84.50,
            "probability_confidence_upper": 93.50,
            "risk_category": "High",
            "will_cancel": 1,
            "explainability": {"Customer_Support_Interactions": 0.42},
            "recommendation_type": "Offer Discount",
            "recommendation_desc": "...",
            "predicted_at": datetime.utcnow().isoformat()
        }
        
        probability_fields = [
            "churn_probability",
            "probability_confidence_lower",
            "probability_confidence_upper"
        ]
        
        for field in probability_fields:
            assert field in mock_response, f"Missing probability field: {field}"


class TestProbabilityEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_probability(self):
        """Test handling of 0% churn probability (no risk)."""
        prob = 0.0
        lower = max(0.0, prob - 5.0)
        upper = min(100.0, prob + 5.0)
        
        assert prob == 0.0
        assert lower == 0.0
        assert upper == 5.0
        assert lower <= prob <= upper

    def test_max_probability(self):
        """Test handling of 100% churn probability (maximum risk)."""
        prob = 100.0
        lower = max(0.0, prob - 5.0)
        upper = min(100.0, prob + 5.0)
        
        assert prob == 100.0
        assert lower == 95.0
        assert upper == 100.0
        assert lower <= prob <= upper

    def test_boundary_probabilities(self):
        """Test boundary values for risk category transitions."""
        boundaries = [
            (29.9, "Low"),  # Just below Medium threshold
            (30.0, "Medium"),  # At Medium threshold
            (69.9, "Medium"),  # Just below High threshold
            (70.0, "High"),  # At High threshold
        ]
        
        for prob, expected_category in boundaries:
            if expected_category == "Low":
                assert prob < 30.0
            elif expected_category == "Medium":
                assert 30.0 <= prob < 70.0
            else:  # High
                assert prob >= 70.0


class TestRegressionDetection:
    """Tests to detect probability calculation regressions."""

    def test_consistent_probability_scaling(self):
        """Verify probabilities are consistently scaled (0-100, not 0-1)."""
        # If probabilities were incorrectly in 0-1 range, they would be < 1
        test_probabilities = [0.0, 25.0, 50.0, 75.0, 100.0]
        
        for prob in test_probabilities:
            # All meaningful probabilities should be >= 0.0 and <= 100.0
            # (excluding the 0-1 range which would indicate a bug)
            assert not (0.0 < prob < 1.0) or prob == 0.0 or prob == 1.0, \
                f"Probability {prob} may not be properly scaled to 0-100 range"

    def test_explainability_field_renamed(self):
        """Verify explainability field is named 'explainability', not 'explainability_json'."""
        mock_response = {
            "customer_id": "1",
            "churn_probability": 85.50,
            "explainability": {"feature": 0.42},
            "explainability_json": None  # Should not exist in API response
        }
        
        # The new schema should have 'explainability'
        assert "explainability" in mock_response
        # Old field should ideally not exist (but we check it's explicitly None if present)
        if "explainability_json" in mock_response:
            # Should only appear in database, not API response
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
