"""Stress test the warning workflow when the current official NAV is unavailable.

At prediction date t, the delayed-NAV scenario uses the current ETF close but
the official NAV from t-1. NAV-dependent gap, return and rolling features are
rebuilt using only that information. Market-only features remain at date t.
The same purged expanding-window folds and validation-only tuning are used.
"""
from __future__ import annotations

from pathlib import Path
import json
import math
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier


warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
DATA, OUT, FIG = ROOT / "data" / "processed", ROOT / "outputs", ROOT / "figures"
MODEL_INPUT = DATA / "ETF_Modeling_Dataset_Leakage_Safe_2021_to_2026.csv"
RAW_INPUT = DATA / "ETF_Analysis_Ready_2021_to_2026.csv"
METRICS_CSV = OUT / "ETF_NAV_Timing_Stress_Metrics.csv"
SUMMARY_CSV = OUT / "ETF_NAV_Timing_Stress_Summary.csv"
RESULTS_JSON = OUT / "nav_timing_stress_results.json"
TARGET = "Y_Abnormal_Dislocation_95Q"

FOLDS = [
    {"Fold": "Fold 1", "Train_End": "2022-12-31", "Validation_Year": 2023, "Test_Year": 2024},
    {"Fold": "Fold 2", "Train_End": "2023-12-31", "Validation_Year": 2024, "Test_Year": 2025},
    {"Fold": "Fold 3", "Train_End": "2024-12-31", "Validation_Year": 2025, "Test_Year": 2026},
]


def purge_prior(prior, following):
    if prior.empty or following.empty:
        return prior.copy()
    return prior.loc[prior["Target_Date"] < following["Prediction_Date"].min()].copy()


def top_budget(y, score, budget=.10):
    y, score = np.asarray(y, int), np.asarray(score, float)
    k = max(1, int(math.ceil(len(y) * budget)))
    idx = np.argsort(-score, kind="stable")[:k]
    tp = int(y[idx].sum())
    return {"Alerts": k, "True_Positives": tp, "Precision": float(tp / k),
            "Recall": float(tp / max(1, y.sum()))}


model = pd.read_csv(MODEL_INPUT, parse_dates=["Prediction_Date", "Target_Date"])
raw = pd.read_csv(RAW_INPUT, parse_dates=["Date"]).sort_values("Date").copy()

# Rebuild the date-t gap using the latest NAV that would have been available
# under a full one-trading-day publication delay.
raw["Stale_NAV"] = raw["NAV"].shift(1)
raw["Stale_Dislocation"] = 100.0 * (raw["ETF_Close"] - raw["Stale_NAV"]) / raw["Stale_NAV"]
raw["Stale_Abs"] = raw["Stale_Dislocation"].abs()
raw["Stale_NAV_Return"] = raw["Stale_NAV"].pct_change() * 100.0
raw["ETF_Return"] = raw["ETF_Close"].pct_change() * 100.0
raw["Stale_Tracking_Return"] = raw["ETF_Return"] - raw["Stale_NAV_Return"]
raw["Stale_Threshold"] = raw["Stale_Abs"].rolling(252, min_periods=252).quantile(.95)
raw["Stale_Ratio"] = raw["Stale_Abs"] / raw["Stale_Threshold"]
raw["Stale_Premium"] = (raw["Stale_Dislocation"] > 0).astype(int)
for lag in [1, 2, 5]: raw[f"Stale_Lag_{lag}"] = raw["Stale_Dislocation"].shift(lag)
raw["Stale_Mean_5"] = raw["Stale_Abs"].rolling(5, min_periods=5).mean()
raw["Stale_Mean_20"] = raw["Stale_Abs"].rolling(20, min_periods=20).mean()
raw["Stale_SD_20"] = raw["Stale_Abs"].rolling(20, min_periods=20).std()

stale = raw[["Date", "Stale_Dislocation", "Stale_Abs", "Stale_NAV_Return", "Stale_Tracking_Return",
             "Stale_Threshold", "Stale_Ratio", "Stale_Premium", "Stale_Lag_1", "Stale_Lag_2",
             "Stale_Lag_5", "Stale_Mean_5", "Stale_Mean_20", "Stale_SD_20"]]
df = model.merge(stale, left_on="Prediction_Date", right_on="Date", how="left").drop(columns="Date")
replace = {
    "X_Dislocation_Pct_t": "Stale_Dislocation",
    "X_Abs_Dislocation_Pct_t": "Stale_Abs",
    "X_Dislocation_Lag_1_Pct": "Stale_Lag_1",
    "X_Dislocation_Lag_2_Pct": "Stale_Lag_2",
    "X_Dislocation_Lag_5_Pct": "Stale_Lag_5",
    "X_Premium_Flag_t": "Stale_Premium",
    "X_Abs_Dislocation_Mean_5D_Pct": "Stale_Mean_5",
    "X_Abs_Dislocation_Mean_20D_Pct": "Stale_Mean_20",
    "X_Abs_Dislocation_Std_20D_Pct": "Stale_SD_20",
    "X_Current_Abs_Gap_to_Threshold_Ratio": "Stale_Ratio",
    "X_NAV_Return_1D_Pct": "Stale_NAV_Return",
    "X_Tracking_Return_Difference_1D_Pct": "Stale_Tracking_Return",
}
for feature, source in replace.items(): df[feature] = df[source]
df["Rolling_Threshold_95Pct"] = df["Stale_Threshold"]
features = [c for c in model.columns if c.startswith("X_")]
df = df.dropna(subset=features + [TARGET]).copy()

