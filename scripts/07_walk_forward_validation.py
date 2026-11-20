"""Purged expanding-window validation for the enhanced final study.

The fold definitions and reporting rules are frozen in docs/ANALYSIS_PLAN_V2.md.
Models are fitted on each fold's training period, hyperparameters are selected
using validation PR-AUC only, and the subsequent calendar period is evaluated
once. No test outcome enters tuning or feature selection.
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
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier


warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = ROOT / "outputs"
FIG = ROOT / "figures"
OUT.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)

INPUT = DATA / "ETF_Modeling_Dataset_Leakage_Safe_2021_to_2026.csv"
RESULTS_JSON = OUT / "walk_forward_results.json"
METRICS_CSV = OUT / "ETF_Walk_Forward_Metrics.csv"
PREDICTIONS_CSV = OUT / "ETF_Walk_Forward_Predictions.csv"
TUNING_CSV = OUT / "ETF_Walk_Forward_Tuning.csv"
COEFFICIENTS_CSV = OUT / "ETF_Logistic_Standardized_Coefficients.csv"

df = pd.read_csv(INPUT, parse_dates=["Prediction_Date", "Target_Date"])
features = [c for c in df.columns if c.startswith("X_")]
target = "Y_Abnormal_Dislocation_95Q"

folds = [
    {"Fold": "Fold 1", "Train_End": "2022-12-31", "Validation_Year": 2023, "Test_Year": 2024},
    {"Fold": "Fold 2", "Train_End": "2023-12-31", "Validation_Year": 2024, "Test_Year": 2025},
    {"Fold": "Fold 3", "Train_End": "2024-12-31", "Validation_Year": 2025, "Test_Year": 2026},
]


def safe_auc(y, score):
    return float(roc_auc_score(y, score)) if len(np.unique(y)) > 1 else None


def top_budget(y, score, budget=0.10):
    y = np.asarray(y, dtype=int)
    score = np.asarray(score, dtype=float)
    k = max(1, int(math.ceil(len(y) * budget)))
    order = np.argsort(-score, kind="stable")
    alert = np.zeros(len(y), dtype=int)
    alert[order[:k]] = 1
    tp = int(((alert == 1) & (y == 1)).sum())
    precision = tp / k
    prevalence = y.mean()
    return {
        "Budget_Pct": budget * 100,
        "Alerts": k,
        "True_Positives": tp,
        "Precision": float(precision),
        "Recall": float(tp / max(1, y.sum())),
        "Lift": float(precision / prevalence) if prevalence else None,
        "Number_Needed_to_Review": float(k / tp) if tp else None,
        "Alert_Flag": alert,
    }


def no_skill_budget(y, budget=0.10):
    """Expected performance from random review at the same capacity.

    A constant prevalence score contains no ranking information, so choosing
    arbitrary tied rows would make its realised precision depend on row order.
    """
    y = np.asarray(y, dtype=int)
    k = max(1, int(math.ceil(len(y) * budget)))
    prevalence = float(y.mean())
    return {
        "Budget_Pct": budget * 100,
        "Alerts": k,
        "True_Positives": float(k * prevalence),
        "Precision": prevalence,
        "Recall": float(k / len(y)),
        "Lift": 1.0,
        "Number_Needed_to_Review": float(1 / prevalence) if prevalence else None,
        "Alert_Flag": np.zeros(len(y), dtype=int),
    }


def purge_prior(prior, following):
    """Remove any prior sample whose label reaches the next split's feature date."""
    if prior.empty or following.empty:
        return prior.copy(), 0
    first_next_prediction = following["Prediction_Date"].min()
    keep = prior["Target_Date"] < first_next_prediction
    return prior.loc[keep].copy(), int((~keep).sum())


def metric_row(fold, model, split, y, score, probability=False):
    row = {
        "Fold": fold,
        "Model": model,
        "Split": split,
        "Observations": int(len(y)),
        "Events": int(np.asarray(y).sum()),
        "Event_Rate": float(np.asarray(y).mean()),
        "PR_AUC": float(average_precision_score(y, score)),
        "ROC_AUC": safe_auc(y, score),
        "Brier_Score": None,
        "Log_Loss": None,
    }
    if probability:
        p = np.clip(np.asarray(score, dtype=float), 1e-6, 1 - 1e-6)
        row["Brier_Score"] = float(brier_score_loss(y, p))
        row["Log_Loss"] = float(log_loss(y, p, labels=[0, 1]))
    return row


