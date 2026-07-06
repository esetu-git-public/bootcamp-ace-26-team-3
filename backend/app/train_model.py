import os
import sys
import json
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix
# Add backend directory to sys.path to enable imports of app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 1. Define paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "..", "..", "Subscription Fatigue.csv")
MODEL_SAVE_PATH = os.path.join(BASE_DIR, "models", "catboost_model.cbm")
METRICS_SAVE_PATH = os.path.join(BASE_DIR, "models", "model_metrics.json")

print("Loading data from:", DATA_PATH)
df = pd.read_csv(DATA_PATH)

# 2. Data Preprocessing & Cleaning
# Clip negative values for spend and usage
df['Avg_Usage_Hours_Per_Week'] = df['Avg_Usage_Hours_Per_Week'].clip(lower=0.0)
df['Monthly_Total_Spend'] = df['Monthly_Total_Spend'].clip(lower=0.0)

# Target and features splits
X = df.drop(columns=['Customer_ID', 'Will_Cancel_Next_3_Months'])
y = df['Will_Cancel_Next_3_Months']

# Categorical column names
cat_features = ['Income_Level', 'Payment_Mode', 'Device_Type']

# Convert categorical columns to string type
for col in cat_features:
    X[col] = X[col].astype(str)

# 3. Train-Test Split (80:20 stratified)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"Training set size: {X_train.shape[0]}, Test set size: {X_test.shape[0]}")

# 4. Train CatBoostClassifier
model = CatBoostClassifier(
    iterations=500,
    learning_rate=0.05,
    depth=6,
    eval_metric='AUC',
    random_seed=42,
    verbose=100
)

model.fit(
    X_train, y_train,
    cat_features=cat_features,
    eval_set=(X_test, y_test),
    early_stopping_rounds=50
)

# 5. Evaluate Model
y_pred = model.predict(X_test)
y_pred_proba = model.predict_proba(X_test)[:, 1]

accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred)
recall = recall_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)
roc_auc = roc_auc_score(y_test, y_pred_proba)

tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()

# Feature importance
feature_importance_dict = dict(zip(X.columns, model.get_feature_importance().tolist()))

metrics = {
    "model_version": "v1.2.0-catboost",
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
os.makedirs(os.path.dirname(MODEL_SAVE_PATH), exist_ok=True)

# Save CatBoost model
model.save_model(MODEL_SAVE_PATH)
print(f"Model saved to: {MODEL_SAVE_PATH}")

# Save metrics JSON
with open(METRICS_SAVE_PATH, "w") as f:
    json.dump(metrics, f, indent=2)
print(f"Metrics saved to: {METRICS_SAVE_PATH}")

# Save metrics to database
print("Saving model evaluation metrics to database...")
db = None
try:
    from backend.app.database import SessionLocal
    from backend.app.models import ModelMetric

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