rows = []
for spec in FOLDS:
    fold = spec["Fold"]
    train = df[df["Target_Date"] <= pd.Timestamp(spec["Train_End"])].copy()
    valid = df[df["Target_Date"].dt.year.eq(spec["Validation_Year"])].copy()
    test = df[df["Target_Date"].dt.year.eq(spec["Test_Year"])].copy()
    train, valid = purge_prior(train, valid), purge_prior(valid, test)
    Xtr, ytr = train[features], train[TARGET].astype(int)
    Xva, yva = valid[features], valid[TARGET].astype(int)
    Xte, yte = test[features], test[TARGET].astype(int)

    fitted = {}
    candidates = []
    for c in [.01, .1, 1., 10.]:
        m = Pipeline([("scale", StandardScaler()), ("model", LogisticRegression(
            C=c, penalty="l2", solver="liblinear", max_iter=5000, random_state=42))]).fit(Xtr, ytr)
        p = m.predict_proba(Xva)[:, 1]
        candidates.append((average_precision_score(yva, p), -brier_score_loss(yva, p), m))
    fitted["Logistic Regression"] = max(candidates, key=lambda z: (z[0], z[1]))[2]

    candidates = []
    for depth in [2, 3, 4, 5]:
        for leaf in [10, 25, 50]:
            for weight in [None, "balanced"]:
                m = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=leaf,
                    class_weight=weight, random_state=42).fit(Xtr, ytr)
                p = m.predict_proba(Xva)[:, 1]
                candidates.append((average_precision_score(yva, p), -brier_score_loss(yva, p), m))
    fitted["Decision Tree"] = max(candidates, key=lambda z: (z[0], z[1]))[2]

    candidates = []
    for depth in [3, 5, None]:
        for leaf in [5, 10, 20]:
            for mf in ["sqrt", .5]:
                for weight in [None, "balanced_subsample"]:
                    m = RandomForestClassifier(n_estimators=400, max_depth=depth,
                        min_samples_leaf=leaf, max_features=mf, class_weight=weight,
                        random_state=42, n_jobs=-1).fit(Xtr, ytr)
                    p = m.predict_proba(Xva)[:, 1]
                    candidates.append((average_precision_score(yva, p), -brier_score_loss(yva, p), m))
    fitted["Random Forest"] = max(candidates, key=lambda z: (z[0], z[1]))[2]

    scores = {"Current Gap Ratio": test["X_Current_Abs_Gap_to_Threshold_Ratio"].to_numpy(float)}
    for name, fitted_model in fitted.items(): scores[name] = fitted_model.predict_proba(Xte)[:, 1]
    for name, score in scores.items():
        budget = top_budget(yte, score)
        rows.append({"Fold": fold, "Test_Year": spec["Test_Year"], "Model": name,
                     "Observations": len(test), "Events": int(yte.sum()),
                     "PR_AUC": float(average_precision_score(yte, score)), **budget})

metrics = pd.DataFrame(rows)
summary = metrics.groupby("Model", as_index=False).agg(
    Folds=("Fold", "nunique"), Mean_PR_AUC=("PR_AUC", "mean"),
    Minimum_PR_AUC=("PR_AUC", "min"), Maximum_PR_AUC=("PR_AUC", "max"),
    Mean_Precision_at_10Pct=("Precision", "mean"), Mean_Recall_at_10Pct=("Recall", "mean"))
metrics.to_csv(METRICS_CSV, index=False, float_format="%.17g")
summary.to_csv(SUMMARY_CSV, index=False, float_format="%.17g")
RESULTS_JSON.write_text(json.dumps({
    "analysis": "One-trading-day delayed official NAV stress test",
    "information_set": "Current ETF market data plus official NAV from the preceding trading date",
    "replaced_features": replace,
    "metrics": metrics.to_dict("records"), "summary": summary.to_dict("records")
}, indent=2), encoding="utf-8")

pivot = metrics.pivot(index="Test_Year", columns="Model", values="PR_AUC")
ax = pivot.plot(marker="o", figsize=(8.2, 4.7))
ax.set_title("Delayed-NAV stress test: test PR-AUC")
ax.set_xlabel("Test year"); ax.set_ylabel("PR-AUC"); ax.grid(alpha=.25)
ax.legend(frameon=False, fontsize=8, ncol=2)
plt.tight_layout(); plt.savefig(FIG / "ETF_NAV_Timing_Stress_PR_AUC.png", dpi=220, bbox_inches="tight"); plt.close()

print(json.dumps(summary.to_dict("records"), indent=2))
