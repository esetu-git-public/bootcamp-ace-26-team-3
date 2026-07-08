import argparse
import os
import sys
import json
import pickle
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

# Add backend directory to sys.path to enable imports of app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def build_preprocessor(numeric_cols, categorical_cols):
    """Builds a preprocessing pipeline for the model."""
    numeric_transformer = Pipeline(steps=[
        ('scaler', StandardScaler())
    ])
    categorical_transformer = Pipeline(steps=[
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
    ])
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, numeric_cols),
            ('cat', categorical_transformer, categorical_cols)
        ],
        remainder='passthrough'
    )
    return preprocessor

def main(args):
    """Main function to run the model training and evaluation."""
    print("Loading data from:", args.data_path)
    df = pd.read_csv(args.data_path)

    # 2. Data Preprocessing & Cleaning
    df['Avg_Usage_Hours_Per_Week'] = df['Avg_Usage_Hours_Per_Week'].clip(lower=0.0)
    df['Monthly_Total_Spend'] = df['Monthly_Total_Spend'].clip(lower=0.0)

    # Target and features splits
    X = df.drop(columns=['Customer_ID', 'Will_Cancel_Next_3_Months'])
    y = df['Will_Cancel_Next_3_Months']

    # Define feature types
    numeric_features = X.select_dtypes(include=np.number).columns.tolist()
    categorical_features = X.select_dtypes(exclude=np.number).columns.tolist()

    # Ensure categorical features are treated as strings for CatBoost
    for col in categorical_features:
        X[col] = X[col].astype(str)

    # 3. Train-Test Split (80:20 stratified)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"Training set size: {X_train.shape[0]}, Test set size: {X_test.shape[0]}")

    # Build preprocessor
    preprocessor = build_preprocessor(numeric_features, categorical_features)

    # 4. Train CatBoostClassifier
    model = CatBoostClassifier(
        iterations=500,
        learning_rate=0.05,
        depth=6,
        eval_metric='AUC',
        random_seed=42,
        verbose=100,
        cat_features=categorical_features
    )

    # Create a full pipeline
    pipeline = Pipeline(steps=[('preprocessor', preprocessor),
                               ('classifier', model)])

    # Fit the model (CatBoost needs cat_features passed during fit)
    pipeline.fit(X_train, y_train)

    # 5. Evaluate Model
    y_pred = pipeline.predict(X_test)
    y_pred_proba = pipeline.predict_proba(X_test)[:, 1]

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_pred_proba)

    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()

    # Feature importance
    feature_names = numeric_features + \
                    pipeline.named_steps['preprocessor'].named_transformers_['cat'].named_steps['onehot'].get_feature_names_out(categorical_features).tolist()
    importances = pipeline.named_steps['classifier'].get_feature_importance()
    feature_importance_dict = dict(zip(feature_names, importances.tolist()))

    metrics = {
        "model_version": args.model_version,
        "accuracy": round(float(accuracy), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1_score": round(float(f1), 4),
        "roc_auc": round(float(roc_auc), 4),
        "confusion_matrix": {
            "tp": int(tp),
            "fp": int(fp),
            "tn": int(tn),
            "fn": int(fn)
        },
        "feature_importance": feature_importance_dict
    }

    print("\nModel Evaluation Metrics:")
    print(json.dumps(metrics, indent=2))

    # Ensure models directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    # Define paths for artifacts
    model_save_path = os.path.join(args.output_dir, f"catboost_model_{args.model_version}.cbm")
    preprocessor_save_path = os.path.join(args.output_dir, f"preprocessor_{args.model_version}.pkl")
    metrics_save_path = os.path.join(args.output_dir, f"model_metrics_{args.model_version}.json")

    # Save CatBoost model from pipeline
    pipeline.named_steps['classifier'].save_model(model_save_path)
    print(f"Model saved to: {model_save_path}")

    # Save preprocessor
    with open(preprocessor_save_path, "wb") as f:
        pickle.dump(preprocessor, f)
    print(f"Preprocessor saved to: {preprocessor_save_path}")

    # Save metrics JSON
    with open(metrics_save_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Metrics saved to: {metrics_save_path}")

    # Save metrics to database if enabled
    if args.save_to_db:
        print("Saving model evaluation metrics to database...")
        db = None
        try:
            from app.database import SessionLocal
            from app.models import ModelMetric

            db = SessionLocal()
            db_metric = ModelMetric(
                model_version=metrics["model_version"],
                accuracy=metrics["accuracy"],
                precision=metrics["precision"],
                recall=metrics["recall"],
                f1_score=metrics["f1_score"],
                roc_auc=metrics["roc_auc"],
                confusion_matrix=metrics["confusion_matrix"],
                feature_importance=metrics["feature_importance"]
            )
            db.add(db_metric)
            db.commit()
            print("Successfully saved model evaluation metrics to database.")
        except Exception as e:
            print(f"Failed to save metrics to database: {e}")
        finally:
            if db is not None:
                db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train a CatBoost churn prediction model.")
    
    # Get base directory of the script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    parser.add_argument(
        "--data-path",
        type=str,
        default=os.path.join(base_dir, "..", "..", "Subscription Fatigue.csv"),
        help="Path to the training data CSV file."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=os.path.join(base_dir, "core", "model_artifacts"),
        help="Directory to save model artifacts."
    )
    parser.add_argument(
        "--model-version",
        type=str,
        default="v1.3.0",
        help="Version string for the trained model."
    )
    parser.add_argument(
        "--save-to-db",
        action="store_true",
        help="If set, saves the evaluation metrics to the database."
    )
    
    parsed_args = parser.parse_args()
    main(parsed_args)
