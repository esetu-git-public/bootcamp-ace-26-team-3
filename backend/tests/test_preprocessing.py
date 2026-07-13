import sys
import os
# Add the project root directory to sys.path to resolve the 'backend' import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest
import pandas as pd
import numpy as np
from backend.app.core.preprocessing import SubscriptionPreprocessor

@pytest.fixture
def sample_raw_data():
    return pd.DataFrame({
        "Age": [34, 45, 22, 58, 29],
        "Income_Level": ["Medium", "Low", "High", "Medium", "Low"],
        "Number_of_Subscriptions": [2, 1, 4, 3, 2],
        "Tenure_Months": [8, 2, 15, 24, 5],
        "Monthly_Total_Spend": [79.50, 35.00, 120.00, 55.00, 45.00],
        "Avg_Usage_Hours_Per_Week": [14.5, 8.2, 20.0, 5.5, 10.1],
        "App_Switch_Frequency": [15, 5, 25, 2, 10],
        "Customer_Support_Interactions": [3, 5, 1, 0, 2],
        "Satisfaction_Score": [2, 1, 4, 5, 3],
        "Discount_Used": [0, 1, 0, 0, 1],
        "Device_Type": ["Android", "Web", "iOS", "Android", "iOS"],
        "Payment_Mode": ["UPI", "Wallet", "Credit Card", "Debit Card", "Wallet"]
    })

def test_unfitted_transform_raises_value_error(sample_raw_data):
    preprocessor = SubscriptionPreprocessor()
    with pytest.raises(ValueError, match="Preprocessor has not been fitted yet!"):
        preprocessor.transform(sample_raw_data)

def test_feature_engineering_calculations():
    preprocessor = SubscriptionPreprocessor()
    df = pd.DataFrame({
        "Monthly_Total_Spend": [100.0, 0.0],
        "Number_of_Subscriptions": [2, 0],
        "Avg_Usage_Hours_Per_Week": [10.0, 5.0],
        "Customer_Support_Interactions": [4, 0],
        "Tenure_Months": [10, 0],
        "Satisfaction_Score": [3, 5],
        # other fields to avoid crash
        "Age": [30, 40],
        "Income_Level": ["High", "Medium"],
        "App_Switch_Frequency": [5, 2],
        "Discount_Used": [1, 0],
        "Device_Type": ["Android", "iOS"],
        "Payment_Mode": ["UPI", "Wallet"]
    })
    
    engineered = preprocessor._add_engineered_features(df)
    
    # Check Spend_Per_Subscription: 100.0 / (2 + 1e-5)
    assert np.isclose(engineered.loc[0, "Spend_Per_Subscription"], 100.0 / (2 + 1e-5))
    # 0.0 / (0 + 1e-5)
    assert np.isclose(engineered.loc[1, "Spend_Per_Subscription"], 0.0)

    # Check Usage_Per_Subscription
    assert np.isclose(engineered.loc[0, "Usage_Per_Subscription"], 10.0 / (2 + 1e-5))
    
    # Check Interactions_Per_Tenure_Month
    assert np.isclose(engineered.loc[0, "Interactions_Per_Tenure_Month"], 4.0 / (10 + 1e-5))
    
    # Check Engagement_Score: 10.0 * 3 = 30.0
    assert np.isclose(engineered.loc[0, "Engagement_Score"], 30.0)
    
    # Check Risk_Indicator: 4 * (10.0 - 3) = 28.0
    assert np.isclose(engineered.loc[0, "Risk_Indicator"], 28.0)

def test_income_and_discount_mappings(sample_raw_data):
    preprocessor = SubscriptionPreprocessor()
    preprocessor.fit(sample_raw_data)
    
    # Test mapping with some missing/unseen values
    test_df = pd.DataFrame({
        "Age": [30, 40],
        "Income_Level": [None, "High"], # None should default to 2 (Medium)
        "Number_of_Subscriptions": [2, 1],
        "Tenure_Months": [10, 5],
        "Monthly_Total_Spend": [50.0, 60.0],
        "Avg_Usage_Hours_Per_Week": [12.0, 15.0],
        "App_Switch_Frequency": [8, 12],
        "Customer_Support_Interactions": [1, 2],
        "Satisfaction_Score": [None, 4], # None should default to 3
        "Discount_Used": [None, 1], # None should default to 0
        "Device_Type": ["Android", "iOS"],
        "Payment_Mode": ["UPI", "Wallet"]
    })
    
    transformed = preprocessor.transform(test_df)
    
    # Income_Level column is transformed
    assert transformed.loc[0, "Income_Level"] == 2
    assert transformed.loc[1, "Income_Level"] == 3
    
    # Satisfaction_Score
    assert transformed.loc[0, "Satisfaction_Score"] == 3
    assert transformed.loc[1, "Satisfaction_Score"] == 4
    
    # Discount_Used
    assert transformed.loc[0, "Discount_Used"] == 0
    assert transformed.loc[1, "Discount_Used"] == 1

def test_imputation_and_scaling(sample_raw_data):
    preprocessor = SubscriptionPreprocessor()
    preprocessor.fit(sample_raw_data)
    
    # Create a dataframe with some missing numerical values to verify numerical imputer (median)
    test_df = pd.DataFrame({
        "Age": [None, 45], # first has missing Age
        "Income_Level": ["High", "Low"],
        "Number_of_Subscriptions": [2, 2],
        "Tenure_Months": [8, 8],
        "Monthly_Total_Spend": [79.5, 79.5],
        "Avg_Usage_Hours_Per_Week": [14.5, 14.5],
        "App_Switch_Frequency": [15, 15],
        "Customer_Support_Interactions": [3, 3],
        "Satisfaction_Score": [4, 4],
        "Discount_Used": [1, 1],
        "Device_Type": ["Android", "Web"],
        "Payment_Mode": ["UPI", "Wallet"]
    })
    
    transformed = preprocessor.transform(test_df)
    # The age is imputed and scaled. Let's make sure the age is scaled and not NaN
    assert not transformed["Age"].isna().any()

def test_fit_transform_consistency(sample_raw_data):
    preprocessor1 = SubscriptionPreprocessor()
    transformed1 = preprocessor1.fit_transform(sample_raw_data)
    
    preprocessor2 = SubscriptionPreprocessor()
    preprocessor2.fit(sample_raw_data)
    transformed2 = preprocessor2.transform(sample_raw_data)
    
    pd.testing.assert_frame_equal(transformed1, transformed2)

if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
