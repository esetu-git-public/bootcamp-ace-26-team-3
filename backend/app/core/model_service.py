# ==============================================================================
# MODEL SERVICE MODULE
# ==============================================================================
# This module acts as the unified controller for managing Machine Learning model
# artifacts (serialization, version registration, A/B testing configurations,
# and runtime inference). It supports both Scikit-Learn models and CatBoost models.

import os
import pickle
import sys
import threading
from typing import Any, Dict, List, Optional, TypedDict, Union, cast

import numpy as np
import pandas as pd

from . import preprocessing as preprocessing_module

# ── PICKLE NAMESPACE RESOLUTIONS ─────────────────────────────────────────────
# Set module namespaces before pickle unserialization so that older model pickles
# originally serialized under the 'app' namespace can be resolved correctly under
# the new 'backend.app' namespace structure.
backend_app_module = sys.modules.get("backend.app")
backend_core_module = sys.modules.get("backend.app.core")
if backend_app_module is not None:
    sys.modules.setdefault("app", backend_app_module)
if backend_core_module is not None:
    sys.modules.setdefault("app.core", backend_core_module)
sys.modules.setdefault("app.core.preprocessing", preprocessing_module)

# ── OPTIONAL MODULE IMPORTS ──────────────────────────────────────────────────
# Attempt imports of CatBoost and SHAP. If not installed or incompatible, 
# flag availability as False and gracefully fall back to default models/predict.
try:
    from catboost import CatBoostClassifier
    CATBOOST_AVAILABLE = True
except Exception as e:
    print(f"Warning: CatBoost not available due to: {e}")
    CatBoostClassifier = None
    CATBOOST_AVAILABLE = False

try:
    import shap
    SHAP_AVAILABLE = True
except Exception as e:
    print(f"Warning: SHAP not available due to: {e}")
    shap = None
    SHAP_AVAILABLE = False

if SHAP_AVAILABLE:
    try:
        from .shap_explainer import SHAPExplainer
    except Exception as e:
        print(f"Warning: SHAPExplainer not available: {e}")
        SHAPExplainer = None
else:
    SHAPExplainer = None

# ── FILE PATH RESOLUTIONS ───────────────────────────────────────────────────
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), "model_artifacts")

def _install_pickle_module_aliases() -> None:
    """
    Ensures that older model artifacts serialized under 'app.core.*' can be unpickled
    seamlessly. Also handles compatibilities between numpy versions 1.x and 2.x
    by mapping numpy._core internal module references back to numpy.core.
    """
    try:
        import backend.app as backend_app
        import backend.app.core as backend_core
        from backend.app.core import preprocessing
        sys.modules.setdefault("app", backend_app)
        sys.modules.setdefault("app.core", backend_core)
        sys.modules.setdefault("app.core.preprocessing", preprocessing)
    except Exception:
        pass

    try:
        import numpy
        import numpy.core
        sys.modules.setdefault("numpy._core", numpy.core)
        
        if hasattr(numpy.core, "numeric"):
            sys.modules.setdefault("numpy._core.numeric", numpy.core.numeric)
        if hasattr(numpy.core, "multiarray"):
            sys.modules.setdefault("numpy._core.multiarray", numpy.core.multiarray)
        if hasattr(numpy.core, "umath"):
            sys.modules.setdefault("numpy._core.umath", numpy.core.umath)
    except Exception as e:
        print(f"Warning: Could not install numpy._core aliases: {e}")


# ── A/B TESTING STRUCT TYPE ──────────────────────────────────────────────────
class ABTestConfigDict(TypedDict):
    is_active: bool
    challenger_version: Optional[str]
    traffic_split_percent: int


