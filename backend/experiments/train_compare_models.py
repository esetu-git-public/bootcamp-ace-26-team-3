import os
import sys
import json
import pickle
import argparse
import pandas as pd
import numpy as np

# Configure matplotlib to run without a GUI
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
    roc_curve,
)

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier

try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except Exception:
    HAS_XGBOOST = False

try:
    from catboost import CatBoostClassifier
    HAS_CATBOOST = True
except Exception:
    HAS_CATBOOST = False

# Add backend directory to path to import preprocessor
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.preprocessing import SubscriptionPreprocessor

RANDOM_STATE = 42
MODEL_VERSION = "v1.3.0-model-comparison"


def check_data_leakage(df: pd.DataFrame, target_col: str):
    """Scan columns for potential data leakage or identifier columns."""
    flagged_columns = []
    for col in df.columns:
        if col == target_col:
            continue
        col_lower = col.lower()
        if any(keyword in col_lower for keyword in ["cancel", "churn", "will_cancel", "target", "prediction"]):
            flagged_columns.append(col)
        elif any(keyword in col_lower for keyword in ["customer_id", "cust_id", "uuid"]):
            flagged_columns.append(col)
            
    # Also check if any numerical column has suspiciously high correlation (e.g. > 0.95)
    for col in df.select_dtypes(include=[np.number]).columns:
        if col == target_col:
            continue
        correlation = abs(df[col].corr(df[target_col]))
        if correlation > 0.95 and col not in flagged_columns:
            flagged_columns.append(col)
            print(f"Warning: Column '{col}' flagged due to very high correlation ({correlation:.4f}) with target.")
            
    return flagged_columns


