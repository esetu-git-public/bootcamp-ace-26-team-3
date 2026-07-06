"""
Enhanced SHAP Explainability Module

Provides comprehensive explainability for CatBoost churn predictions using SHAP.
Includes local explanations, global feature importance, and visualization support.
"""

import os
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from catboost import CatBoostClassifier
import pickle

# Try to import SHAP, but make it optional
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
    
    Provides:
    - Local feature contributions for individual predictions
    - Global feature importance across dataset
    - SHAP value statistics
    - Feature interaction analysis
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
        self.explainer = None
        self.background_data = None
        self._initialize_explainer()
    
    def _initialize_explainer(self):
        """Initialize SHAP TreeExplainer."""
        if not SHAP_AVAILABLE or shap is None:
            raise RuntimeError("SHAP is not installed or could not be imported.")

        try:
            self.explainer = shap.TreeExplainer(self.model)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize SHAP TreeExplainer: {str(e)}")

    @staticmethod
    def _as_shap_array(raw_values) -> np.ndarray:
        """Normalize SHAP output to a 2D array for the positive class."""
        if isinstance(raw_values, list):
            raw_values = raw_values[1] if len(raw_values) > 1 else raw_values[0]

        values = np.asarray(raw_values)
        if values.ndim == 1:
            values = values.reshape(1, -1)
        return values

    def _expected_value(self) -> float:
        """Return the expected value for the positive class when available."""
        expected = self.explainer.expected_value
        if isinstance(expected, (list, tuple, np.ndarray)):
            expected_array = np.asarray(expected).flatten()
            expected = expected_array[1] if expected_array.size > 1 else expected_array[0]
        return float(expected)
    
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
        # Preprocess features
        processed = self.preprocessor.transform(raw_features)
        
        # Get prediction probability
        probabilities = self.model.predict_proba(processed)
        probability = float(probabilities[0, 1])  # Class 1 probability
        
        # Get SHAP values
        shap_values = self._as_shap_array(self.explainer.shap_values(processed))
        shap_row = shap_values[0]
        
        # Build feature contributions
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
        Build detailed feature contribution objects.
        
        Args:
            shap_values: SHAP values for the instance
            original_values: Original feature values before preprocessing
            
        Returns:
            List of feature contribution dictionaries, sorted by absolute SHAP value
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
        
        # Sort by absolute SHAP value (most important first)
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
        # Calculate SHAP values for all samples
        shap_array = self._as_shap_array(self.explainer.shap_values(processed_features))
        
        # Calculate mean absolute SHAP values
        mean_abs_shap = np.mean(np.abs(shap_array), axis=0)
        
        # Create importance dataframe
        importance_df = pd.DataFrame({
            "feature": self.feature_names,
            "mean_abs_shap": mean_abs_shap
        })
        
        importance_df = importance_df.sort_values("mean_abs_shap", ascending=False)
        
        result = {
            "global_importance": importance_df.head(top_n).to_dict(orient="records"),
            "total_features": len(self.feature_names),
            "base_value": self._expected_value(),
        }
        
        # Add percentile information
        result["importance_percentiles"] = {
            "min": float(importance_df["mean_abs_shap"].min()),
            "max": float(importance_df["mean_abs_shap"].max()),
            "mean": float(importance_df["mean_abs_shap"].mean()),
            "median": float(importance_df["mean_abs_shap"].median()),
        }
        
        return result
    
    def feature_interaction_analysis(
        self,
        raw_features: pd.DataFrame,
        feature1: str,
        feature2: str
    ) -> Dict:
        """
        Analyze interaction between two features using SHAP.
        
        Args:
            raw_features: Raw input features
            feature1: Name of first feature
            feature2: Name of second feature
            
        Returns:
            Dictionary with interaction analysis
        """
        if feature1 not in self.feature_names or feature2 not in self.feature_names:
            raise ValueError(f"Feature must be in {self.feature_names}")
        
        idx1 = self.feature_names.index(feature1)
        idx2 = self.feature_names.index(feature2)
        
        processed = self.preprocessor.transform(raw_features)
        shap_array = self._as_shap_array(self.explainer.shap_values(processed))
        
        # Calculate correlation between SHAP values of two features
        shap_corr = np.corrcoef(shap_array[:, idx1], shap_array[:, idx2])[0, 1]
        
        return {
            "feature1": feature1,
            "feature2": feature2,
            "shap_correlation": float(shap_corr) if not np.isnan(shap_corr) else 0.0,
            "interpretation": self._interpret_correlation(shap_corr)
        }
    
    @staticmethod
    def _interpret_correlation(corr: float) -> str:
        """Interpret correlation coefficient."""
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
        
        # Get top N features by absolute value
        contributions = explanation["feature_contributions"][:top_n]
        
        return {contrib["feature"]: contrib["shap_value"] for contrib in contributions}
    
    def summary_statistics(
        self,
        processed_features: pd.DataFrame
    ) -> Dict:
        """
        Generate summary statistics for SHAP values across dataset.
        
        Args:
            processed_features: Preprocessed feature data
            
        Returns:
            Dictionary with summary statistics
        """
        shap_array = self._as_shap_array(self.explainer.shap_values(processed_features))
        
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
    """
    Load and initialize SHAPExplainer from saved artifacts.
    
    Args:
        preprocessor_path: Path to saved preprocessor
        model: Trained CatBoost model
        
    Returns:
        Initialized SHAPExplainer or None if artifacts not found
    """
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
