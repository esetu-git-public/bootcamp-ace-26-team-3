import os
import pickle
import sys
import threading
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
        # Main model artifacts
        self.champion_version: Optional[str] = None
        self.models: Dict[str, Dict] = {}  # Stores artifacts for each loaded version

        # A/B Test configuration
        self.ab_test_config = {
            "is_active": False,
            "challenger_version": None,
            "traffic_split_percent": 0,  # Percentage of traffic to challenger
        }

        self._lock = threading.Lock()
        self.load_latest_model()

    @property
    def is_ready(self) -> bool:
        """Check if the champion model is loaded and ready."""
        return self.champion_version is not None and self.champion_version in self.models

    def load_latest_model(self):
        """Loads the latest model from the database-backed model registry."""
        # This will become the default "champion" model
        from app.database import SessionLocal
        from app.models import ModelMetric
        db = SessionLocal()
        try:
            latest_metric = db.query(ModelMetric).order_by(ModelMetric.evaluated_at.desc()).first()
            if latest_metric and latest_metric.model_version:
                print(f"Found latest model version '{latest_metric.model_version}' in registry. Attempting to load.")
                self.load_artifacts(latest_metric.model_version, as_champion=True)
            else:
                print("No models found in the registry. Loading fallback champion model version 'v1.2.0-catboost'.")
                self.load_artifacts("v1.2.0-catboost", as_champion=True)
        except Exception as e:
            print(f"Warning: Could not load latest model from registry due to: {e}. Loading fallback champion model version 'v1.2.0-catboost'.")
            try:
                self.load_artifacts("v1.2.0-catboost", as_champion=True)
            except Exception as load_err:
                print(f"Error loading fallback model: {load_err}")
        finally:
            db.close()

    def load_artifacts(self, version: str, as_champion: bool = False):
        """Loads model artifacts for a specific version."""
        model_path = os.path.join(ARTIFACT_DIR, f"catboost_model_{version}.cbm")
        preprocessor_path = os.path.join(ARTIFACT_DIR, f"preprocessor_{version}.pkl")

        if not os.path.exists(preprocessor_path) or not os.path.exists(model_path):
            print(f"Artifacts for version '{version}' not found. Falling back to default unversioned artifacts.")
            model_path = os.path.join(ARTIFACT_DIR, "catboost_model.cbm")
            preprocessor_path = os.path.join(ARTIFACT_DIR, "preprocessor.pkl")

        if not os.path.exists(preprocessor_path) or not os.path.exists(model_path):
            print(f"Artifacts not found. Searched for version '{version}' and default paths.")
            return

        try:
            _install_pickle_module_aliases()
            with open(preprocessor_path, "rb") as f:
                preprocessor = pickle.load(f)
        except (ModuleNotFoundError, AttributeError, pickle.UnpicklingError) as e:
            print(f"Warning: Could not load preprocessor pickle: {e}. Continuing without it.")
            return # Cannot proceed without a preprocessor

        if not CATBOOST_AVAILABLE or CatBoostClassifier is None:
            print("Warning: CatBoost not available, ML model service disabled.")
            return

        try:
            model = CatBoostClassifier()
            model.load_model(model_path)
        except Exception as e:
            print(f"Warning: Could not load CatBoost model: {e}")
            return

        feature_names = []
        if hasattr(preprocessor, "feature_names_"):
            feature_names = list(preprocessor.feature_names_)

        # Only initialize SHAP if available and model loaded
        if SHAP_AVAILABLE and shap is not None:
            try:
                explainer = shap.TreeExplainer(model)
                # Initialize enhanced SHAP explainer
                if feature_names and SHAPExplainer is not None:
                    shap_explainer = SHAPExplainer(model, preprocessor, feature_names)
                else:
                    shap_explainer = None
            except Exception as e:
                explainer = None
                shap_explainer = None
                print(f"Warning: Could not initialize SHAP explainer: {str(e)}")
        else:
            explainer = None
            shap_explainer = None

        # Store loaded artifacts
        self.models[version] = {
            "model": model,
            "preprocessor": preprocessor,
            "explainer": explainer,
            "shap_explainer": shap_explainer,
            "feature_names": feature_names
        }

        if as_champion:
            self.champion_version = version
            print(f"Successfully loaded champion model version '{version}'.")
            # Setup aliases for backwards compatibility and easy access
            self.model = model
            self.preprocessor = preprocessor
            self.explainer = explainer
            self.shap_explainer = shap_explainer
            self.feature_names = feature_names
        else:
            print(f"Successfully loaded challenger model version '{version}'.")

    def get_ab_test_status(self) -> Dict:
        """Get status of the A/B test and loaded models."""
        return {
            "is_active": self.ab_test_config["is_active"],
            "champion_version": self.champion_version,
            "challenger_version": self.ab_test_config["challenger_version"],
            "traffic_split_percent": self.ab_test_config["traffic_split_percent"],
            "loaded_models": list(self.models.keys())
        }

    def get_model_version_for_request(self, customer_id: int) -> Optional[str]:
        """Determine which model version to use for a given customer based on A/B test config."""
        with self._lock:
            if not self.is_ready:
                return None
            
            if not self.ab_test_config["is_active"] or not self.ab_test_config["challenger_version"]:
                return self.champion_version

            # Deterministic split based on customer_id hash
            try:
                cid = int(customer_id)
            except (ValueError, TypeError):
                # Fallback to simple hash of string
                import hashlib
                cid = int(hashlib.md5(str(customer_id).encode()).hexdigest(), 16)

            bucket = cid % 100
            if bucket < self.ab_test_config["traffic_split_percent"]:
                return self.ab_test_config["challenger_version"]
            return self.champion_version

    def _shap_values(self, processed_features: pd.DataFrame) -> np.ndarray:
        raw_values = self.explainer.shap_values(processed_features)
        if isinstance(raw_values, list):
            shap_values = raw_values[1] if len(raw_values) > 1 else raw_values[0]
        else:
            shap_values = raw_values
        return np.array(shap_values)

    def predict_and_explain(self, raw_features: pd.DataFrame, model_version: Optional[str] = None) -> Dict[str, object]:
        """Legacy method for backward compatibility."""
        with self._lock:
            version = model_version or self.champion_version
            if not version or version not in self.models:
                raise RuntimeError(f"Model artifacts for version '{version}' are not available.")

            artifacts = self.models[version]
            preprocessor = artifacts["preprocessor"]
            model = artifacts["model"]
            explainer = artifacts["explainer"]
            feature_names = artifacts["feature_names"]

            processed = preprocessor.transform(raw_features)
            probabilities = model.predict_proba(processed)[:, 1]
            probability = float(probabilities[0])

            if explainer is not None:
                raw_values = explainer.shap_values(processed)
                if isinstance(raw_values, list):
                    shap_values = raw_values[1] if len(raw_values) > 1 else raw_values[0]
                else:
                    shap_values = raw_values
                shap_row = np.array(shap_values)[0]
                explainability = {
                    feature: float(value)
                    for feature, value in zip(feature_names, shap_row.tolist())
                }
            else:
                explainability = {}
            
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

    def predict_with_advanced_explanation(self, raw_features: pd.DataFrame, model_version: Optional[str] = None) -> Dict[str, object]:
        """Enhanced prediction with detailed SHAP explanations."""
        with self._lock:
            version = model_version or self.champion_version
            if not version or version not in self.models:
                raise RuntimeError(f"Model artifacts for version '{version}' are not available.")
            
            artifacts = self.models[version]
            shap_explainer = artifacts["shap_explainer"]
            
            if shap_explainer is None:
                # Fallback to legacy method
                return self.predict_and_explain(raw_features, model_version=version)
            
            return shap_explainer.explain_prediction(raw_features, return_base_value=True)

    def get_global_importance(self, processed_features: Optional[pd.DataFrame] = None, top_n: int = 10) -> Dict:
        """Get global feature importance using SHAP."""
        with self._lock:
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
        with self._lock:
            if not self.is_ready or self.shap_explainer is None:
                raise RuntimeError("Model artifacts are not available or SHAP explainer not initialized.")
            
            return self.shap_explainer.feature_interaction_analysis(raw_features, feature1, feature2)

    def get_shap_summary_statistics(self, processed_features: pd.DataFrame) -> Dict:
        """Get SHAP statistics for dataset."""
        with self._lock:
            if not self.is_ready or self.shap_explainer is None:
                raise RuntimeError("Model artifacts are not available or SHAP explainer not initialized.")
            
            return self.shap_explainer.summary_statistics(processed_features)

    def reload_model(self, version: str):
        """Thread-safe method to reload model artifacts."""
        with self._lock:
            print(f"Acquired lock to reload model. Attempting to load version '{version}'...")
            self.load_artifacts(version, as_champion=True)
            if not self.is_ready or self.champion_version != version:
                print(f"Failed to reload to version '{version}'. Restoring latest available model.")
                self.load_latest_model() # Attempt to restore a working model


model_service = ModelService()
