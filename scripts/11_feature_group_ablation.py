"""Prespecified feature-group ablation with purged walk-forward evaluation.

Each classifier is retuned on validation PR-AUC for every feature group and
fold. Test outcomes never enter preprocessing, hyperparameter selection or
feature-group construction.
"""
from __future__ import annotations

from pathlib import Path
import json
import math
import warnings

import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter, MaxNLocator
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier


warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = ROOT / "outputs"
FIG = ROOT / "figures"
INPUT = DATA / "ETF_Modeling_Dataset_Leakage_Safe_2021_to_2026.csv"
METRICS_CSV = OUT / "ETF_Feature_Ablation_Metrics.csv"
SUMMARY_CSV = OUT / "ETF_Feature_Ablation_Summary.csv"
DELTAS_CSV = OUT / "ETF_Feature_Ablation_Deltas.csv"
TUNING_CSV = OUT / "ETF_Feature_Ablation_Tuning.csv"
RESULTS_JSON = OUT / "feature_ablation_results.json"

target = "Y_Abnormal_Dislocation_95Q"
folds = [
    {"Fold": "Fold 1", "Train_End": "2022-12-31", "Validation_Year": 2023, "Test_Year": 2024},
    {"Fold": "Fold 2", "Train_End": "2023-12-31", "Validation_Year": 2024, "Test_Year": 2025},
    {"Fold": "Fold 3", "Train_End": "2024-12-31", "Validation_Year": 2025, "Test_Year": 2026},
]

gap_only = [
    "X_Dislocation_Pct_t", "X_Abs_Dislocation_Pct_t", "X_Dislocation_Lag_1_Pct",
    "X_Dislocation_Lag_2_Pct", "X_Dislocation_Lag_5_Pct", "X_Premium_Flag_t",
]
gap_history_add = [
    "X_Abs_Dislocation_Mean_5D_Pct", "X_Abs_Dislocation_Mean_20D_Pct",
    "X_Abs_Dislocation_Std_20D_Pct", "X_Current_Abs_Gap_to_Threshold_Ratio",
]
market_stress_add = [
    "X_NIFTY50_Return_1D_Pct", "X_NIFTY50_Return_5D_Pct", "X_INDIA_VIX_Close_t",
    "X_INDIA_VIX_Change_1D_Pct", "X_VIX_Change_5D_Pct",
]
liquidity_add = [
    "X_Log_ETF_Volume_t", "X_Volume_to_20D_Median", "X_Log_ETF_Turnover_t",
    "X_Average_Trade_Value_INR_t", "X_Delivery_Pct_t", "X_Intraday_Range_Pct_t",
]

df = pd.read_csv(INPUT, parse_dates=["Prediction_Date", "Target_Date"])
all_features = [c for c in df.columns if c.startswith("X_")]
assert len(all_features) == 25
feature_groups = {
    "Gap Only": gap_only,
    "Gap History": gap_only + gap_history_add,
    "Gap + Market Stress": gap_only + gap_history_add + market_stress_add,
    "Gap + Liquidity": gap_only + gap_history_add + liquidity_add,
    "Full 25 Predictors": all_features,
}
for name, cols in feature_groups.items():
    assert len(cols) == len(set(cols)) and set(cols).issubset(all_features), name


def purge_prior(prior, following):
    if prior.empty or following.empty:
        return prior.copy(), 0
    first_next_prediction = following["Prediction_Date"].min()
    keep = prior["Target_Date"] < first_next_prediction
    return prior.loc[keep].copy(), int((~keep).sum())


def tie_adjusted_budget(y, score, budget=0.10):
    y = np.asarray(y, dtype=int)
    score = np.asarray(score, dtype=float)
    k = max(1, int(math.ceil(len(y) * budget)))
    order = np.argsort(-score, kind="stable")
    cutoff = score[order[k - 1]]
    above, tied = score > cutoff, score == cutoff
    slots = k - int(above.sum())
    expected_tp = float(y[above].sum() + slots * y[tied].mean())
    precision = expected_tp / k
    prevalence = float(y.mean())
    return {
        "Alerts_at_10Pct": k,
        "Expected_TP_at_10Pct": expected_tp,
        "Precision_at_10Pct": precision,
        "Recall_at_10Pct": expected_tp / max(1, int(y.sum())),
        "Lift_at_10Pct": precision / prevalence if prevalence else None,
        "Cutoff_Tie_Rows": int(tied.sum()),
    }


