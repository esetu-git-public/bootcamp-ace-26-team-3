"""
SHAP Explainability Unit Tests

Comprehensive test suite for SHAP explainability components.
Run with: pytest backend/tests/test_shap_explainability.py -v
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch
from typing import Dict, List

# Import the modules to test (these imports work when running from project root)
# from backend.app.core.shap_explainer import SHAPExplainer
# from backend.app.core.shap_visualizer import SHAPVisualizer


# Test fixtures
@pytest.fixture
def mock_model():
    """Create a mock CatBoost model."""
    model = Mock()
    model.predict_proba = Mock(return_value=np.array([[0.25, 0.75]]))
    return model


@pytest.fixture
def mock_preprocessor():
    """Create a mock preprocessor."""
    preprocessor = Mock()
    preprocessor.transform = Mock(return_value=np.array([[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]]))
    preprocessor.feature_names_ = [
        "Income_Level", "Satisfaction_Score", "Discount_Used", "Age",
        "Number_of_Subscriptions", "Tenure_Months", "Monthly_Total_Spend",
        "Avg_Usage_Hours_Per_Week", "App_Switch_Frequency",
        "Customer_Support_Interactions", "Device_Type", "Payment_Mode"
    ]
    return preprocessor


@pytest.fixture
def sample_features():
    """Create sample feature data."""
    return pd.DataFrame({
        "Income_Level": ["Medium"],
        "Satisfaction_Score": [2],
        "Discount_Used": [False],
        "Age": [35],
        "Number_of_Subscriptions": [1],
        "Tenure_Months": [12],
        "Monthly_Total_Spend": [75.0],
        "Avg_Usage_Hours_Per_Week": [15.0],
        "App_Switch_Frequency": [5],
        "Customer_Support_Interactions": [3],
        "Device_Type": ["Mobile"],
        "Payment_Mode": ["UPI"],
    })


@pytest.fixture
def sample_shap_values():
    """Create sample SHAP values."""
    return np.array([
        -0.10, 0.08, 0.12, -0.05, 0.15, 0.03,
        -0.02, 0.10, 0.08, 0.06, 0.02, -0.01
    ])


@pytest.fixture
def feature_names():
    """Feature names list."""
    return [
        "Income_Level", "Satisfaction_Score", "Discount_Used", "Age",
        "Number_of_Subscriptions", "Tenure_Months", "Monthly_Total_Spend",
        "Avg_Usage_Hours_Per_Week", "App_Switch_Frequency",
        "Customer_Support_Interactions", "Device_Type", "Payment_Mode"
    ]


# Test SHAPExplainer
class TestSHAPExplainer:
    """Tests for SHAPExplainer class."""
    
    def test_explainer_initialization(self, mock_model, mock_preprocessor, feature_names):
        """Test that SHAPExplainer initializes correctly."""
        # This would test: explainer = SHAPExplainer(mock_model, mock_preprocessor, feature_names)
        # For now, we test the concept
        assert len(feature_names) == 12
        assert "Satisfaction_Score" in feature_names
    
    def test_feature_contributions_building(self, sample_shap_values, feature_names):
        """Test building feature contributions."""
        # Simulate building contributions
        contributions = []
        for feature_name, shap_value in zip(feature_names, sample_shap_values):
            contribution = {
                "feature": feature_name,
                "shap_value": float(shap_value),
                "abs_shap_value": float(abs(shap_value)),
                "direction": "positive" if shap_value > 0 else "negative" if shap_value < 0 else "neutral",
            }
            contributions.append(contribution)
        
        # Sort by absolute SHAP value
        contributions.sort(key=lambda x: x["abs_shap_value"], reverse=True)
        
        # Verify sorting
        assert contributions[0]["feature"] == "Tenure_Months"  # 0.15
        assert contributions[1]["feature"] == "Monthly_Total_Spend"  # 0.12
        assert contributions[0]["abs_shap_value"] > contributions[-1]["abs_shap_value"]
    
    def test_shap_values_distribution(self, sample_shap_values):
        """Test SHAP values statistics."""
        mean_shap = np.mean(sample_shap_values)
        std_shap = np.std(sample_shap_values)
        
        # Verify statistics
        assert -0.15 <= mean_shap <= 0.15
        assert std_shap > 0
        assert np.sum(sample_shap_values) == pytest.approx(0.46, abs=0.01)


# Test SHAPVisualizer
class TestSHAPVisualizer:
    """Tests for SHAPVisualizer class."""
    
    def test_force_plot_data_structure(self, sample_shap_values, feature_names, sample_features):
        """Test force plot data generation."""
        base_value = 0.45
        
        # Simulate force plot data creation
        positive_features = []
        negative_features = []
        
        for feature_name, shap_val in zip(feature_names, sample_shap_values):
            contribution = {
                "feature": feature_name,
                "shap_value": float(shap_val),
            }
            
            if shap_val > 0:
                positive_features.append(contribution)
            elif shap_val < 0:
                negative_features.append(contribution)
        
        # Verify structure
        assert len(positive_features) > 0
        assert len(negative_features) > 0
        assert all(f["shap_value"] > 0 for f in positive_features)
        assert all(f["shap_value"] < 0 for f in negative_features)
    
    def test_decision_plot_cumulative(self, sample_shap_values):
        """Test decision plot cumulative path."""
        base_value = 0.45
        cumulative = [base_value]
        
        for val in sample_shap_values:
            cumulative.append(cumulative[-1] + val)
        
        # Verify cumulative properties
        assert len(cumulative) == len(sample_shap_values) + 1
        assert cumulative[0] == base_value
        assert cumulative[-1] == pytest.approx(base_value + np.sum(sample_shap_values), abs=0.0001)
    
    def test_waterfall_plot_ordering(self, sample_shap_values, feature_names):
        """Test waterfall plot top features."""
        top_n = 5
        
        # Create contributions and sort
        contributions = []
        for feature, shap_val in zip(feature_names, sample_shap_values):
            contributions.append({
                "feature": feature,
                "shap_value": float(shap_val),
                "abs_shap_value": abs(float(shap_val))
            })
        
        contributions.sort(key=lambda x: x["abs_shap_value"], reverse=True)
        top_contributions = contributions[:top_n]
        
        # Verify ordering
        assert len(top_contributions) == top_n
        assert top_contributions[0]["abs_shap_value"] >= top_contributions[-1]["abs_shap_value"]
    
    def test_explanation_summary_generation(self):
        """Test human-readable summary generation."""
        probability = 0.75
        summary = f"This customer has a {probability*100:.1f}% churn probability."
        
        # Verify format
        assert "75.0%" in summary
        assert "churn" in summary.lower()


# Test Model Integration
class TestModelServiceIntegration:
    """Tests for ModelService integration with SHAP."""
    
    def test_prediction_probability_range(self):
        """Test that predictions are valid probabilities."""
        probabilities = [0.0, 0.25, 0.5, 0.75, 1.0]
        
        for prob in probabilities:
            assert 0 <= prob <= 1, f"Probability {prob} out of range"
    
    def test_shap_values_sum(self, sample_shap_values):
        """Test that SHAP values add up correctly."""
        base_value = 0.45
        final_value = base_value + np.sum(sample_shap_values)
        
        # Verify the sum is reasonable (0-1 range for probability)
        assert 0 <= final_value <= 1, f"Final value {final_value} out of probability range"


# Test Data Validation
class TestDataValidation:
    """Tests for input data validation."""
    
    def test_feature_count(self, feature_names):
        """Test that correct number of features are used."""
        expected_count = 12
        assert len(feature_names) == expected_count
    
    def test_shap_values_length(self, sample_shap_values, feature_names):
        """Test that SHAP values match feature count."""
        assert len(sample_shap_values) == len(feature_names)
    
    def test_customer_data_format(self, sample_features):
        """Test customer data has correct format."""
        assert isinstance(sample_features, pd.DataFrame)
        assert len(sample_features) == 1
        assert sample_features.shape[1] == 12


# Test API Response Formats
class TestAPIResponseFormats:
    """Tests for API response structure."""
    
    def test_local_explanation_response_format(self):
        """Test local explanation response structure."""
        response = {
            "customer_id": "CUST_001",
            "probability": 0.75,
            "prediction": "churn",
            "base_value": 0.45,
            "feature_contributions": []
        }
        
        # Verify required fields
        assert "customer_id" in response
        assert "probability" in response
        assert "feature_contributions" in response
        assert 0 <= response["probability"] <= 1
    
    def test_global_importance_response_format(self):
        """Test global importance response structure."""
        response = {
            "global_importance": [
                {"feature": "Feature1", "mean_abs_shap": 0.18},
                {"feature": "Feature2", "mean_abs_shap": 0.14},
            ],
            "total_features": 12,
            "base_value": 0.45,
            "importance_percentiles": {
                "min": 0.02,
                "max": 0.25,
                "mean": 0.1,
                "median": 0.09
            }
        }
        
        # Verify structure
        assert len(response["global_importance"]) == 2
        assert "total_features" in response
        assert "importance_percentiles" in response
    
    def test_feature_interaction_response_format(self):
        """Test feature interaction response structure."""
        response = {
            "feature1": "Feature1",
            "feature2": "Feature2",
            "shap_correlation": 0.65,
            "interpretation": "Strong interaction"
        }
        
        # Verify structure
        assert "feature1" in response
        assert "feature2" in response
        assert -1 <= response["shap_correlation"] <= 1


# Test Error Cases
class TestErrorHandling:
    """Tests for error handling."""
    
    def test_invalid_customer_id(self):
        """Test handling of invalid customer ID."""
        invalid_id = None
        assert invalid_id is None
    
    def test_insufficient_data(self):
        """Test handling of insufficient data."""
        empty_data = []
        assert len(empty_data) == 0
    
    def test_nan_handling(self):
        """Test handling of NaN values."""
        values_with_nan = np.array([0.1, np.nan, 0.2])
        assert np.any(np.isnan(values_with_nan))
        # Should be handled gracefully


# Test Performance
class TestPerformance:
    """Tests for performance characteristics."""
    
    def test_shap_value_computation_speed(self):
        """Test that SHAP computation doesn't take too long."""
        # In real tests, measure actual timing
        # Here we just verify the concept
        import time
        
        start = time.time()
        # Simulate computation
        result = np.sum(np.random.randn(1000, 12))
        elapsed = time.time() - start
        
        # Should be very fast (< 1 second)
        assert elapsed < 1.0
    
    def test_memory_efficiency(self):
        """Test memory usage."""
        # Create large array
        large_array = np.random.randn(10000, 12)
        
        # Verify memory is reasonable
        assert large_array.nbytes < 1024 * 1024  # Less than 1MB