metric_rows, tuning_rows, coefficient_rows, prediction_parts, fold_audit = [], [], [], [], []

for spec in folds:
    fold = spec["Fold"]
    train = df[df["Target_Date"] <= pd.Timestamp(spec["Train_End"])].copy()
    valid = df[df["Target_Date"].dt.year.eq(spec["Validation_Year"])].copy()
    test = df[df["Target_Date"].dt.year.eq(spec["Test_Year"])].copy()

    train, purge_train = purge_prior(train, valid)
    valid, purge_valid = purge_prior(valid, test)

    counts = {
        "Fold": fold,
        "Train_Target_End": spec["Train_End"],
        "Validation_Year": spec["Validation_Year"],
        "Test_Year": spec["Test_Year"],
        "Train_Rows": len(train), "Train_Events": int(train[target].sum()),
        "Validation_Rows": len(valid), "Validation_Events": int(valid[target].sum()),
        "Test_Rows": len(test), "Test_Events": int(test[target].sum()),
        "Purged_Train_Boundary_Rows": purge_train,
        "Purged_Validation_Boundary_Rows": purge_valid,
        "Feasible": True,
        "Reason": "",
    }
    if any(part[target].nunique() < 2 for part in [train, valid, test]):
        counts["Feasible"] = False
        counts["Reason"] = "At least one partition contains only one outcome class"
        fold_audit.append(counts)
        continue
    fold_audit.append(counts)

    Xtr, ytr = train[features], train[target].astype(int)
    Xva, yva = valid[features], valid[target].astype(int)
    Xte, yte = test[features], test[target].astype(int)

    best = {}

    # Logistic regression.
    candidates = []
    for c in [0.01, 0.1, 1.0, 10.0]:
        model = Pipeline([
            ("scale", StandardScaler()),
            ("model", LogisticRegression(C=c, penalty="l2", solver="liblinear", max_iter=5000, random_state=42)),
        ])
        model.fit(Xtr, ytr)
        p = model.predict_proba(Xva)[:, 1]
        row = {"Fold": fold, "Model": "Logistic Regression", "Parameters": f"C={c}",
               "Validation_PR_AUC": average_precision_score(yva, p), "Validation_Brier": brier_score_loss(yva, p)}
        tuning_rows.append(row); candidates.append((row, model))
    best_row, log_model = max(candidates, key=lambda x: (x[0]["Validation_PR_AUC"], -x[0]["Validation_Brier"]))
    best["Logistic Regression"] = best_row["Parameters"]

    # Coefficients are on standardized training features because the selected
    # logistic model is a StandardScaler -> LogisticRegression pipeline.
    # Saving every fold makes the paper's explanation table reproducible.
    fold_coefficients = log_model.named_steps["model"].coef_[0]
    coefficient_order = np.argsort(-np.abs(fold_coefficients))
    for rank, feature_index in enumerate(coefficient_order, start=1):
        coefficient_rows.append({
            "Fold": fold,
            "Test_Year": spec["Test_Year"],
            "Selected_C": float(best_row["Parameters"].split("=")[1]),
            "Feature": features[feature_index],
            "Standardized_Coefficient": float(fold_coefficients[feature_index]),
            "Absolute_Coefficient": float(abs(fold_coefficients[feature_index])),
            "Absolute_Rank_within_Fold": rank,
        })

    # Bounded decision tree.
    candidates = []
    for depth in [2, 3, 4, 5]:
        for leaf in [10, 25, 50]:
            for weight in [None, "balanced"]:
                model = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=leaf, class_weight=weight, random_state=42)
                model.fit(Xtr, ytr)
                p = model.predict_proba(Xva)[:, 1]
                row = {"Fold": fold, "Model": "Decision Tree",
                       "Parameters": f"depth={depth}; leaf={leaf}; weight={weight}",
                       "Validation_PR_AUC": average_precision_score(yva, p), "Validation_Brier": brier_score_loss(yva, p)}
                tuning_rows.append(row); candidates.append((row, model))
    best_row, tree_model = max(candidates, key=lambda x: (x[0]["Validation_PR_AUC"], -x[0]["Validation_Brier"]))
    best["Decision Tree"] = best_row["Parameters"]

    # Random forest.
    candidates = []
    for depth in [3, 5, None]:
        for leaf in [5, 10, 20]:
            for max_features in ["sqrt", 0.5]:
                for weight in [None, "balanced_subsample"]:
                    model = RandomForestClassifier(
                        n_estimators=400, max_depth=depth, min_samples_leaf=leaf,
                        max_features=max_features, class_weight=weight,
                        random_state=42, n_jobs=-1,
                    )
                    model.fit(Xtr, ytr)
                    p = model.predict_proba(Xva)[:, 1]
                    row = {"Fold": fold, "Model": "Random Forest",
                           "Parameters": f"depth={depth}; leaf={leaf}; max_features={max_features}; weight={weight}",
                           "Validation_PR_AUC": average_precision_score(yva, p), "Validation_Brier": brier_score_loss(yva, p)}
                    tuning_rows.append(row); candidates.append((row, model))
    best_row, rf_model = max(candidates, key=lambda x: (x[0]["Validation_PR_AUC"], -x[0]["Validation_Brier"]))
    best["Random Forest"] = best_row["Parameters"]

    models = {
        "Logistic Regression": log_model,
        "Decision Tree": tree_model,
        "Random Forest": rf_model,
    }
    train_prevalence = float(ytr.mean())

    for split_name, part, y in [("Validation", valid, yva), ("Test", test, yte)]:
        scores = {
            "Historical Prevalence": np.repeat(train_prevalence, len(part)),
            "Current Absolute Gap": part["X_Abs_Dislocation_Pct_t"].to_numpy(float),
            "Current Gap Ratio": part["X_Current_Abs_Gap_to_Threshold_Ratio"].to_numpy(float),
            "Previous Event Persistence": (part["X_Abs_Dislocation_Pct_t"] > part["Rolling_Threshold_95Pct"]).astype(float).to_numpy(),
        }
        for name, model in models.items():
            scores[name] = model.predict_proba(part[features])[:, 1]

        for name, score in scores.items():
            probability = name in {"Historical Prevalence", "Logistic Regression", "Decision Tree", "Random Forest"}
            row = metric_row(fold, name, split_name, y, score, probability)
            budget = no_skill_budget(y, 0.10) if name == "Historical Prevalence" else top_budget(y, score, 0.10)
            row.update({k: v for k, v in budget.items() if k != "Alert_Flag"})
            metric_rows.append(row)

        if split_name == "Test":
            p = part[["Prediction_Date", "Target_Date", target, "Target_Abs_Dislocation_Pct"]].copy()
            p.insert(0, "Fold", fold)
            for name, score in scores.items():
                key = name.replace(" ", "_")
                p[f"{key}_Score"] = score
                budget_result = no_skill_budget(y, 0.10) if name == "Historical Prevalence" else top_budget(y, score, 0.10)
                p[f"{key}_Top10Pct_Alert"] = budget_result["Alert_Flag"]
            prediction_parts.append(p)

    # Add selected classifier to fold audit using validation results.
    fold_val = [r for r in metric_rows if r["Fold"] == fold and r["Split"] == "Validation" and r["Model"] in models]
    selected = sorted(fold_val, key=lambda r: (r["PR_AUC"], -(r["Brier_Score"] or 999)), reverse=True)[0]["Model"]
    fold_audit[-1]["Selected_Classifier"] = selected
    fold_audit[-1]["Best_Parameters"] = best


