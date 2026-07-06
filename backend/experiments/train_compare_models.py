import os
import json
import argparse
from dataclasses import dataclass, asdict

import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    roc_auc_score,
    confusion_matrix,
    classification_report,
)

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier

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


RANDOM_STATE = 42


@dataclass
class ModelMetrics:
    model_name: str
    roc_auc: float | None
    accuracy: float
    precision: float
    recall: float
    f1: float
    confusion_matrix: list


def _detect_feature_types(df: pd.DataFrame, target_col: str):
    feature_cols = [c for c in df.columns if c != target_col]
    numeric_cols = []
    categorical_cols = []
    for c in feature_cols:
        if pd.api.types.is_numeric_dtype(df[c]):
            numeric_cols.append(c)
        else:
            categorical_cols.append(c)
    return numeric_cols, categorical_cols


def build_preprocessor(df: pd.DataFrame, target_col: str):
    numeric_cols, categorical_cols = _detect_feature_types(df, target_col)

    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
        ]
    )

    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_cols),
            ("cat", categorical_transformer, categorical_cols),
        ],
        remainder="drop",
    )

    return preprocessor


def make_models():
    models = []

    models.append(
        (
            "logreg",
            LogisticRegression(
                max_iter=2000,
                class_weight="balanced",
                solver="lbfgs",
            ),
        )
    )

    models.append(
        (
            "rf",
            RandomForestClassifier(
                n_estimators=500,
                random_state=RANDOM_STATE,
                class_weight="balanced",
                n_jobs=-1,
            ),
        )
    )

    if HAS_XGBOOST:
        models.append(
            (
                "xgboost",
                XGBClassifier(
                    n_estimators=500,
                    learning_rate=0.05,
                    max_depth=4,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    reg_lambda=1.0,
                    random_state=RANDOM_STATE,
                    n_jobs=-1,
                    objective="binary:logistic",
                    eval_metric="auc",
                ),
            )
        )

    if HAS_CATBOOST:
        # CatBoost can handle categorical features directly, but since we are
        # using a one-hot preprocessor for uniformity, it still works.
        # We keep it in the comparison pipeline for simplicity.
        models.append(
            (
                "catboost",
                CatBoostClassifier(
                    iterations=2000,
                    learning_rate=0.05,
                    depth=6,
                    loss_function="Logloss",
                    random_seed=RANDOM_STATE,
                    verbose=False,
                ),
            )
        )

    return models


def evaluate_binary_classifier(model, model_name: str, X_test, y_test):
    # y_prob for roc_auc if available
    roc_auc = None
    if hasattr(model, "predict_proba"):
        y_prob = model.predict_proba(X_test)[:, 1]
        roc_auc = float(roc_auc_score(y_test, y_prob))
    elif hasattr(model, "decision_function"):
        scores = model.decision_function(X_test)
        roc_auc = float(roc_auc_score(y_test, scores))

    y_pred = model.predict(X_test)

    acc = float(accuracy_score(y_test, y_pred))

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average="binary", zero_division=0
    )

    cm = confusion_matrix(y_test, y_pred).tolist()

    return ModelMetrics(
        model_name=model_name,
        roc_auc=roc_auc,
        accuracy=acc,
        precision=float(precision),
        recall=float(recall),
        f1=float(f1),
        confusion_matrix=cm,
    )


def main():
    parser = argparse.ArgumentParser(description="Train and compare ML models for churn prediction")
    parser.add_argument(
        "--data-path",
        type=str,
        default=os.path.join("dataset", "dataset.csv"),
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
        default=os.path.join("reports"),
        help="Where to write results.",
    )

    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    df = pd.read_csv(args.data_path)
    if args.target_col not in df.columns:
        raise ValueError(
            f"Target column '{args.target_col}' not found. Available columns: {list(df.columns)}"
        )

    # Basic cleanup: enforce target as int 0/1
    y = df[args.target_col].astype(int)
    X = df.drop(columns=[args.target_col])

    preprocessor = build_preprocessor(df, args.target_col)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=RANDOM_STATE, stratify=y
    )

    models = make_models()
    results: list[ModelMetrics] = []

    for model_name, estimator in models:
        # Build pipeline: preprocess -> model
        if model_name in {"catboost"}:
            # CatBoostClassifier can accept dense numeric matrices; one-hot pipeline already does that.
            clf = estimator
        else:
            clf = estimator

        pipeline = Pipeline(
            steps=[
                ("preprocess", preprocessor),
                ("model", clf),
            ]
        )

        pipeline.fit(X_train, y_train)
        metrics = evaluate_binary_classifier(pipeline, model_name, X_test, y_test)
        results.append(metrics)

        # Also write a small per-model report
        report = classification_report(y_test, pipeline.predict(X_test), zero_division=0)
        with open(os.path.join(args.output_dir, f"{model_name}_classification_report.txt"), "w", encoding="utf-8") as f:
            f.write(report)

    # Save results as CSV/JSON
    results_dicts = [asdict(r) for r in results]
    results_df = pd.DataFrame(results_dicts)

    results_df.to_csv(os.path.join(args.output_dir, "model_comparison_results.csv"), index=False)
    with open(os.path.join(args.output_dir, "model_comparison_results.json"), "w", encoding="utf-8") as f:
        json.dump(results_dicts, f, indent=2)

    # Print a short summary to terminal
    print("\nModel comparison:")
    print(results_df[["model_name", "roc_auc", "accuracy", "precision", "recall", "f1"]].sort_values(
        by=["roc_auc", "f1"], ascending=False
    ).to_string(index=False))

    # Best model selection
    scored = [r for r in results if r.roc_auc is not None]
    if scored:
        best = max(scored, key=lambda r: (r.roc_auc, r.f1))
    else:
        best = max(results, key=lambda r: (r.f1, r.accuracy))

    with open(os.path.join(args.output_dir, "best_model.txt"), "w", encoding="utf-8") as f:
        f.write(
            f"Best model: {best.model_name}\n"
            f"ROC-AUC: {best.roc_auc}\n"
            f"Accuracy: {best.accuracy}\n"
            f"Precision: {best.precision}\n"
            f"Recall: {best.recall}\n"
            f"F1: {best.f1}\n"
        )

    print(f"\nBest model: {best.model_name} (ROC-AUC={best.roc_auc}, F1={best.f1})")


if __name__ == "__main__":
    main()