def metric_row(group, feature_count, fold, model, split, y, p):
    y = np.asarray(y, dtype=int)
    p = np.asarray(p, dtype=float)
    row = {
        "Feature_Group": group, "Feature_Count": feature_count, "Fold": fold,
        "Model": model, "Split": split, "Observations": int(len(y)),
        "Events": int(y.sum()), "Event_Rate": float(y.mean()),
        "PR_AUC": float(average_precision_score(y, p)),
        "ROC_AUC": float(roc_auc_score(y, p)),
        "Brier_Score": float(brier_score_loss(y, np.clip(p, 1e-6, 1 - 1e-6))),
    }
    row.update(tie_adjusted_budget(y, p))
    return row


def fit_models(train, valid, features, group, fold, tuning_rows):
    Xtr, ytr = train[features], train[target].astype(int)
    Xva, yva = valid[features], valid[target].astype(int)
    chosen = {}

    candidates = []
    for c in [0.01, 0.1, 1.0, 10.0]:
        model = Pipeline([
            ("scale", StandardScaler()),
            ("model", LogisticRegression(C=c, penalty="l2", solver="liblinear", max_iter=5000, random_state=42)),
        ])
        model.fit(Xtr, ytr); p = model.predict_proba(Xva)[:, 1]
        row = {"Feature_Group": group, "Fold": fold, "Model": "Logistic Regression", "Parameters": f"C={c}",
               "Validation_PR_AUC": float(average_precision_score(yva, p)), "Validation_Brier": float(brier_score_loss(yva, p))}
        tuning_rows.append(row); candidates.append((row, model))
    _, chosen["Logistic Regression"] = max(candidates, key=lambda x: (x[0]["Validation_PR_AUC"], -x[0]["Validation_Brier"]))

    candidates = []
    for depth in [2, 3, 4, 5]:
        for leaf in [10, 25, 50]:
            for weight in [None, "balanced"]:
                model = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=leaf, class_weight=weight, random_state=42)
                model.fit(Xtr, ytr); p = model.predict_proba(Xva)[:, 1]
                row = {"Feature_Group": group, "Fold": fold, "Model": "Decision Tree",
                       "Parameters": f"depth={depth}; leaf={leaf}; weight={weight}",
                       "Validation_PR_AUC": float(average_precision_score(yva, p)), "Validation_Brier": float(brier_score_loss(yva, p))}
                tuning_rows.append(row); candidates.append((row, model))
    _, chosen["Decision Tree"] = max(candidates, key=lambda x: (x[0]["Validation_PR_AUC"], -x[0]["Validation_Brier"]))

    candidates = []
    for depth in [3, 5, None]:
        for leaf in [5, 10, 20]:
            for max_features in ["sqrt", 0.5]:
                for weight in [None, "balanced_subsample"]:
                    model = RandomForestClassifier(
                        n_estimators=400, max_depth=depth, min_samples_leaf=leaf,
                        max_features=max_features, class_weight=weight, random_state=42, n_jobs=-1,
                    )
                    model.fit(Xtr, ytr); p = model.predict_proba(Xva)[:, 1]
                    row = {"Feature_Group": group, "Fold": fold, "Model": "Random Forest",
                           "Parameters": f"depth={depth}; leaf={leaf}; max_features={max_features}; weight={weight}",
                           "Validation_PR_AUC": float(average_precision_score(yva, p)), "Validation_Brier": float(brier_score_loss(yva, p))}
                    tuning_rows.append(row); candidates.append((row, model))
    _, chosen["Random Forest"] = max(candidates, key=lambda x: (x[0]["Validation_PR_AUC"], -x[0]["Validation_Brier"]))
    return chosen


