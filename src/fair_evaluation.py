"""
fair_evaluation.py  --  protocol used in the revised paper.
All three models get the same class-balanced weighting. Hyper-parameters are fixed in advance
(no tuning). The operating threshold of each model is chosen ONLY from 5-fold out-of-fold
predictions on the training split (highest threshold with OOF recall >= TARGET_RECALL); the 20 %
held-out test split (same split as before: random_state=42) is touched once, for reporting.
Run:  python fair_evaluation.py   (needs synthetic_batches.csv beside it)
"""
import json, warnings
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score, roc_curve
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.utils.class_weight import compute_sample_weight
warnings.filterwarnings("ignore")
BASE = Path(__file__).resolve().parent
CAT = ["crop_type", "supply_chain_stage"]
NUM = ["storage_temp_c", "storage_duration_hrs", "transit_time_hrs", "transit_temp_c",
       "humidity_pct", "prior_inspection_fail_count", "days_since_harvest"]
TARGET, TARGET_RECALL, N_BOOT = "contaminated", 0.80, 2000

d = pd.read_csv(BASE / "synthetic_batches.csv")
X, y = d[CAT + NUM], d[TARGET].astype(int)
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.20, random_state=42, stratify=y)

def pipe(clf, scale=False):
    pre = ColumnTransformer([("c", OneHotEncoder(handle_unknown="ignore"), CAT),
                             ("n", StandardScaler() if scale else "passthrough", NUM)])
    return Pipeline([("p", pre), ("c", clf)])

def make(name):
    if name == "LR":  return pipe(LogisticRegression(max_iter=2000, class_weight="balanced"), True)
    if name == "RF":  return pipe(RandomForestClassifier(n_estimators=200, random_state=42,
                                  class_weight="balanced", n_jobs=-1))
    return pipe(GradientBoostingClassifier(random_state=42))

def fit(m, Xa, ya):
    sw = compute_sample_weight("balanced", ya)
    return m.fit(Xa, ya, c__sample_weight=sw) if isinstance(m.steps[-1][1], GradientBoostingClassifier) else m.fit(Xa, ya)

def pick_threshold(ya, p, target):
    ts = np.unique(np.round(p, 4))[::-1]
    for t in ts:
        if (p[ya == 1] >= t).mean() >= target: return float(t)
    return float(ts[-1])

skf = StratifiedKFold(5, shuffle=True, random_state=1)
res, P, models, rng = {}, {}, {}, np.random.default_rng(0)
yt = yte.values; n = len(yt)
for name in ("LR", "RF", "GB"):
    oof = np.zeros(len(ytr))
    for a, b in skf.split(Xtr, ytr):
        m = fit(make(name), Xtr.iloc[a], ytr.iloc[a]); oof[b] = m.predict_proba(Xtr.iloc[b])[:, 1]
    thr = pick_threshold(ytr.values, oof, TARGET_RECALL)
    m = fit(make(name), Xtr, ytr); p = m.predict_proba(Xte)[:, 1]
    models[name], P[name] = m, p
    res[name] = {"cv_auc": float(roc_auc_score(ytr, oof)), "cv_ap": float(average_precision_score(ytr, oof)),
                 "threshold": thr}
def at(p, t):
    pr = p >= t; tp = int((pr & (yt == 1)).sum()); fp = int((pr & (yt == 0)).sum())
    fn = int((~pr & (yt == 1)).sum()); tn = int((~pr & (yt == 0)).sum())
    rec = tp / (tp + fn); prec = tp / max(tp + fp, 1); fpr = fp / (fp + tn)
    return dict(recall=rec, precision=prec, f1=2*prec*rec/max(prec+rec, 1e-9), fpr=fpr, tp=tp, fp=fp, fn=fn, tn=tn)
idx = [rng.integers(0, n, n) for _ in range(N_BOOT)]
def ci(f): v = np.array([f(i) for i in idx]); return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]
for name, p in P.items():
    t = res[name]["threshold"]
    res[name].update(test_auc=float(roc_auc_score(yt, p)), test_ap=float(average_precision_score(yt, p)),
        auc_ci=ci(lambda i: roc_auc_score(yt[i], p[i])), ap_ci=ci(lambda i: average_precision_score(yt[i], p[i])),
        op=at(p, t), op_recall_ci=ci(lambda i: ((p[i] >= t) & (yt[i] == 1)).sum() / (yt[i] == 1).sum()),
        op_prec_ci=ci(lambda i: ((p[i] >= t) & (yt[i] == 1)).sum() / max((p[i] >= t).sum(), 1)),
        at05=at(p, 0.5))
    f, tp_, _ = roc_curve(yt, p)
    res[name]["recall_at_fpr"] = {str(q): float(np.interp(q, f, tp_)) for q in (0.05, 0.10, 0.15)}
res["paired"] = {}
for a, b in (("GB", "RF"), ("GB", "LR"), ("RF", "LR")):
    res["paired"][f"{a}-{b} AUC"] = [float(np.percentile([roc_auc_score(yt[i], P[a][i]) - roc_auc_score(yt[i], P[b][i]) for i in idx], q)) for q in (2.5, 50, 97.5)]
    res["paired"][f"{a}-{b} AP"] = [float(np.percentile([average_precision_score(yt[i], P[a][i]) - average_precision_score(yt[i], P[b][i]) for i in idx], q)) for q in (2.5, 50, 97.5)]
res["info"] = dict(rows=len(d), prevalence=float(y.mean()), train=len(Xtr), test=len(Xte), test_pos=int(yt.sum()),
                   target_recall=TARGET_RECALL, n_boot=N_BOOT)
# permutation importance (test, AUC drop) for GB and RF
for name in ("RF", "GB"):
    pi = permutation_importance(models[name], Xte, yte, scoring="roc_auc", n_repeats=20, random_state=0)
    res[f"perm_{name}"] = {c: [float(pi.importances_mean[k]), float(pi.importances_std[k])] for k, c in enumerate(X.columns)}
(BASE / "fair_results.json").write_text(json.dumps(res, indent=1))
print(json.dumps({k: v for k, v in res.items() if not k.startswith("perm_")}, indent=1))
for name in ("RF", "GB"):
    print(name, sorted(res[f"perm_{name}"].items(), key=lambda kv: -kv[1][0]))
