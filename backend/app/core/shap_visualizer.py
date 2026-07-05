"""
SHAP Visualization Utilities

Provides utilities to generate SHAP visualizations and explanations
in formats suitable for web display (JSON, images).
"""

import os
import json
import base64
import io
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
import shap


class SHAPVisualizer:
    """Generate SHAP visualizations for web display."""
    
    @staticmethod
    def create_force_plot_data(
        explainer_base_value: float,
        shap_values: np.ndarray,
        features: pd.DataFrame,
        feature_names: List[str]
    ) -> Dict:
        """
        Create data for a force plot visualization (JSON format).
        
        Args:
            explainer_base_value: Base value from SHAP explainer
            shap_values: SHAP values for the instance
            features: Original feature values
            feature_names: Names of features
            
        Returns:
            Dictionary with force plot data
        """
        # Separate positive and negative contributions
        positive_features = []
        negative_features = []
        
        for feature_name, shap_val, feature_val in zip(feature_names, shap_values, features.iloc[0]):
            contribution = {
                "feature": feature_name,
                "shap_value": float(shap_val),
                "feature_value": str(feature_val),
            }
            
            if shap_val > 0:
                positive_features.append(contribution)
            elif shap_val < 0:
                negative_features.append(contribution)
        
        # Sort by absolute value
        positive_features.sort(key=lambda x: x["shap_value"], reverse=True)
        negative_features.sort(key=lambda x: x["shap_value"])
        
        return {
            "base_value": float(explainer_base_value),
            "prediction_value": float(explainer_base_value + np.sum(shap_values)),
            "positive_features": positive_features,
            "negative_features": negative_features,
        }
    
    @staticmethod
    def create_decision_plot_data(
        explainer_base_value: float,
        shap_values: np.ndarray,
        feature_names: List[str],
        features: Optional[pd.DataFrame] = None
    ) -> Dict:
        """
        Create data for a decision plot (showing cumulative SHAP contribution).
        
        Args:
            explainer_base_value: Base value
            shap_values: SHAP values
            feature_names: Feature names
            features: Original features (optional)
            
        Returns:
            Dictionary with decision plot data
        """
        # Calculate cumulative contributions
        cumulative_values = [float(explainer_base_value)]
        contributions = []
        
        for i, (feature_name, shap_val) in enumerate(zip(feature_names, shap_values)):
            cumulative_values.append(cumulative_values[-1] + float(shap_val))
            
            contribution = {
                "step": i,
                "feature": feature_name,
                "shap_value": float(shap_val),
                "cumulative_value": cumulative_values[-1],
                "direction": "up" if shap_val > 0 else "down" if shap_val < 0 else "neutral"
            }
            
            if features is not None:
                contribution["feature_value"] = str(features.iloc[0, i])
            
            contributions.append(contribution)
        
        return {
            "base_value": float(explainer_base_value),
            "final_value": cumulative_values[-1],
            "decision_path": contributions,
        }
    
    @staticmethod
    def create_waterfall_plot_data(
        explainer_base_value: float,
        shap_values: np.ndarray,
        feature_names: List[str],
        features: Optional[pd.DataFrame] = None,
        top_n: int = 10
    ) -> Dict:
        """
        Create data for waterfall plot (ordered by impact).
        
        Args:
            explainer_base_value: Base value
            shap_values: SHAP values
            feature_names: Feature names
            features: Original features (optional)
            top_n: Top features to show (by absolute SHAP value)
            
        Returns:
            Dictionary with waterfall plot data
        """
        # Create feature contributions
        contributions_list = []
        for feature_name, shap_val in zip(feature_names, shap_values):
            contributions_list.append({
                "feature": feature_name,
                "shap_value": float(shap_val),
                "abs_shap_value": abs(float(shap_val))
            })
        
        # Sort by absolute value and take top N
        contributions_list.sort(key=lambda x: x["abs_shap_value"], reverse=True)
        contributions_list = contributions_list[:top_n]
        
        # Calculate cumulative for waterfall
        cumulative = float(explainer_base_value)
        waterfall_steps = [
            {
                "step": "Base Value",
                "value": float(explainer_base_value),
                "cumulative": cumulative,
                "type": "base"
            }
        ]
        
        for i, contrib in enumerate(contributions_list):
            cumulative += contrib["shap_value"]
            waterfall_steps.append({
                "step": contrib["feature"],
                "value": contrib["shap_value"],
                "cumulative": cumulative,
                "type": "positive" if contrib["shap_value"] > 0 else "negative"
            })
        
        return {
            "waterfall_steps": waterfall_steps,
            "final_value": cumulative,
        }
    
    @staticmethod
    def create_feature_importance_chart(
        feature_importance: Dict
    ) -> Dict:
        """
        Create data for feature importance bar chart.
        
        Args:
            feature_importance: Output from global_feature_importance
            
        Returns:
            Dictionary with chart data
        """
        if not feature_importance.get("global_importance"):
            return {"features": [], "importance_scores": []}
        
        features = []
        scores = []
        
        for item in feature_importance["global_importance"]:
            features.append(item["feature"])
            scores.append(item["mean_abs_shap"])
        
        return {
            "features": features,
            "importance_scores": scores,
            "base_value": feature_importance.get("base_value", 0.0),
            "statistics": feature_importance.get("importance_percentiles", {})
        }
    
    @staticmethod
    def generate_matplotlib_plot(
        plot_type: str,
        explainer_base_value: float,
        shap_values: np.ndarray,
        feature_names: List[str],
        features: Optional[pd.DataFrame] = None,
        figsize: Tuple[int, int] = (10, 6),
        dpi: int = 100
    ) -> str:
        """
        Generate a matplotlib plot and return as base64-encoded image.
        
        Args:
            plot_type: Type of plot ('force', 'bar', 'decision')
            explainer_base_value: Base value
            shap_values: SHAP values
            feature_names: Feature names
            features: Original features
            figsize: Figure size
            dpi: DPI for image
            
        Returns:
            Base64-encoded image string
        """
        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
        
        try:
            if plot_type == "bar":
                # Bar plot of top features
                top_n = min(10, len(feature_names))
                indices = np.argsort(np.abs(shap_values))[-top_n:][::-1]
                
                sorted_names = [feature_names[i] for i in indices]
                sorted_values = shap_values[indices]
                colors = ['red' if v < 0 else 'green' for v in sorted_values]
                
                ax.barh(sorted_names, sorted_values, color=colors, alpha=0.7)
                ax.set_xlabel('SHAP Value')
                ax.set_title('Top Feature Contributions')
                ax.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
            
            elif plot_type == "decision":
                # Decision plot showing cumulative contribution
                cumulative = [explainer_base_value]
                for val in shap_values:
                    cumulative.append(cumulative[-1] + val)
                
                ax.plot(cumulative, marker='o', linewidth=2, markersize=4)
                ax.set_xlabel('Features')
                ax.set_ylabel('Cumulative SHAP Value')
                ax.set_title('Decision Path')
                ax.grid(True, alpha=0.3)
            
            # Convert figure to base64
            buffer = io.BytesIO()
            fig.savefig(buffer, format='png', bbox_inches='tight', dpi=dpi)
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
            
            plt.close(fig)
            
            return f"data:image/png;base64,{image_base64}"
        
        except Exception as e:
            plt.close(fig)
            raise RuntimeError(f"Failed to generate {plot_type} plot: {str(e)}")
    
    @staticmethod
    def create_explanation_summary(
        probability: float,
        shap_values: np.ndarray,
        feature_names: List[str],
        top_n: int = 3
    ) -> str:
        """
        Create a human-readable explanation summary.
        
        Args:
            probability: Prediction probability
            shap_values: SHAP values
            feature_names: Feature names
            top_n: Number of top features to mention
            
        Returns:
            Human-readable explanation string
        """
        # Get top contributing features
        top_indices = np.argsort(np.abs(shap_values))[-top_n:][::-1]
        
        summary = f"This customer has a {probability*100:.1f}% churn probability. "
        
        top_features = []
        for idx in top_indices:
            feature = feature_names[idx]
            value = shap_values[idx]
            direction = "increasing" if value > 0 else "decreasing"
            top_features.append(f"{feature} ({direction} churn risk)")
        
        summary += f"The top factors are: {', '.join(top_features)}."
        
        return summary