metric_rows, tuning_rows, audit_rows = [], [], []
for group, features in feature_groups.items():
    for spec in folds:
        fold = spec["Fold"]
        train = df[df["Target_Date"] <= pd.Timestamp(spec["Train_End"])].copy()
        valid = df[df["Target_Date"].dt.year.eq(spec["Validation_Year"])].copy()
        test = df[df["Target_Date"].dt.year.eq(spec["Test_Year"])].copy()
        train, purge_train = purge_prior(train, valid)
        valid, purge_valid = purge_prior(valid, test)
        feasible = all(part[target].nunique() == 2 for part in [train, valid, test])
        audit_rows.append({
            "Feature_Group": group, "Feature_Count": len(features), "Fold": fold,
            "Train_Rows": len(train), "Train_Events": int(train[target].sum()),
            "Validation_Rows": len(valid), "Validation_Events": int(valid[target].sum()),
            "Test_Rows": len(test), "Test_Events": int(test[target].sum()),
            "Purged_Train_Rows": purge_train, "Purged_Validation_Rows": purge_valid,
            "Feasible": feasible,
        })
        if not feasible:
            continue
        models = fit_models(train, valid, features, group, fold, tuning_rows)
        for split, part in [("Validation", valid), ("Test", test)]:
            y = part[target].astype(int).to_numpy()
            for model_name, model in models.items():
                p = model.predict_proba(part[features])[:, 1]
                metric_rows.append(metric_row(group, len(features), fold, model_name, split, y, p))

metrics = pd.DataFrame(metric_rows)
tuning = pd.DataFrame(tuning_rows)
audit = pd.DataFrame(audit_rows)
test = metrics[metrics["Split"].eq("Test")].copy()
summary = test.groupby(["Feature_Group", "Feature_Count", "Model"], as_index=False).agg(
    Folds=("Fold", "nunique"), Mean_PR_AUC=("PR_AUC", "mean"),
    Minimum_PR_AUC=("PR_AUC", "min"), Maximum_PR_AUC=("PR_AUC", "max"),
    Mean_ROC_AUC=("ROC_AUC", "mean"), Mean_Brier=("Brier_Score", "mean"),
    Mean_Precision_at_10Pct=("Precision_at_10Pct", "mean"),
    Mean_Recall_at_10Pct=("Recall_at_10Pct", "mean"), Mean_Lift_at_10Pct=("Lift_at_10Pct", "mean"),
)
summary["PR_AUC_Rank_within_Model"] = summary.groupby("Model")["Mean_PR_AUC"].rank(method="min", ascending=False).astype(int)

baseline = summary[summary["Feature_Group"].eq("Gap History")][
    ["Model", "Mean_PR_AUC", "Mean_Brier", "Mean_Precision_at_10Pct"]
].rename(columns={
    "Mean_PR_AUC": "Gap_History_PR_AUC", "Mean_Brier": "Gap_History_Brier",
    "Mean_Precision_at_10Pct": "Gap_History_Precision_at_10Pct",
})
deltas = summary.merge(baseline, on="Model", how="left")
deltas["PR_AUC_Delta_vs_Gap_History"] = deltas["Mean_PR_AUC"] - deltas["Gap_History_PR_AUC"]
deltas["Brier_Improvement_vs_Gap_History"] = deltas["Gap_History_Brier"] - deltas["Mean_Brier"]
deltas["Precision_Delta_vs_Gap_History"] = deltas["Mean_Precision_at_10Pct"] - deltas["Gap_History_Precision_at_10Pct"]

# Transparent reference recomputed on the same test folds.
gap_reference = []
for spec in folds:
    part = df[df["Target_Date"].dt.year.eq(spec["Test_Year"])]
    gap_reference.append(float(average_precision_score(part[target], part["X_Current_Abs_Gap_to_Threshold_Ratio"])))
gap_reference_mean = float(np.mean(gap_reference))