def main():
    parser = argparse.ArgumentParser(description="Train and compare ML models with leakage & overfitting checks")
    parser.add_argument(
        "--data-path",
        type=str,
        default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Subscription Fatigue.csv")),
        help="Path to CSV dataset.",
    )
    parser.add_argument(
        "--target-col",
        type=str,
        default="Will_Cancel_Next_3_Months",
        help="Target column name.",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Test split fraction.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "reports")),
        help="Where to write results.",
    )
    parser.add_argument(
        "--artifacts-dir",
        type=str,
        default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app", "core", "model_artifacts")),
        help="Where to save model artifacts.",
    )

    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(args.artifacts_dir, exist_ok=True)

    if not os.path.exists(args.data_path):
        # Try finding in root directly
        fallback_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Subscription Fatigue.csv"))
        if os.path.exists(fallback_path):
            args.data_path = fallback_path
        else:
            raise FileNotFoundError(f"Dataset path {args.data_path} not found.")

    print(f"Loading data from: {args.data_path}")
    df = pd.read_csv(args.data_path)
    
    if args.target_col not in df.columns:
        raise ValueError(f"Target column '{args.target_col}' not found. Columns: {list(df.columns)}")

    # Detect data leakage
    leakage_cols = check_data_leakage(df, args.target_col)
    print(f"Data leakage/identifier columns identified and dropped: {leakage_cols}")
    
    y = df[args.target_col].astype(int)
    X_raw = df.drop(columns=[args.target_col] + leakage_cols, errors="ignore")

    X_train_raw, X_test_raw, y_train, y_test = train_test_split(
        X_raw, y, test_size=args.test_size, random_state=RANDOM_STATE, stratify=y
    )

    # Fit preprocessor
    preprocessor = SubscriptionPreprocessor()
    X_train = preprocessor.fit_transform(X_train_raw)
    X_test = preprocessor.transform(X_test_raw)

    # Configure models
    models = {
        "logreg": LogisticRegression(max_iter=1000, class_weight="balanced", random_state=RANDOM_STATE),
        "rf": RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=RANDOM_STATE, n_jobs=-1),
        "gb": GradientBoostingClassifier(n_estimators=100, learning_rate=0.05, max_depth=4, random_state=RANDOM_STATE),
    }

    if HAS_XGBOOST:
        models["xgboost"] = XGBClassifier(
            n_estimators=100,
            learning_rate=0.05,
            max_depth=5,
            random_state=RANDOM_STATE,
            n_jobs=-1,
            eval_metric="logloss",
        )
    if HAS_CATBOOST:
        models["catboost"] = CatBoostClassifier(
            iterations=200,
            learning_rate=0.05,
            depth=6,
            random_seed=RANDOM_STATE,
            verbose=False,
        )

    results = {}
    cv_folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)

    for name, estimator in models.items():
        print(f"Training {name}...")
        estimator.fit(X_train, y_train)

        # Predictions
        y_train_pred = estimator.predict(X_train)
        y_test_pred = estimator.predict(X_test)
        y_test_prob = estimator.predict_proba(X_test)[:, 1]

        # Calculate metrics
        train_acc = float(accuracy_score(y_train, y_train_pred))
        test_acc = float(accuracy_score(y_test, y_test_pred))
        accuracy_gap = float(train_acc - test_acc)
        precision = float(precision_score(y_test, y_test_pred, zero_division=0))
        recall = float(recall_score(y_test, y_test_pred, zero_division=0))
        f1 = float(f1_score(y_test, y_test_pred, zero_division=0))
        roc_auc = float(roc_auc_score(y_test, y_test_prob))
        cm = confusion_matrix(y_test, y_test_pred).tolist()

        # Cross Validation on train split
        print(f"Evaluating Cross-Validation for {name}...")
        cv_roc_auc = float(np.mean(cross_val_score(estimator, X_train, y_train, cv=cv_folds, scoring="roc_auc", n_jobs=-1)))
        cv_f1 = float(np.mean(cross_val_score(estimator, X_train, y_train, cv=cv_folds, scoring="f1", n_jobs=-1)))

        results[name] = {
            "train_accuracy": train_acc,
            "test_accuracy": test_acc,
            "accuracy_gap": accuracy_gap,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "roc_auc": roc_auc,
            "confusion_matrix": cm,
            "cv_roc_auc": cv_roc_auc,
            "cv_f1": cv_f1,
            "is_overfitted": "Yes" if (accuracy_gap > 0.05 or roc_auc >= 0.999) else "No",
        }

    # Print summary to console
    print("\nModel comparison results:")
    for name, metrics in results.items():
        print(
            f"Model: {name:15} | Train Acc: {metrics['train_accuracy']:.4f} | "
            f"Test Acc: {metrics['test_accuracy']:.4f} | Gap: {metrics['accuracy_gap']:.4f} | "
            f"ROC-AUC: {metrics['roc_auc']:.4f} | F1: {metrics['f1_score']:.4f} | Overfit: {metrics['is_overfitted']}"
        )

    # Best model selection logic
    best_model_name = None
    best_score = -1.0
    best_f1 = -1.0
    best_recall = -1.0

    overfit_report = {}

    for name, m in results.items():
        gap = m["accuracy_gap"]
        is_leak = m["roc_auc"] >= 0.999
        overfit_report[name] = {
            "accuracy_gap": gap,
            "is_overfitted": "Yes" if gap > 0.05 else "No",
            "potential_data_leakage": "Yes" if is_leak else "No",
        }

        # Select model only if not overfitted and no leakage
        if gap <= 0.05 and not is_leak:
            if m["roc_auc"] > best_score:
                best_score = m["roc_auc"]
                best_f1 = m["f1_score"]
                best_recall = m["recall"]
                best_model_name = name
            elif abs(m["roc_auc"] - best_score) < 1e-5:
                if m["f1_score"] > best_f1:
                    best_f1 = m["f1_score"]
                    best_recall = m["recall"]
                    best_model_name = name
                elif abs(m["f1_score"] - best_f1) < 1e-5:
                    if m["recall"] > best_recall:
                        best_recall = m["recall"]
                        best_model_name = name

    if best_model_name is None:
        print("\n[WARNING] All models exceeded 5% overfitting gap or flagged with leakage. Selecting best fallback model.")
        best_model_name = max(results.keys(), key=lambda k: (results[k]["roc_auc"], results[k]["f1_score"]))

    best_metrics = results[best_model_name]
    print(f"\nSelected Best Model: {best_model_name} (ROC-AUC={best_metrics['roc_auc']:.4f}, F1={best_metrics['f1_score']:.4f})")

    # Save Comparison CSV and JSON reports
    results_df = pd.DataFrame(results).T
    results_df.to_csv(os.path.join(args.output_dir, "model_comparison_results.csv"), index=True)
    with open(os.path.join(args.output_dir, "model_comparison_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    # Save Best Model metadata
    with open(os.path.join(args.output_dir, "best_model.txt"), "w", encoding="utf-8") as f:
        f.write(f"Best Model Selected: {best_model_name}\n")
        f.write(f"Model Version: {MODEL_VERSION}\n")
        for k, v in best_metrics.items():
            f.write(f"{k}: {v}\n")

    # Save Overfitting Report
    with open(os.path.join(args.output_dir, "model_overfitting_report.json"), "w", encoding="utf-8") as f:
        json.dump(overfit_report, f, indent=2)

    # Save summary markdown report
    summary_md = f"""# Model Training and Comparison Summary

## Best Model Selected: {best_model_name}
**Version**: {MODEL_VERSION}
**Selection Criteria**: Highest ROC-AUC first, then F1-score, then recall (rejecting models with > 5% train/test accuracy gap).

### Metrics Summary Table

| Model Name | Train Accuracy | Test Accuracy | Train-Test Gap | Test ROC-AUC | Test F1-Score | Overfitted? |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
"""
    for name, m in results.items():
        summary_md += f"| {name} | {m['train_accuracy']:.4f} | {m['test_accuracy']:.4f} | {m['accuracy_gap']:.4f} | {m['roc_auc']:.4f} | {m['f1_score']:.4f} | {m['is_overfitted']} |\n"

    with open(os.path.join(args.output_dir, "model_comparison_summary.md"), "w", encoding="utf-8") as f:
        f.write(summary_md)

    # Plot & Save Visualizations
    # 1. Model comparison metrics chart
    plt.figure(figsize=(10, 6))
    metrics_to_plot = ["test_accuracy", "roc_auc", "f1_score"]
    plot_df = results_df[metrics_to_plot].reset_index().rename(columns={"index": "Model"})
    melt_df = pd.melt(plot_df, id_vars=["Model"], value_vars=metrics_to_plot, var_name="Metric", value_name="Score")
    sns.barplot(data=melt_df, x="Model", y="Score", hue="Metric", palette="viridis")
    plt.title("Model Performance Comparison")
    plt.ylim(0, 1.05)
    plt.tight_layout()
    plt.savefig(os.path.join(args.output_dir, "model_comparison_metrics.png"))
    plt.close()

    # 2. Confusion matrix of the best model
    best_cm = np.array(best_metrics["confusion_matrix"])
    plt.figure(figsize=(6, 5))
    sns.heatmap(best_cm, annot=True, fmt="d", cmap="Blues", xticklabels=["Stable", "Churn"], yticklabels=["Stable", "Churn"])
    plt.title(f"Confusion Matrix - {best_model_name}")
    plt.ylabel("Actual")
    plt.xlabel("Predicted")
    plt.tight_layout()
    plt.savefig(os.path.join(args.output_dir, "confusion_matrix_best_model.png"))
    plt.close()

    # 3. ROC Curve comparison
    plt.figure(figsize=(10, 8))
    for name, clf in models.items():
        probs = clf.predict_proba(X_test)[:, 1]
        fpr, tpr, _ = roc_curve(y_test, probs)
        plt.plot(fpr, tpr, label=f"{name} (AUC={results[name]['roc_auc']:.3f})")
    plt.plot([0, 1], [0, 1], "k--", label="Random Guess")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC Curve Comparison")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(args.output_dir, "roc_curve_comparison.png"))
    plt.close()

    # 4. Feature importance chart of the best model
    plt.figure(figsize=(10, 6))
    best_clf = models[best_model_name]
    if hasattr(best_clf, "feature_importances_"):
        importances = best_clf.feature_importances_
    elif hasattr(best_clf, "coef_"):
        importances = np.abs(best_clf.coef_[0])
    else:
        importances = np.zeros(X_train.shape[1])

    feat_importances = pd.Series(importances, index=X_train.columns).sort_values(ascending=True)
    feat_importances.tail(15).plot(kind="barh", color="teal")
    plt.title(f"Feature Importance - {best_model_name}")
    plt.tight_layout()
    plt.savefig(os.path.join(args.output_dir, "feature_importance_best_model.png"))
    plt.close()

    print("All charts and summaries saved successfully to reports/.")

    # Save fitted preprocessor
    preprocessor_out_path = os.path.join(args.artifacts_dir, "preprocessor.pkl")
    preprocessor_version_path = os.path.join(args.artifacts_dir, f"preprocessor_{MODEL_VERSION}.pkl")
    for path in [preprocessor_out_path, preprocessor_version_path]:
        with open(path, "wb") as f:
            pickle.dump(preprocessor, f)
    print("Fitted preprocessor saved successfully.")

    # Save selected best model to model_artifacts
    if best_model_name == "catboost":
        model_out_path = os.path.join(args.artifacts_dir, "catboost_model.cbm")
        model_version_path = os.path.join(args.artifacts_dir, f"catboost_model_{MODEL_VERSION}.cbm")
        best_clf.save_model(model_out_path)
        best_clf.save_model(model_version_path)
        print("CatBoost model artifacts saved successfully.")
    else:
        # Save as sklearn pkl
        model_out_path = os.path.join(args.artifacts_dir, "sklearn_model.pkl")
        model_version_path = os.path.join(args.artifacts_dir, f"sklearn_model_{MODEL_VERSION}.pkl")
        for path in [model_out_path, model_version_path]:
            with open(path, "wb") as f:
                pickle.dump(best_clf, f)
        print(f"Sklearn pipeline model ({best_model_name}) saved successfully.")

    # Update app model metrics JSON file
    metrics_json_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app", "models", "model_metrics.json"))
    
    # Format feature importance for json
    feat_imp_dict = {}
    for feat, imp in zip(X_train.columns, importances.tolist()):
        feat_imp_dict[feat] = float(imp)

    # confusion matrix map tp/fp/tn/fn
    tn, fp, fn, tp = best_cm.ravel()
    cm_dict = {"tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn)}

    app_metrics = {
        "model_name": best_model_name,
        "model_version": MODEL_VERSION,
        "accuracy": float(best_metrics["test_accuracy"]),
        "precision": float(best_metrics["precision"]),
        "recall": float(best_metrics["recall"]),
        "f1_score": float(best_metrics["f1_score"]),
        "roc_auc": float(best_metrics["roc_auc"]),
        "confusion_matrix": cm_dict,
        "feature_importance": feat_imp_dict,
        "train_accuracy": float(best_metrics["train_accuracy"]),
        "test_accuracy": float(best_metrics["test_accuracy"]),
        "overfitting_gap": float(best_metrics["accuracy_gap"]),
        "cv_roc_auc": float(best_metrics["cv_roc_auc"]),
        "cv_f1_score": float(best_metrics["cv_f1"]),
        "evaluated_at": pd.Timestamp.now().isoformat(),
    }

    with open(metrics_json_path, "w", encoding="utf-8") as f:
        json.dump(app_metrics, f, indent=2)
    print("Updated app model metrics JSON successfully.")


if __name__ == "__main__":
    main()
