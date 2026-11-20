"""Validation-tuned histogram gradient boosting on frozen walk-forward folds.

This model closes the original proposal's gradient-boosting comparison without
altering the primary model family, label, folds or reported classifier results.
"""
from __future__ import annotations

from pathlib import Path
import json
import math

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, brier_score_loss


ROOT = Path(__file__).resolve().parents[1]
DATA, OUT = ROOT / "data" / "processed", ROOT / "outputs"
INPUT = DATA / "ETF_Modeling_Dataset_Leakage_Safe_2021_to_2026.csv"
METRICS_CSV = OUT / "ETF_Gradient_Boosting_Metrics.csv"
TUNING_CSV = OUT / "ETF_Gradient_Boosting_Tuning.csv"
RESULTS_JSON = OUT / "gradient_boosting_results.json"
TARGET = "Y_Abnormal_Dislocation_95Q"
FOLDS = [
    {"Fold": "Fold 1", "Train_End": "2022-12-31", "Validation_Year": 2023, "Test_Year": 2024},
    {"Fold": "Fold 2", "Train_End": "2023-12-31", "Validation_Year": 2024, "Test_Year": 2025},
    {"Fold": "Fold 3", "Train_End": "2024-12-31", "Validation_Year": 2025, "Test_Year": 2026},
]


def purge_prior(prior, following):
    if prior.empty or following.empty: return prior.copy()
    return prior.loc[prior["Target_Date"] < following["Prediction_Date"].min()].copy()


def budget(y, score, level=.10):
    y, score = np.asarray(y, int), np.asarray(score, float)
    k = max(1, int(math.ceil(len(y) * level)))
    tp = int(y[np.argsort(-score, kind="stable")[:k]].sum())
    return {"Alerts": k, "True_Positives": tp, "Precision": float(tp/k),
            "Recall": float(tp/max(1, y.sum()))}


df = pd.read_csv(INPUT, parse_dates=["Prediction_Date", "Target_Date"])
features = [c for c in df.columns if c.startswith("X_")]
tuning_rows, metric_rows = [], []
for spec in FOLDS:
    train = purge_prior(df[df["Target_Date"] <= pd.Timestamp(spec["Train_End"])],
                        df[df["Target_Date"].dt.year.eq(spec["Validation_Year"])])
    valid = purge_prior(df[df["Target_Date"].dt.year.eq(spec["Validation_Year"])],
                        df[df["Target_Date"].dt.year.eq(spec["Test_Year"])])
    test = df[df["Target_Date"].dt.year.eq(spec["Test_Year"])].copy()
    Xtr, ytr = train[features], train[TARGET].astype(int)
    Xva, yva = valid[features], valid[TARGET].astype(int)
    Xte, yte = test[features], test[TARGET].astype(int)
    candidates = []
    for lr in [.05, .10]:
        for leaves in [7, 15]:
            for l2 in [0., 1.]:
                m = HistGradientBoostingClassifier(learning_rate=lr, max_leaf_nodes=leaves,
                    max_iter=150, l2_regularization=l2, class_weight="balanced", random_state=42).fit(Xtr, ytr)
                p = m.predict_proba(Xva)[:, 1]
                row = {"Fold": spec["Fold"], "Learning_Rate": lr, "Max_Leaf_Nodes": leaves,
                       "L2_Regularization": l2, "Validation_PR_AUC": float(average_precision_score(yva, p)),
                       "Validation_Brier": float(brier_score_loss(yva, p))}
                tuning_rows.append(row); candidates.append((row, m))
    selected, fitted = max(candidates, key=lambda z: (z[0]["Validation_PR_AUC"], -z[0]["Validation_Brier"]))
    p = fitted.predict_proba(Xte)[:, 1]
    metric_rows.append({"Fold": spec["Fold"], "Test_Year": spec["Test_Year"],
                        "Observations": int(len(test)), "Events": int(yte.sum()),
                        "Selected_Learning_Rate": selected["Learning_Rate"],
                        "Selected_Max_Leaf_Nodes": selected["Max_Leaf_Nodes"],
                        "Selected_L2_Regularization": selected["L2_Regularization"],
                        "PR_AUC": float(average_precision_score(yte, p)),
                        "Brier_Score": float(brier_score_loss(yte, p)), **budget(yte, p)})

tuning, metrics = pd.DataFrame(tuning_rows), pd.DataFrame(metric_rows)
summary = {"Mean_PR_AUC": float(metrics["PR_AUC"].mean()),
           "Minimum_PR_AUC": float(metrics["PR_AUC"].min()),
           "Maximum_PR_AUC": float(metrics["PR_AUC"].max()),
           "Mean_Precision_at_10Pct": float(metrics["Precision"].mean()),
           "Mean_Recall_at_10Pct": float(metrics["Recall"].mean())}
tuning.to_csv(TUNING_CSV, index=False, float_format="%.17g")
metrics.to_csv(METRICS_CSV, index=False, float_format="%.17g")
RESULTS_JSON.write_text(json.dumps({"analysis": "Validation-tuned histogram gradient boosting",
    "metrics": metrics.to_dict("records"), "summary": summary}, indent=2), encoding="utf-8")
print(json.dumps({"metrics": metrics.to_dict("records"), "summary": summary}, indent=2))