metrics.to_csv(METRICS_CSV, index=False, float_format="%.17g")
summary.to_csv(SUMMARY_CSV, index=False, float_format="%.17g")
deltas.to_csv(DELTAS_CSV, index=False, float_format="%.17g")
tuning.to_csv(TUNING_CSV, index=False, float_format="%.17g")
audit.to_csv(OUT / "ETF_Feature_Ablation_Fold_Audit.csv", index=False)

clean = lambda d: d.astype(object).where(pd.notna(d), None).to_dict("records")
result = {
    "analysis": "Feature-group ablation with validation-only retuning in each walk-forward fold",
    "feature_groups": feature_groups,
    "current_gap_ratio_reference_mean_pr_auc": gap_reference_mean,
    "current_gap_ratio_reference_fold_pr_auc": gap_reference,
    "fold_audit": clean(audit), "test_summary": clean(summary), "deltas_vs_gap_history": clean(deltas),
}
RESULTS_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")

group_order = list(feature_groups)
model_order = ["Logistic Regression", "Decision Tree", "Random Forest"]
plot = summary.pivot(index="Feature_Group", columns="Model", values="Mean_PR_AUC").reindex(group_order)[model_order]
ax = plot.plot(kind="bar", figsize=(11, 5.5), color=["#4472C4", "#70AD47", "#ED7D31"], width=.78)
ax.axhline(gap_reference_mean, color="#1F4E78", linestyle="--", linewidth=1.5, label="Current gap ratio reference")
ax.set_title("Feature-group ablation: mean walk-forward test PR-AUC")
ax.set_ylabel("Mean test PR-AUC"); ax.set_xlabel(""); ax.tick_params(axis="x", rotation=15)
ax.grid(axis="y", alpha=.25); ax.legend(frameon=False, ncol=2, fontsize=8)
fig = ax.get_figure(); fig.tight_layout(); fig.savefig(FIG / "ETF_Feature_Ablation_PR_AUC.png", dpi=220, bbox_inches="tight"); plt.close(fig)

fig, axes = plt.subplots(1, 3, figsize=(12.2, 4.4), sharey=True)
for ax, model in zip(axes, model_order):
    p = deltas[deltas["Model"].eq(model)].set_index("Feature_Group").reindex(group_order)
    colors = ["#70AD47" if x >= 0 else "#C0504D" for x in p["PR_AUC_Delta_vs_Gap_History"]]
    ax.barh(group_order, p["PR_AUC_Delta_vs_Gap_History"], color=colors)
    ax.axvline(0, color="#7F7F7F", linewidth=1); ax.set_title(model); ax.grid(axis="x", alpha=.2)
    ax.xaxis.set_major_locator(MaxNLocator(nbins=5)); ax.xaxis.set_major_formatter(FormatStrFormatter("%.3f"))
    ax.tick_params(axis="x", labelsize=9)
axes[0].set_xlabel("PR-AUC difference vs gap history")
fig.suptitle("Incremental value relative to gap-history features", y=1.02)
fig.tight_layout(); fig.savefig(FIG / "ETF_Feature_Ablation_Deltas.png", dpi=220, bbox_inches="tight"); plt.close(fig)

best = summary.loc[summary.groupby("Model")["Mean_PR_AUC"].idxmax(), ["Model", "Feature_Group", "Mean_PR_AUC"]]
print(json.dumps({
    "gap_ratio_reference_mean_pr_auc": gap_reference_mean,
    "best_group_by_model": best.to_dict("records"),
    "market_stress_deltas": deltas[deltas["Feature_Group"].eq("Gap + Market Stress")][["Model", "PR_AUC_Delta_vs_Gap_History", "Brier_Improvement_vs_Gap_History"]].to_dict("records"),
    "liquidity_deltas": deltas[deltas["Feature_Group"].eq("Gap + Liquidity")][["Model", "PR_AUC_Delta_vs_Gap_History", "Brier_Improvement_vs_Gap_History"]].to_dict("records"),
}, indent=2))