class InteractiveExplainationGenerator:
    """Generate interactive explanations combining multiple visualization types."""
    
    @staticmethod
    def generate_full_explanation(
        probability: float,
        shap_values: np.ndarray,
        feature_names: List[str],
        features: pd.DataFrame,
        explainer_base_value: float,
        global_importance: Optional[Dict] = None
    ) -> Dict:
        """
        Generate complete interactive explanation package.
        
        Args:
            probability: Prediction probability
            shap_values: SHAP values
            feature_names: Feature names
            features: Original features
            explainer_base_value: Base value
            global_importance: Global feature importance (optional)
            
        Returns:
            Dictionary with multiple explanation formats
        """
        visualizer = SHAPVisualizer()
        
        return {
            "prediction": {
                "probability": float(probability),
                "class": "churn" if probability >= 0.5 else "no_churn",
                "confidence": float(max(probability, 1 - probability))
            },
            "force_plot": visualizer.create_force_plot_data(
                explainer_base_value, shap_values, features, feature_names
            ),
            "decision_plot": visualizer.create_decision_plot_data(
                explainer_base_value, shap_values, feature_names, features
            ),
            "waterfall_plot": visualizer.create_waterfall_plot_data(
                explainer_base_value, shap_values, feature_names, features
            ),
            "feature_importance": global_importance or {},
            "summary": visualizer.create_explanation_summary(probability, shap_values, feature_names),
        }
