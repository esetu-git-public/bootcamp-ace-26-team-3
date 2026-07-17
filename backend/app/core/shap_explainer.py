"""
Enhanced SHAP Explainability Module

Provides comprehensive explainability for CatBoost churn predictions using SHAP.
Includes local explanations, global feature importance, and visualization support.
"""

import os
import json
import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional, cast
from catboost import CatBoostClassifier
import pickle

# Try to import SHAP, but make it optional to prevent build failure on non-linux boxes
try:
    import shap
    SHAP_AVAILABLE = True
except Exception as e:
    print(f"Warning: SHAP import failed: {e}")
    shap = None
    SHAP_AVAILABLE = False


class SHAPExplainer:
    """
    Advanced SHAP explainer for CatBoost models.
    Translates model weights and decision splits into additive feature contributions
    matching game theoretic properties (Shapley Values).
    """
    
    def __init__(self, model: CatBoostClassifier, preprocessor, feature_names: List[str]):
        """
        Initialize SHAP explainer.
        
        Args:
            model: Trained CatBoost classifier
            preprocessor: Fitted preprocessor (e.g., ColumnTransformer)
            feature_names: List of feature names
        """
        self.model = model
        self.preprocessor = preprocessor
        self.feature_names = feature_names
        self.explainer: Any = None
        self.background_data = None
        self._initialize_explainer()
    
    def _initialize_explainer(self):
        """Initialize SHAP explainer, falling back to model agnostic Explainer if TreeExplainer fails."""
        if not SHAP_AVAILABLE or shap is None:
            raise RuntimeError("SHAP is not installed or could not be imported.")

        try:
            # TreeExplainer is O(N) where N is tree size, much faster than generic kernel explainer
            self.explainer = shap.TreeExplainer(self.model)
        except Exception as e:
            try:
                # Fallback to model agnostic partition explainer
                self.explainer = shap.Explainer(self.model)
            except Exception as e2:
                raise RuntimeError(f"Failed to initialize SHAP explainer: {str(e2)}")

    @staticmethod
    def _as_shap_array(raw_values) -> np.ndarray:
        """Normalizes raw SHAP values array formats (handles binary list dimensions vs 2D arrays)."""
        if isinstance(raw_values, list):
            # Extract positive class values (index 1) if binary probabilities returned
            raw_values = raw_values[1] if len(raw_values) > 1 else raw_values[0]

        values = np.asarray(raw_values)
        if values.ndim == 1:
            values = values.reshape(1, -1)
        return values

    def _compute_shap_values(self, processed_features) -> np.ndarray:
        """Computes SHAP scores, abstraction layer handling callable vs object shape differences."""
        if self.explainer is None:
            raise RuntimeError("SHAP explainer is not initialized.")

        explainer = cast(Any, self.explainer)
        if hasattr(explainer, "shap_values"):
            return cast(np.ndarray, explainer.shap_values(processed_features))
        elif callable(explainer):
            explanation = cast(Any, explainer(processed_features))
            if hasattr(explanation, "values"):
                return cast(np.ndarray, explanation.values)
            return cast(np.ndarray, explanation)
        else:
            raise AttributeError("The SHAP explainer object does not support computing SHAP values.")

    def _expected_value(self) -> float:
        """Extracts the base model expectation (mean log-odds or mean probability rate)."""
        if self.explainer is None:
            return 0.0
        
        explainer = cast(Any, self.explainer)
        if hasattr(explainer, "expected_value"):
            expected = explainer.expected_value
        else:
            expected = 0.0
            
        if isinstance(expected, (list, tuple, np.ndarray)):
            expected_array = np.asarray(expected).flatten()
            expected = expected_array[1] if expected_array.size > 1 else expected_array[0]
        return float(cast(Any, expected))
    
    def explain_prediction(
        self, 
        raw_features: pd.DataFrame,
        return_base_value: bool = True
    ) -> Dict:
        """
        Generate local SHAP explanations for a single prediction.
        
        Args:
            raw_features: Input features (must match preprocessor format)
            return_base_value: Whether to include base value (model's expected value)
            
        Returns:
            Dictionary with SHAP values, probability, and feature contributions
        """
        # Run preprocessing transform before explaining features
        processed = self.preprocessor.transform(raw_features)
        
        # Calculate raw classification score
        probabilities = self.model.predict_proba(processed)
        probability = float(probabilities[0, 1])  
        
        # Run explainer to calculate contributions
        shap_values = self._as_shap_array(self._compute_shap_values(processed))
        shap_row = shap_values[0]
        
        # Map values back to feature names
        feature_contributions = self._build_feature_contributions(
            shap_row, 
            raw_features.iloc[0].to_dict()
        )
        
        result = {
            "probability": probability,
            "prediction": int(probability >= 0.5),
            "feature_contributions": feature_contributions,
        }
        
        if return_base_value:
            result["base_value"] = self._expected_value()
        
        return result
    
    def _build_feature_contributions(
        self, 
        shap_values: np.ndarray, 
        original_values: Dict
    ) -> List[Dict]:
        """
        Formats contributions into neat UI-consumable metrics.
        Sorts absolute SHAP values descending to put main drivers first.
        """
        contributions = []
        
        for feature_name, shap_value in zip(self.feature_names, shap_values):
            contribution = {
                "feature": feature_name,
                "shap_value": float(shap_value),
                "abs_shap_value": float(abs(shap_value)),
                "direction": "positive" if shap_value > 0 else "negative" if shap_value < 0 else "neutral",
                "original_value": original_values.get(feature_name, "N/A")
            }
            contributions.append(contribution)
        
        # Sorting priority
        contributions.sort(key=lambda x: x["abs_shap_value"], reverse=True)
        
        return contributions
    
    def global_feature_importance(
        self, 
        processed_features: pd.DataFrame,
        top_n: int = 10
    ) -> Dict:
        """
        Calculate global feature importance using mean absolute SHAP values.
        
        Args:
            processed_features: Preprocessed feature data
            top_n: Number of top features to return
            
        Returns:
            Dictionary with feature importance statistics
        """
        shap_array = self._as_shap_array(self._compute_shap_values(processed_features))
        
        # Average absolute impact of each feature across the validation batch
        mean_abs_shap = np.mean(np.abs(shap_array), axis=0)
        
        importance_df = pd.DataFrame({
            "feature": self.feature_names,
            "mean_abs_shap": mean_abs_shap
        })
        
        importance_df = importance_df.sort_values("mean_abs_shap", ascending=False)
        
        result = {
            "global_importance": importance_df.head(top_n).to_dict(orient="records"),
            "total_features": len(self.feature_names),
            "base_value": self._expected_value(),
            "importance_percentiles": {
                "min": float(importance_df["mean_abs_shap"].min()),
                "max": float(importance_df["mean_abs_shap"].max()),
                "mean": float(importance_df["mean_abs_shap"].mean()),
                "median": float(importance_df["mean_abs_shap"].median()),
            },
        }
        
        return result
    
    def feature_interaction_analysis(
        self,
        raw_features: pd.DataFrame,
        feature1: str,
        feature2: str
    ) -> Dict:
        """
        Calculates correlation coefficient between the SHAP values of two features
        to evaluate feature dependency levels.
        """
        if feature1 not in self.feature_names or feature2 not in self.feature_names:
            raise ValueError(f"Feature must be in {self.feature_names}")
        
        idx1 = self.feature_names.index(feature1)
        idx2 = self.feature_names.index(feature2)
        
        processed = self.preprocessor.transform(raw_features)
        shap_array = self._as_shap_array(self._compute_shap_values(processed))
        
        # Calculate Pearson correlation coefficient of columns
        shap_corr = np.corrcoef(shap_array[:, idx1], shap_array[:, idx2])[0, 1]
        
        return {
            "feature1": feature1,
            "feature2": feature2,
            "shap_correlation": float(shap_corr) if not np.isnan(shap_corr) else 0.0,
            "interpretation": self._interpret_correlation(shap_corr)
        }
    
    @staticmethod
    def _interpret_correlation(corr: float) -> str:
        """Interpret correlation coefficient bounds for interactive plotting."""
        if np.isnan(corr):
            return "Insufficient data"
        
        abs_corr = abs(corr)
        if abs_corr > 0.7:
            return "Strong interaction"
        elif abs_corr > 0.4:
            return "Moderate interaction"
        elif abs_corr > 0.2:
            return "Weak interaction"
        else:
            return "No significant interaction"
    
    def explain_prediction_simple(
        self, 
        raw_features: pd.DataFrame,
        top_n: int = 5
    ) -> Dict[str, float]:
        """
        Get simplified SHAP explanation (for backward compatibility).
        
        Args:
            raw_features: Input features
            top_n: Number of top features to include
            
        Returns:
            Dictionary mapping feature names to SHAP values
        """
        explanation = self.explain_prediction(raw_features, return_base_value=False)
        contributions = explanation["feature_contributions"][:top_n]
        return {contrib["feature"]: contrib["shap_value"] for contrib in contributions}
    
    def summary_statistics(
        self,
        processed_features: pd.DataFrame
    ) -> Dict:
        """
        Generate statistical distributions for SHAP metrics.
        """
        shap_array = self._as_shap_array(self._compute_shap_values(processed_features))
        
        stats = {}
        for i, feature_name in enumerate(self.feature_names):
            feature_shap = shap_array[:, i]
            stats[feature_name] = {
                "mean": float(np.mean(feature_shap)),
                "std": float(np.std(feature_shap)),
                "min": float(np.min(feature_shap)),
                "max": float(np.max(feature_shap)),
                "median": float(np.median(feature_shap)),
            }
        
        return stats


def load_explainer_from_artifacts(preprocessor_path: str, model: CatBoostClassifier) -> Optional[SHAPExplainer]:
    """Loads and instantiates a SHAPExplainer wrapper from the serialized preprocessor and model."""
    if not os.path.exists(preprocessor_path):
        return None
    
    try:
        with open(preprocessor_path, "rb") as f:
            preprocessor = pickle.load(f)
        
        feature_names = list(preprocessor.feature_names_) if hasattr(preprocessor, "feature_names_") else []
        
        if not feature_names:
            return None
        
        return SHAPExplainer(model, preprocessor, feature_names)
    except Exception as e:
        print(f"Error loading explainer: {str(e)}")
        return None