metrics = pd.DataFrame(metric_rows)
tuning = pd.DataFrame(tuning_rows)
predictions = pd.concat(prediction_parts, ignore_index=True) if prediction_parts else pd.DataFrame()
coefficients = pd.DataFrame(coefficient_rows)

test_metrics = metrics[metrics["Split"].eq("Test")].copy()
summary = test_metrics.groupby("Model", as_index=False).agg(
    Folds=("Fold", "nunique"),
    Mean_PR_AUC=("PR_AUC", "mean"),
    SD_PR_AUC=("PR_AUC", "std"),
    Minimum_PR_AUC=("PR_AUC", "min"),
    Maximum_PR_AUC=("PR_AUC", "max"),
    Mean_Precision_at_10Pct=("Precision", "mean"),
    Mean_Recall_at_10Pct=("Recall", "mean"),
    Mean_Lift_at_10Pct=("Lift", "mean"),
)

if not test_metrics.empty:
    winners = test_metrics.loc[test_metrics.groupby("Fold")["PR_AUC"].idxmax(), ["Fold", "Model"]]
    win_counts = winners["Model"].value_counts()
    summary["Fold_Wins"] = summary["Model"].map(win_counts).fillna(0).astype(int)

for frame in [metrics, tuning, predictions, coefficients]:
    for col in ["Prediction_Date", "Target_Date"]:
        if col in frame:
            frame[col] = pd.to_datetime(frame[col]).dt.strftime("%Y-%m-%d")

