import os
import pickle

import numpy as np
import pandas as pd
import shap
from catboost import CatBoostClassifier
from sklearn.model_selection import train_test_split

from .preprocessing import SubscriptionPreprocessor

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
RAW_DATA_PATH = os.path.join(BASE_DIR, "Subscription Fatigue.csv")
ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), "model_artifacts")
PREPROCESSOR_PATH = os.path.join(ARTIFACT_DIR, "preprocessor.pkl")
MODEL_PATH = os.path.join(ARTIFACT_DIR, "catboost_model.cbm")


def load_raw_dataset() -> pd.DataFrame:
    if os.path.exists(RAW_DATA_PATH):
        return pd.read_csv(RAW_DATA_PATH)

    raise FileNotFoundError(
        f"Raw dataset not found at {RAW_DATA_PATH}. Place the CSV file at the project root."
    )


def build_training_set(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    target_col = "Will_Cancel_Next_3_Months"
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in dataset.")

    feature_df = df.copy()
    if "Customer_ID" in feature_df.columns:
        feature_df = feature_df.drop(columns=["Customer_ID"])

    y = feature_df[target_col].astype(int)
    X = feature_df.drop(columns=[target_col])
    return X, y


def train():
    print("Loading raw dataset...")
    df = load_raw_dataset()

    print("Preparing training data...")
    X, y = build_training_set(df)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    print("Fitting preprocessing pipeline...")
    preprocessor = SubscriptionPreprocessor()
    X_train_processed = preprocessor.fit_transform(X_train)
    X_test_processed = preprocessor.transform(X_test)

    print("Training CatBoost classifier...")
    model = CatBoostClassifier(
        iterations=200,
        learning_rate=0.08,
        depth=6,
        random_seed=42,
        verbose=False,
    )
    model.fit(
        X_train_processed,
        y_train,
        eval_set=(X_test_processed, y_test),
        early_stopping_rounds=25,
        verbose=False,
    )

    print("Computing SHAP explainability on evaluation set...")
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test_processed)
    if isinstance(shap_values, list):
        shap_values = shap_values[1] if len(shap_values) > 1 else shap_values[0]
    shap_array = np.array(shap_values)
    feature_importance = np.abs(shap_array).mean(axis=0)

    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    with open(PREPROCESSOR_PATH, "wb") as f:
        pickle.dump(preprocessor, f)

    model.save_model(MODEL_PATH)

    importance = {
        feature: float(value)
        for feature, value in zip(preprocessor.feature_names_, feature_importance.tolist())
    }

    print("Model training completed.")
    print(f"Saved preprocessor to: {PREPROCESSOR_PATH}")
    print(f"Saved CatBoost model to: {MODEL_PATH}")
    print("Feature importance (SHAP mean abs):")
    for feature, value in importance.items():
        print(f"  {feature}: {value:.6f}")

    return {
        "model_path": MODEL_PATH,
        "preprocessor_path": PREPROCESSOR_PATH,
        "feature_importance": importance,
    }


if __name__ == "__main__":
    train()
