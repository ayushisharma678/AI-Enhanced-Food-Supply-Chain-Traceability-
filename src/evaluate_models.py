"""
evaluate_models.py
Evaluates Logistic Regression, Random Forest and Gradient Boosting on the SAME
data split (80/20, stratified, random_state=42) and writes:
  - model_results.json
  - model_comparison_chart.png

Random Forest: uses the shipped food_risk_model.joblib if it is beside this
script, so the numbers match the app and the PPT exactly. If the file is
missing, it trains a Random Forest with the same settings as train_model.py.

Run:  python evaluate_models.py
"""
import json
import warnings
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

warnings.filterwarnings("ignore")
BASE = Path(__file__).resolve().parent
THRESHOLDS = (0.5, 0.3)

CAT = ["crop_type", "supply_chain_stage"]
NUM = ["storage_temp_c", "storage_duration_hrs", "transit_time_hrs",
       "transit_temp_c", "humidity_pct", "prior_inspection_fail_count",
       "days_since_harvest"]
TARGET = "contaminated"

df = pd.read_csv(BASE / "synthetic_batches.csv")[CAT + NUM + [TARGET]].dropna()
X, y = df[CAT + NUM], df[TARGET].astype(int)
X_tr, X_te, y_tr, y_te = train_test_split(
    X, y, test_size=0.20, random_state=42, stratify=y)


def pipe(clf, scale=False):
    num = StandardScaler() if scale else "passthrough"
    pre = ColumnTransformer([
        ("categories", OneHotEncoder(handle_unknown="ignore"), CAT),
        ("numbers", num, NUM)])
    return Pipeline([("preprocessor", pre), ("classifier", clf)])


models = {}
models["logreg"] = ("Logistic Regression (baseline)",
                    pipe(LogisticRegression(max_iter=2000), scale=True).fit(X_tr, y_tr))
models["gb"] = ("Gradient Boosting",
                pipe(GradientBoostingClassifier(random_state=42)).fit(X_tr, y_tr))

rf_path = BASE / "food_risk_model.joblib"
if rf_path.exists():
    rf, rf_source = joblib.load(rf_path), "shipped food_risk_model.joblib"
else:
    rf = pipe(RandomForestClassifier(n_estimators=200, random_state=42,
                                     class_weight="balanced", n_jobs=-1)).fit(X_tr, y_tr)
    rf_source = "trained here (same settings as train_model.py)"
models["rf"] = ("Random Forest", rf)

results = {"info": {"dataset": "synthetic_batches.csv", "rows": int(len(df)),
                    "train_rows": int(len(X_tr)), "test_rows": int(len(X_te)),
                    "test_positives": int(y_te.sum()),
                    "split": "80/20 stratified, random_state=42",
                    "random_forest_source": rf_source},
           "metrics": {}, "confusion_matrices": {}}

for key, (name, model) in models.items():
    prob = model.predict_proba(X_te)[:, 1]
    auc = float(roc_auc_score(y_te, prob))
    for t in THRESHOLDS:
        # positive when probability is ABOVE the threshold (same rule as model.predict at 0.5)
        pred = (prob > t).astype(int)
        tag = f"{key}@{t}"
        results["metrics"][tag] = {
            "model": name, "threshold": t,
            "accuracy": round(float(accuracy_score(y_te, pred)), 4),
            "precision": round(float(precision_score(y_te, pred, zero_division=0)), 4),
            "recall": round(float(recall_score(y_te, pred)), 4),
            "f1": round(float(f1_score(y_te, pred)), 4),
            "roc_auc": round(auc, 4)}
        results["confusion_matrices"][tag] = confusion_matrix(y_te, pred).tolist()

# Random Forest feature importance (one-hot columns added back to their group)
pre, clf = rf.named_steps["preprocessor"], rf.named_steps["classifier"]
imp = {}
for n, v in zip(pre.get_feature_names_out(), clf.feature_importances_):
    n = n.split("__", 1)[1]
    group = "crop_type" if n.startswith("crop_type_") else \
            "supply_chain_stage" if n.startswith("supply_chain_stage_") else n
    imp[group] = imp.get(group, 0) + float(v)
results["feature_importance_rf"] = dict(
    sorted(((k, round(v, 4)) for k, v in imp.items()), key=lambda kv: -kv[1]))

(BASE / "model_results.json").write_text(json.dumps(results, indent=2))

# ---- chart: two panels (threshold 0.5 and 0.3) ----
labels = ["Logistic\nRegression", "Random\nForest", "Gradient\nBoosting"]
keys = ["logreg", "rf", "gb"]
mets = [("accuracy", "Accuracy", "#9aa5a1"), ("precision", "Precision", "#c8852b"),
        ("recall", "Recall", "#1f7a6a"), ("f1", "F1", "#15594d")]
fig, axes = plt.subplots(1, 2, figsize=(14, 5.6), sharey=True)
for ax, t in zip(axes, THRESHOLDS):
    w = 0.2
    for i, (m, lab, col) in enumerate(mets):
        vals = [results["metrics"][f"{k}@{t}"][m] * 100 for k in keys]
        bars = ax.bar(np.arange(3) + (i - 1.5) * w, vals, w, label=lab, color=col)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 1, f"{v:.1f}", ha="center", fontsize=8)
    ax.set_xticks(range(3)); ax.set_xticklabels(labels)
    ax.set_title(f"Decision threshold = {t}", fontsize=12, fontweight="bold")
    ax.set_ylim(0, 108); ax.spines[["top", "right"]].set_visible(False)
axes[0].set_ylabel("Score (%)")
axes[0].legend(loc="upper center", ncol=4, fontsize=9, frameon=False)
fig.suptitle(f"Model Comparison - Synthetic Test Set (N={len(X_te)})",
             fontsize=14, fontweight="bold")
fig.tight_layout()
fig.savefig(BASE / "model_comparison_chart.png", dpi=200)

print(f"Random Forest source: {rf_source}\n")
print(f"{'model@threshold':<16}{'Acc':>7}{'Prec':>7}{'Rec':>7}{'F1':>7}{'AUC':>8}")
for tag, m in results["metrics"].items():
    print(f"{tag:<16}{m['accuracy']*100:7.1f}{m['precision']*100:7.1f}"
          f"{m['recall']*100:7.1f}{m['f1']*100:7.1f}{m['roc_auc']:8.3f}")
print("\nRF feature importance:", results["feature_importance_rf"])
print("\nSaved model_results.json and model_comparison_chart.png")