# ── MODEL SERVICE CONTROLLER ────────────────────────────────────────────────
class ModelService:
    """
    Thread-safe model service managing model loading, preprocessor execution,
    A/B test bucket splitting, local prediction scoring, and SHAP explainability.
    """
    def __init__(self):
        # Version indicators and artifact dictionary
        self.champion_version: Optional[str] = None
        self.models: Dict[str, Dict] = {}  # Format: { "version_str": { "model": obj, "preprocessor": obj, ... } }

        # Active A/B Test Configuration details
        self.ab_test_config: ABTestConfigDict = {
            "is_active": False,
            "challenger_version": None,
            "traffic_split_percent": 0,
        }

        # Lock to ensure thread-safety during runtime model swaps/reloads
        self._lock = threading.Lock()
        self.load_latest_model()

    @property
    def is_ready(self) -> bool:
        """Helper checking if at least one champion model has been successfully initialized."""
        return self.champion_version is not None and self.champion_version in self.models

    def load_latest_model(self):
        """
        Loads the latest registered model version from the database registry table.
        Falls back to 'v1.2.0-catboost' if no database connection or entries exist.
        """
        from ..database import SessionLocal
        from ..models import ModelMetric
        db = SessionLocal()
        try:
            # Query the database for the newest model metric registry record
            latest_metric = db.query(ModelMetric).order_by(ModelMetric.evaluated_at.desc()).first()
            if latest_metric is not None:
                model_version = cast(str, latest_metric.model_version)
                if model_version:
                    print(f"Found latest model version '{model_version}' in registry. Attempting to load.")
                    self.load_artifacts(model_version, as_champion=True)
                else:
                    print("No models found in the registry. Loading fallback champion model version 'v1.2.0-catboost'.")
                    self.load_artifacts("v1.2.0-catboost", as_champion=True)
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
        """
        Loads model pickles (classifier and column transformers) for a specific version string.
        Optionally registers it as the active 'champion' model version.
        """
        sklearn_model_path = os.path.join(ARTIFACT_DIR, f"sklearn_model_{version}.pkl")
        catboost_model_path = os.path.join(ARTIFACT_DIR, f"catboost_model_{version}.cbm")
        preprocessor_path = os.path.join(ARTIFACT_DIR, f"preprocessor_{version}.pkl")

        is_sklearn = False
        model_path = None

        # Determine if version maps to Scikit-learn (.pkl) or CatBoost (.cbm) format
        if os.path.exists(sklearn_model_path):
            model_path = sklearn_model_path
            is_sklearn = True
        elif os.path.exists(catboost_model_path):
            model_path = catboost_model_path
            is_sklearn = False
        else:
            print(f"Artifacts for version '{version}' not found. Falling back to default unversioned artifacts.")
            unversioned_sklearn = os.path.join(ARTIFACT_DIR, "sklearn_model.pkl")
            unversioned_catboost = os.path.join(ARTIFACT_DIR, "catboost_model.cbm")
            preprocessor_path = os.path.join(ARTIFACT_DIR, "preprocessor.pkl")

            if os.path.exists(unversioned_sklearn):
                model_path = unversioned_sklearn
                is_sklearn = True
            elif os.path.exists(unversioned_catboost):
                model_path = unversioned_catboost
                is_sklearn = False

        if not model_path or not os.path.exists(preprocessor_path):
            print(f"Artifacts not found. Searched for version '{version}' and default paths.")
            return

        # Load preprocessor artifacts
        try:
            _install_pickle_module_aliases()
            with open(preprocessor_path, "rb") as f:
                preprocessor = pickle.load(f)
        except Exception as e:
            print(f"Warning: Could not load preprocessor pickle: {e}")
            return

        # Load model classifier based on format type
        try:
            if is_sklearn:
                with open(model_path, "rb") as f:
                    model = pickle.load(f)
            else:
                if not CATBOOST_AVAILABLE or CatBoostClassifier is None:
                    print("Warning: CatBoost not available, cannot load CatBoost model.")
                    return
                model = CatBoostClassifier()
                model.load_model(model_path)
        except Exception as e:
            print(f"Warning: Could not load model: {e}")
            return

        feature_names = []
        if hasattr(preprocessor, "feature_names_"):
            feature_names = list(preprocessor.feature_names_)

        # Load SHAP Visualizers and Maskers if available
        explainer = None
        shap_explainer = None
        if SHAP_AVAILABLE and shap is not None:
            try:
                try:
                    explainer = shap.TreeExplainer(model)
                except Exception:
                    try:
                        explainer = shap.Explainer(model)
                    except Exception:
                        explainer = None
                
                if feature_names and SHAPExplainer is not None:
                    shap_explainer = SHAPExplainer(model, preprocessor, feature_names)
                else:
                    shap_explainer = None
            except Exception as e:
                explainer = None
                shap_explainer = None
                print(f"Warning: Could not initialize SHAP explainer: {str(e)}")

        # Register version artifacts in cache dictionary
        self.models[version] = {
            "model": model,
            "preprocessor": preprocessor,
            "explainer": explainer,
            "shap_explainer": shap_explainer,
            "feature_names": feature_names
        }

        # Set champion mappings if flagged as champion
        if as_champion:
            self.champion_version = version
            print(f"Successfully loaded champion model version '{version}'.")
            self.model = model
            self.preprocessor = preprocessor
            self.explainer = explainer
            self.shap_explainer = shap_explainer
            self.feature_names = feature_names
        else:
            print(f"Successfully loaded challenger model version '{version}'.")

    def get_ab_test_status(self) -> Dict:
        """Helper to check the active status of A/B split versions and metrics mapping."""
        return {
            "is_active": self.ab_test_config["is_active"],
            "champion_version": self.champion_version,
            "challenger_version": self.ab_test_config["challenger_version"],
            "traffic_split_percent": self.ab_test_config["traffic_split_percent"],
            "loaded_models": list(self.models.keys())
        }

    def get_model_version_for_request(self, customer_id: Union[int, str]) -> Optional[str]:
        """
        Calculates a hash bucket for the customer ID. Determines deterministically 
        if this customer request gets the champion version or the challenger version.
        """
        with self._lock:
            if not self.is_ready:
                return None
            
            if not self.ab_test_config["is_active"] or not self.ab_test_config["challenger_version"]:
                return self.champion_version

            try:
                cid = int(customer_id)
            except (ValueError, TypeError):
                import hashlib
                cid = int(hashlib.md5(str(customer_id).encode()).hexdigest(), 16)

            bucket = cid % 100
            if bucket < self.ab_test_config["traffic_split_percent"]:
                return self.ab_test_config["challenger_version"]
            return self.champion_version

    def _shap_values(self, processed_features: pd.DataFrame) -> np.ndarray:
        """Runs the active SHAP explainer to calculate baseline feature scores."""
        if self.explainer is None:
            num_features = len(self.feature_names) if self.feature_names else processed_features.shape[1]
            return np.zeros((processed_features.shape[0], num_features))

        if hasattr(self.explainer, "shap_values"):
            raw_values = self.explainer.shap_values(processed_features)
        elif callable(self.explainer):
            explanation = self.explainer(processed_features)
            raw_values = explanation.values if hasattr(explanation, "values") else explanation
        else:
            num_features = len(self.feature_names) if self.feature_names else processed_features.shape[1]
            return np.zeros((processed_features.shape[0], num_features))

        if isinstance(raw_values, list):
            shap_values = raw_values[1] if len(raw_values) > 1 else raw_values[0]
        else:
            shap_values = raw_values
        return np.array(shap_values)

    def predict_and_explain(self, raw_features: pd.DataFrame, model_version: Optional[str] = None) -> Dict[str, Any]:
        """
        Synchronously calculates churn prediction probability, standard confidence
        intervals, and basic local SHAP explanation mappings for a single customer row.
        """
        with self._lock:
            version = model_version or self.champion_version
            if not version or version not in self.models:
                raise RuntimeError(f"Model artifacts for version '{version}' are not available.")

            artifacts = self.models[version]
            preprocessor = artifacts["preprocessor"]
            model = artifacts["model"]
            explainer = artifacts["explainer"]
            feature_names = artifacts["feature_names"]

            # Transform raw features using cached preprocessing pipeline
            processed = preprocessor.transform(raw_features)
            probabilities = model.predict_proba(processed)[:, 1]
            probability = float(probabilities[0])

            # Extract local SHAP explanations
            if explainer is not None:
                if hasattr(explainer, "shap_values"):
                    raw_values = explainer.shap_values(processed)
                elif callable(explainer):
                    explanation = explainer(processed)
                    raw_values = explanation.values if hasattr(explanation, "values") else explanation
                else:
                    raw_values = None

                if raw_values is not None:
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
            else:
                explainability = {}
            
            # Formulate a 95% Confidence Interval using standard Binomial proportion margins
            z_score = 1.96  
            margin_of_error = z_score * np.sqrt((probability * (1 - probability)) / 100)
            confidence_lower = max(0.0, probability - margin_of_error)
            confidence_upper = min(1.0, probability + margin_of_error)

            return {
                "probability": probability,
                "probability_confidence_lower": confidence_lower,
                "probability_confidence_upper": confidence_upper,
                "explainability": explainability,
            }

    def predict_with_advanced_explanation(self, raw_features: pd.DataFrame, model_version: Optional[str] = None) -> Dict[str, Any]:
        """Runs the enhanced SHAP explainability calculations, yielding base value shifts."""
        with self._lock:
            version = model_version or self.champion_version
            if not version or version not in self.models:
                raise RuntimeError(f"Model artifacts for version '{version}' are not available.")
            
            artifacts = self.models[version]
            shap_explainer = artifacts["shap_explainer"]
            
            if shap_explainer is None:
                return self.predict_and_explain(raw_features, model_version=version)
            
            return shap_explainer.explain_prediction(raw_features, return_base_value=True)

    def get_global_importance(self, processed_features: Optional[pd.DataFrame] = None, top_n: int = 10) -> Dict:
        """Aggregates absolute SHAP values across a batch of customers to yield global feature priorities."""
        with self._lock:
            if not self.is_ready or self.shap_explainer is None:
                raise RuntimeError("Model artifacts are not available or SHAP explainer not initialized.")
            
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
        """Runs interaction analysis to check if changes in feature1 modify the SHAP impact of feature2."""
        with self._lock:
            if not self.is_ready or self.shap_explainer is None:
                raise RuntimeError("Model artifacts are not available or SHAP explainer not initialized.")
            
            return self.shap_explainer.feature_interaction_analysis(raw_features, feature1, feature2)

    def get_shap_summary_statistics(self, processed_features: pd.DataFrame) -> Dict:
        """Yields mean, max, and min SHAP metrics for standard audits."""
        with self._lock:
            if not self.is_ready or self.shap_explainer is None:
                raise RuntimeError("Model artifacts are not available or SHAP explainer not initialized.")
            
            return self.shap_explainer.summary_statistics(processed_features)

    def reload_model(self, version: str):
        """Reloads active model artifacts at runtime. Thread-safe."""
        with self._lock:
            print(f"Acquired lock to reload model. Attempting to load version '{version}'...")
            self.load_artifacts(version, as_champion=True)
            if not self.is_ready or self.champion_version != version:
                print(f"Failed to reload to version '{version}'. Restoring latest available model.")
                self.load_latest_model() 


# Instantiates singleton instance for application importing
model_service = ModelService()

