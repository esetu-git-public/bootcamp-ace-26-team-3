import os
import pickle
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer

class SubscriptionPreprocessor:
    def __init__(self):
        # Numerical features to impute and scale (including engineered features)
        self.num_cols = [
            "Age",
            "Number_of_Subscriptions",
            "Tenure_Months",
            "Monthly_Total_Spend",
            "Avg_Usage_Hours_Per_Week",
            "App_Switch_Frequency",
            "Customer_Support_Interactions",
            "Spend_Per_Subscription",
            "Usage_Per_Subscription",
            "Interactions_Per_Tenure_Month",
            "Engagement_Score",
            "Risk_Indicator"
        ]
        
        # Categorical nominal features to impute and one-hot encode
        self.cat_cols = [
            "Device_Type",
            "Payment_Mode"
        ]
        
        # Ordinal mapping for Income_Level
        self.income_mapping = {"Low": 1, "Medium": 2, "High": 3}
        
        # Transformers setup
        self.num_imputer = SimpleImputer(strategy="median")
        self.scaler = StandardScaler()
        
        self.cat_imputer = SimpleImputer(strategy="most_frequent")
        self.encoder = OneHotEncoder(drop="first", handle_unknown="ignore", sparse_output=False)
        
        self.feature_names_ = None
        self.is_fitted = False

    def _add_engineered_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["Spend_Per_Subscription"] = df["Monthly_Total_Spend"] / (df["Number_of_Subscriptions"] + 1e-5)
        df["Usage_Per_Subscription"] = df["Avg_Usage_Hours_Per_Week"] / (df["Number_of_Subscriptions"] + 1e-5)
        df["Interactions_Per_Tenure_Month"] = df["Customer_Support_Interactions"] / (df["Tenure_Months"] + 1e-5)
        df["Engagement_Score"] = df["Avg_Usage_Hours_Per_Week"] * df["Satisfaction_Score"]
        df["Risk_Indicator"] = df["Customer_Support_Interactions"] * (10.0 - df["Satisfaction_Score"])
        return df

    def fit(self, df: pd.DataFrame):
        df = self._add_engineered_features(df)
        # Fit numerical features
        num_data = df[self.num_cols]
        num_imputed = self.num_imputer.fit_transform(num_data)
        self.scaler.fit(num_imputed)
        
        # Fit categorical features
        cat_data = df[self.cat_cols]
        cat_imputed = self.cat_imputer.fit_transform(cat_data)
        self.encoder.fit(cat_imputed)
        
        # Determine output feature names
        encoded_cat_names = self.encoder.get_feature_names_out(self.cat_cols)
        self.feature_names_ = (
            ["Income_Level", "Satisfaction_Score", "Discount_Used"] +
            self.num_cols +
            list(encoded_cat_names)
        )
        self.is_fitted = True
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self.is_fitted:
            raise ValueError("Preprocessor has not been fitted yet!")
            
        df = self._add_engineered_features(df)
        
        # 1. Map Income_Level ordinally (default to Medium/2 if not found)
        income_mapped = df["Income_Level"].map(self.income_mapping).fillna(2).astype(int)
        
        # 2. Map Discount_Used to binary (default to 0 if not found)
        discount_mapped = df["Discount_Used"].fillna(0).astype(int)
        
        # 3. Satisfaction_Score passed through (default to 3/medium if not found)
        satisfaction_score = df["Satisfaction_Score"].fillna(3).astype(int)
        
        # 4. Handle numerical features
        num_data = df[self.num_cols]
        num_imputed = self.num_imputer.transform(num_data)
        num_scaled = self.scaler.transform(num_imputed)
        
        # 5. Handle categorical nominal features
        cat_data = df[self.cat_cols]
        cat_imputed = self.cat_imputer.transform(cat_data)
        cat_encoded = self.encoder.transform(cat_imputed)
        
        # Combine all features in the designed order
        X_combined = np.hstack([
            income_mapped.values.reshape(-1, 1),
            satisfaction_score.values.reshape(-1, 1),
            discount_mapped.values.reshape(-1, 1),
            num_scaled,
            cat_encoded
        ])
        
        return pd.DataFrame(X_combined, columns=self.feature_names_)

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.fit(df).transform(df)

if __name__ == "__main__":
    print("Starting Data Preprocessing Pipeline...")
    
    # Locate dataset
    # We find dataset path relative to root directory
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    csv_path = os.path.join(base_dir, "Subscription Fatigue.csv")
    
    if not os.path.exists(csv_path):
        print(f"Error: Dataset file not found at {csv_path}")
        exit(1)
        
    print(f"Loading dataset from: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"Loaded dataset with shape: {df.shape}")
    
    # Target column
    target_col = "Will_Cancel_Next_3_Months"
    if target_col not in df.columns:
        print(f"Error: Target column {target_col} not found in dataset.")
        exit(1)
        
    # Split into features and target
    X_raw = df.drop(columns=[target_col, "Customer_ID"], errors="ignore")
    y = df[target_col]
    
    # Perform Stratified Train-Test Split (80:20)
    print("Splitting dataset into 80% train and 20% test sets (stratified)...")
    X_train_raw, X_test_raw, y_train, y_test = train_test_split(
        X_raw, y, test_size=0.2, stratify=y, random_state=42
    )
    
    # Instantiate and fit preprocessor
    print("Fitting preprocessing pipeline on training data...")
    preprocessor = SubscriptionPreprocessor()
    X_train_processed = preprocessor.fit_transform(X_train_raw)
    X_test_processed = preprocessor.transform(X_test_raw)
    
    # Attach target variable to processed splits
    train_df = X_train_processed.copy()
    train_df[target_col] = y_train.values
    
    test_df = X_test_processed.copy()
    test_df[target_col] = y_test.values
    
    # Create dataset output directory
    dataset_dir = os.path.join(base_dir, "dataset")
    os.makedirs(dataset_dir, exist_ok=True)
    
    # Save preprocessed splits
    train_out_path = os.path.join(dataset_dir, "train_preprocessed.csv")
    test_out_path = os.path.join(dataset_dir, "test_preprocessed.csv")
    
    print(f"Saving preprocessed training split to: {train_out_path}")
    train_df.to_csv(train_out_path, index=False)
    
    print(f"Saving preprocessed testing split to: {test_out_path}")
    test_df.to_csv(test_out_path, index=False)
    
    # Save the fitted preprocessor object
    preprocessor_pkl_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "preprocessor.pkl"))
    print(f"Saving fitted preprocessor object to: {preprocessor_pkl_path}")
    with open(preprocessor_pkl_path, "wb") as f:
        pickle.dump(preprocessor, f)
        
    print("\nData Preprocessing pipeline completed successfully!")
    print(f"Preprocessed train shape: {train_df.shape}")
    print(f"Preprocessed test shape: {test_df.shape}")
    print(f"Churn rate in training split: {train_df[target_col].mean():.4f}")
    print(f"Churn rate in testing split: {test_df[target_col].mean():.4f}")
