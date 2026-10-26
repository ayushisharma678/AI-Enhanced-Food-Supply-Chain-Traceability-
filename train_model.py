
from pathlib import Path
import json

import joblib
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "synthetic_batches.csv"
MODEL_PATH = BASE_DIR / "food_risk_model.joblib"
METRICS_PATH = BASE_DIR / "trained_model_metrics.json"

# 1. Load the existing dataset
if not DATA_PATH.exists():
    raise FileNotFoundError(
        "synthetic_batches.csv is missing. "
        "Copy it beside train_model.py."
    )

df = pd.read_csv(DATA_PATH)

categorical_features = [
    "crop_type",
    "supply_chain_stage",
]

numeric_features = [
    "storage_temp_c",
    "storage_duration_hrs",
    "transit_time_hrs",
    "transit_temp_c",
    "humidity_pct",
    "prior_inspection_fail_count",
    "days_since_harvest",
]

target = "contaminated"
features = categorical_features + numeric_features

required_columns = features + [target]
missing = [c for c in required_columns if c not in df.columns]

if missing:
    raise ValueError(f"Missing dataset columns: {missing}")

df = df[required_columns].dropna().copy()

# The target must contain both classes: 0 and 1.
if df[target].nunique() != 2:
    raise ValueError(
        "The contamination target must contain both 0 and 1."
    )

X = df[features]
y = df[target].astype(int)

# 2. Keep a separate test set for evaluation.
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y,
)

# 3. Convert crop and stage categories into numeric features.
preprocessor = ColumnTransformer(
    transformers=[
        (
            "categories",
            OneHotEncoder(handle_unknown="ignore"),
            categorical_features,
        ),
        ("numbers", "passthrough", numeric_features),
    ]
)

# 4. Build and train the model.
model = Pipeline(
    steps=[
        ("preprocessor", preprocessor),
        (
            "classifier",
            RandomForestClassifier(
                n_estimators=200,
                random_state=42,
                class_weight="balanced",
                n_jobs=-1,
            ),
        ),
    ]
)

model.fit(X_train, y_train)

# 5. Evaluate on data not used during training.
predictions = model.predict(X_test)
probabilities = model.predict_proba(X_test)[:, 1]

metrics = {
    "model": "Random Forest",
    "dataset": DATA_PATH.name,
    "rows_used": int(len(df)),
    "train_rows": int(len(X_train)),
    "test_rows": int(len(X_test)),
    "accuracy": float(accuracy_score(y_test, predictions)),
    "precision": float(
        precision_score(y_test, predictions, zero_division=0)
    ),
    "recall": float(
        recall_score(y_test, predictions, zero_division=0)
    ),
    "f1": float(f1_score(y_test, predictions, zero_division=0)),
    "roc_auc": float(roc_auc_score(y_test, probabilities)),
    "confusion_matrix": confusion_matrix(
        y_test, predictions
    ).tolist(),
    "classification_report": classification_report(
        y_test,
        predictions,
        output_dict=True,
        zero_division=0,
    ),
}

# 6. Save the trained model and its evaluation results.
joblib.dump(model, MODEL_PATH)

with open(METRICS_PATH, "w", encoding="utf-8") as file:
    json.dump(metrics, file, indent=2)

print("\nMODEL TRAINING COMPLETE")
print("-" * 40)
print(f"Rows used: {len(df)}")
print(f"Training rows: {len(X_train)}")
print(f"Test rows: {len(X_test)}")
print(f"Accuracy:  {metrics['accuracy']:.3f}")
print(f"Precision: {metrics['precision']:.3f}")
print(f"Recall:    {metrics['recall']:.3f}")
print(f"F1 score:  {metrics['f1']:.3f}")
print(f"ROC-AUC:   {metrics['roc_auc']:.3f}")
print(f"Confusion matrix: {metrics['confusion_matrix']}")
print(f"\nSaved model: {MODEL_PATH.name}")
print(f"Saved metrics: {METRICS_PATH.name}")