metrics.to_csv(METRICS_CSV, index=False, float_format="%.17g")
tuning.to_csv(TUNING_CSV, index=False, float_format="%.17g")
# Preserve near-tied tree probabilities so recomputed ranking metrics are exact.
predictions.to_csv(PREDICTIONS_CSV, index=False, float_format="%.17g")
coefficients.to_csv(COEFFICIENTS_CSV, index=False, float_format="%.17g")

metrics_clean = metrics.replace([np.inf, -np.inf], np.nan)
summary_clean = summary.replace([np.inf, -np.inf], np.nan)
result = {
    "analysis": "Purged expanding-window walk-forward evaluation",
    "fold_audit": fold_audit,
    "metrics": metrics_clean.astype(object).where(pd.notna(metrics_clean), None).to_dict("records"),
    "test_stability_summary": summary_clean.astype(object).where(pd.notna(summary_clean), None).to_dict("records"),
    "tuning_csv": str(TUNING_CSV.relative_to(ROOT)),
    "predictions_csv": str(PREDICTIONS_CSV.relative_to(ROOT)),
    "standardized_logistic_coefficients_csv": str(COEFFICIENTS_CSV.relative_to(ROOT)),
}
RESULTS_JSON.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

# Figure 1: test PR-AUC by fold.
order = ["Historical Prevalence", "Current Absolute Gap", "Current Gap Ratio",
         "Previous Event Persistence", "Logistic Regression", "Decision Tree", "Random Forest"]
plot = test_metrics.pivot(index="Fold", columns="Model", values="PR_AUC").reindex(columns=order)
ax = plot.plot(kind="bar", figsize=(11, 5.4), width=0.82, color=["#A5A5A5", "#5B9BD5", "#1F4E78", "#9EADBA", "#4472C4", "#70AD47", "#ED7D31"])
ax.set_title("Purged walk-forward test PR-AUC", pad=58)
ax.set_ylabel("PR-AUC"); ax.set_xlabel(""); ax.grid(axis="y", alpha=.25)
ax.legend(frameon=False, ncol=4, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, 1.16))
plt.xticks(rotation=0); plt.tight_layout()
plt.savefig(FIG / "ETF_Walk_Forward_PR_AUC.png", dpi=220, bbox_inches="tight"); plt.close()

# Figure 2: mean and range across test folds.
s = summary.sort_values("Mean_PR_AUC", ascending=True)
lower = s["Mean_PR_AUC"] - s["Minimum_PR_AUC"]
upper = s["Maximum_PR_AUC"] - s["Mean_PR_AUC"]
fig, ax = plt.subplots(figsize=(8.2, 4.8))
ax.errorbar(s["Mean_PR_AUC"], s["Model"], xerr=[lower, upper], fmt="o", color="#1F4E78", ecolor="#7F8C8D", capsize=4)
ax.set_title("Walk-forward PR-AUC stability: mean and observed range")
ax.set_xlabel("Test PR-AUC"); ax.grid(axis="x", alpha=.25)
fig.tight_layout(); fig.savefig(FIG / "ETF_Walk_Forward_Stability.png", dpi=220, bbox_inches="tight"); plt.close(fig)

print(json.dumps({"fold_audit": fold_audit, "test_stability_summary": result["test_stability_summary"]}, indent=2, default=str))