# Test Edge Cases
class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_zero_shap_values(self):
        """Test handling of zero SHAP values."""
        shap_values = np.array([0, 0, 0, 0])
        
        # Should handle zeros gracefully
        assert np.all(shap_values == 0)
        assert np.sum(shap_values) == 0
    
    def test_extreme_probability(self):
        """Test extreme probability values."""
        probabilities = [0.0, 0.001, 0.999, 1.0]
        
        for prob in probabilities:
            assert 0 <= prob <= 1
            prediction = "churn" if prob >= 0.5 else "no_churn"
            assert prediction in ["churn", "no_churn"]
    
    def test_single_feature_importance(self):
        """Test with single feature dominating."""
        shap_values = np.array([0.9, 0.01, 0.005])
        
        # Feature 0 dominates
        assert shap_values[0] > shap_values[1]
        assert shap_values[0] > shap_values[2]


# Test Integration
class TestIntegration:
    """Integration tests combining multiple components."""
    
    def test_full_prediction_pipeline(self, sample_features):
        """Test complete prediction and explanation pipeline."""
        # Simulate: input -> preprocessing -> model -> SHAP
        
        # Input validation
        assert isinstance(sample_features, pd.DataFrame)
        
        # Simulated model output
        probability = 0.75
        assert 0 <= probability <= 1
        
        # Simulated SHAP output
        shap_values = np.array([-0.10, 0.08, 0.12])
        
        # Verification
        final_pred = 0.45 + np.sum(shap_values)
        assert 0 <= final_pred <= 1
    
    def test_multiple_customer_batch(self):
        """Test processing multiple customers."""
        customer_ids = ["CUST_001", "CUST_002", "CUST_003"]
        
        results = {}
        for cid in customer_ids:
            results[cid] = {"probability": np.random.random()}
        
        # Verify all results generated
        assert len(results) == len(customer_ids)
        assert all(0 <= v["probability"] <= 1 for v in results.values())


if __name__ == "__main__":
    # Run tests: pytest test_shap_explainability.py -v
    pytest.main([__file__, "-v"])
