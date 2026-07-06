import os
import pickle
import sys
from typing import Dict, Optional, List

import numpy as np
import pandas as pd

from . import preprocessing as preprocessing_module

backend_app_module = sys.modules.get("backend.app")
backend_core_module = sys.modules.get("backend.app.core")
if backend_app_module is not None:
    sys.modules.setdefault("app", backend_app_module)
if backend_core_module is not None:
    sys.modules.setdefault("app.core", backend_core_module)
sys.modules.setdefault("app.core.preprocessing", preprocessing_module)

try:
    from catboost import CatBoostClassifier
    CATBOOST_AVAILABLE = True
except Exception as e:
    print(f"Warning: CatBoost not available due to: {e}")
    CatBoostClassifier = None
    CATBOOST_AVAILABLE = False

# Try to import SHAP, but make it optional if there are compatibility issues
try:
    import shap
    SHAP_AVAILABLE = True
except Exception as e:
    print(f"Warning: SHAP not available due to: {e}")
    shap = None
    SHAP_AVAILABLE = False

# Only import SHAPExplainer if SHAP is available
if SHAP_AVAILABLE:
    try:
        from .shap_explainer import SHAPExplainer
    except Exception as e:
        print(f"Warning: SHAPExplainer not available: {e}")
        SHAPExplainer = None
else:
    SHAPExplainer = None


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), "model_artifacts")
PREPROCESSOR_PATH = os.path.join(ARTIFACT_DIR, "preprocessor.pkl")
MODEL_PATH = os.path.join(ARTIFACT_DIR, "catboost_model.cbm")


def _install_pickle_module_aliases() -> None:
    """Allow older artifacts pickled as app.core.* to load as backend.app.core.*."""
    try:
        import backend.app as backend_app
        import backend.app.core as backend_core
        from backend.app.core import preprocessing
    except Exception:
        return

    sys.modules.setdefault("app", backend_app)
    sys.modules.setdefault("app.core", backend_core)
    sys.modules.setdefault("app.core.preprocessing", preprocessing)


class ModelService:
    def __init__(self):
        self.preprocessor = None
        self.model = None
        self.explainer = None
        self.shap_explainer = None  # Enhanced SHAP explainer
        self.feature_names = []
        self.is_ready = False
        self._load_artifacts()

    def _load_artifacts(self):
        if not os.path.exists(PREPROCESSOR_PATH) or not os.path.exists(MODEL_PATH):
            return

        try:
            _install_pickle_module_aliases()
            with open(PREPROCESSOR_PATH, "rb") as f:
                self.preprocessor = pickle.load(f)
        except (ModuleNotFoundError, AttributeError, pickle.UnpicklingError) as e:
            print(f"Warning: Could not load preprocessor pickle: {e}. Continuing without it.")
            self.preprocessor = None

        if not CATBOOST_AVAILABLE or CatBoostClassifier is None:
            print("Warning: CatBoost not available, ML model service disabled.")
            self.model = None
            self.is_ready = False
            return

        try:
            self.model = CatBoostClassifier()
            self.model.load_model(MODEL_PATH)
        except Exception as e:
            print(f"Warning: Could not load CatBoost model: {e}")
            self.model = None
            return

        if hasattr(self.preprocessor, "feature_names_"):
            self.feature_names = list(self.preprocessor.feature_names_)

        # Only initialize SHAP if available and model loaded
        if self.model is not None and SHAP_AVAILABLE and shap is not None:
            try:
                self.explainer = shap.TreeExplainer(self.model)
                # Initialize enhanced SHAP explainer
                if self.feature_names and SHAPExplainer is not None:
                    self.shap_explainer = SHAPExplainer(self.model, self.preprocessor, self.feature_names)
                self.is_ready = True
            except Exception as e:
                self.explainer = None
                self.shap_explainer = None
                self.is_ready = False
                print(f"Warning: Could not initialize SHAP explainer: {str(e)}")
        elif self.model is not None:
            # SHAP not available, but core model is still ready
            self.explainer = None
            self.shap_explainer = None
            self.is_ready = True
            print("Warning: SHAP not available, core model features will work but SHAP explainability disabled")
        else:
            self.is_ready = False
            print("Warning: Model not loaded")

    def _shap_values(self, processed_features: pd.DataFrame) -> np.ndarray:
        raw_values = self.explainer.shap_values(processed_features)
        if isinstance(raw_values, list):
            shap_values = raw_values[1] if len(raw_values) > 1 else raw_values[0]
        else:
            shap_values = raw_values
        return np.array(shap_values)

    def predict_and_explain(self, raw_features: pd.DataFrame) -> Dict[str, object]:
        """Legacy method for backward compatibility."""
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

    def predict_with_advanced_explanation(self, raw_features: pd.DataFrame) -> Dict[str, object]:
        """Enhanced prediction with detailed SHAP explanations."""
        if not self.is_ready:
            raise RuntimeError("Model artifacts are not available.")
        
        if self.shap_explainer is None:
            # Fallback to legacy method
            return self.predict_and_explain(raw_features)
        
        return self.shap_explainer.explain_prediction(raw_features, return_base_value=True)

    def get_global_importance(self, processed_features: Optional[pd.DataFrame] = None, top_n: int = 10) -> Dict:
        """Get global feature importance using SHAP."""
        if not self.is_ready or self.shap_explainer is None:
            raise RuntimeError("Model artifacts are not available or SHAP explainer not initialized.")
        
        # If no data provided, return empty but valid structure
        if processed_features is None:
            return {
                "global_importance": [],
                "total_features": len(self.feature_names),
                "base_value": 0.0,
                "importance_percentiles": {}
            }
        
        return self.shap_explainer.global_feature_importance(processed_features, top_n=top_n)

    def get_feature_interaction(
        self, 
        raw_features: pd.DataFrame,
        feature1: str, 
        feature2: str
    ) -> Dict:
        """Analyze interaction between two features."""
        if not self.is_ready or self.shap_explainer is None:
            raise RuntimeError("Model artifacts are not available or SHAP explainer not initialized.")
        
        return self.shap_explainer.feature_interaction_analysis(raw_features, feature1, feature2)

    def get_shap_summary_statistics(self, processed_features: pd.DataFrame) -> Dict:
        """Get SHAP statistics for dataset."""
        if not self.is_ready or self.shap_explainer is None:
            raise RuntimeError("Model artifacts are not available or SHAP explainer not initialized.")
        
        return self.shap_explainer.summary_statistics(processed_features)


model_service = ModelService()
