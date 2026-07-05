import os
import pickle
from typing import Dict, Optional

import numpy as np
import pandas as pd
import shap
from catboost import CatBoostClassifier


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), "model_artifacts")
PREPROCESSOR_PATH = os.path.join(ARTIFACT_DIR, "preprocessor.pkl")
MODEL_PATH = os.path.join(ARTIFACT_DIR, "catboost_model.cbm")


class ModelService:
    def __init__(self):
        self.preprocessor = None
        self.model = None
        self.explainer = None
        self.feature_names = []
        self.is_ready = False
        self._load_artifacts()

    def _load_artifacts(self):
        if not os.path.exists(PREPROCESSOR_PATH) or not os.path.exists(MODEL_PATH):
            return

        with open(PREPROCESSOR_PATH, "rb") as f:
            self.preprocessor = pickle.load(f)

        self.model = CatBoostClassifier()
        self.model.load_model(MODEL_PATH)

        if hasattr(self.preprocessor, "feature_names_"):
            self.feature_names = list(self.preprocessor.feature_names_)

        try:
            self.explainer = shap.TreeExplainer(self.model)
            self.is_ready = True
        except Exception:
            self.explainer = None
            self.is_ready = False

    def _shap_values(self, processed_features: pd.DataFrame) -> np.ndarray:
        raw_values = self.explainer.shap_values(processed_features)
        if isinstance(raw_values, list):
            shap_values = raw_values[1] if len(raw_values) > 1 else raw_values[0]
        else:
            shap_values = raw_values
        return np.array(shap_values)

    def predict_and_explain(self, raw_features: pd.DataFrame) -> Dict[str, object]:
        if not self.is_ready:
            raise RuntimeError("Model artifacts are not available.")

        processed = self.preprocessor.transform(raw_features)
        probabilities = self.model.predict_proba(processed)[:, 1]
        probability = float(probabilities[0])

        shap_values = self._shap_values(processed)
        shap_row = shap_values[0]
        explainability = {
            feature: float(value)
            for feature, value in zip(self.feature_names, shap_row.tolist())
        }
        
        # Calculate confidence interval (95% CI approximation)
        # Using binomial proportion confidence interval
        z_score = 1.96  # 95% confidence
        margin_of_error = z_score * np.sqrt((probability * (1 - probability)) / 100)
        confidence_lower = max(0.0, probability - margin_of_error)
        confidence_upper = min(1.0, probability + margin_of_error)

        return {
            "probability": probability,
            "probability_confidence_lower": confidence_lower,
            "probability_confidence_upper": confidence_upper,
            "explainability": explainability,
        }


model_service = ModelService()
