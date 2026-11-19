"""Prespecified abnormal-event label sensitivity analysis.

Re-runs the purged walk-forward pipeline for rolling 90th, 95th and 97.5th
percentile labels, and audits feasibility for fixed 0.50% and 1.00% labels.
Every rolling threshold uses the 252 complete observations ending on prediction
date t, so the target date never contributes to its own label threshold.
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
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
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

MODEL_INPUT = DATA / "ETF_Modeling_Dataset_Leakage_Safe_2021_to_2026.csv"
MASTER_INPUT = DATA / "ETF_Master_Merged_2021_to_2026.csv"
METRICS_CSV = OUT / "ETF_Label_Sensitivity_Metrics.csv"
SUMMARY_CSV = OUT / "ETF_Label_Sensitivity_Summary.csv"
AUDIT_CSV = OUT / "ETF_Label_Sensitivity_Feasibility.csv"
TUNING_CSV = OUT / "ETF_Label_Sensitivity_Tuning.csv"
RESULTS_JSON = OUT / "label_sensitivity_results.json"

folds = [
    {"Fold": "Fold 1", "Train_End": "2022-12-31", "Validation_Year": 2023, "Test_Year": 2024},
    {"Fold": "Fold 2", "Train_End": "2023-12-31", "Validation_Year": 2024, "Test_Year": 2025},
    {"Fold": "Fold 3", "Train_End": "2024-12-31", "Validation_Year": 2025, "Test_Year": 2026},
]

scenarios = [
    {"Label_Key": "Rolling_90Q", "Label": "Rolling 90th percentile", "kind": "rolling", "value": 0.90},
    {"Label_Key": "Rolling_95Q", "Label": "Rolling 95th percentile", "kind": "rolling", "value": 0.95},
    {"Label_Key": "Rolling_97_5Q", "Label": "Rolling 97.5th percentile", "kind": "rolling", "value": 0.975},
    {"Label_Key": "Fixed_0_50", "Label": "Fixed 0.50%", "kind": "fixed", "value": 0.50},
    {"Label_Key": "Fixed_1_00", "Label": "Fixed 1.00%", "kind": "fixed", "value": 1.00},
]


def purge_prior(prior: pd.DataFrame, following: pd.DataFrame):
    if prior.empty or following.empty:
        return prior.copy(), 0
    first_next_prediction = following["Prediction_Date"].min()
    keep = prior["Target_Date"] < first_next_prediction
    return prior.loc[keep].copy(), int((~keep).sum())


def top_budget(y, score, budget=0.10):
    y = np.asarray(y, dtype=int)
    score = np.asarray(score, dtype=float)
    k = max(1, int(math.ceil(len(y) * budget)))
    order = np.argsort(-score, kind="stable")
    alert = np.zeros(len(y), dtype=int)
    alert[order[:k]] = 1
    tp = int(((alert == 1) & (y == 1)).sum())
    prevalence = float(y.mean())
    return {
        "Alerts": k,
        "True_Positives": tp,
        "Precision": float(tp / k),
        "Recall": float(tp / max(1, y.sum())),
        "Lift": float((tp / k) / prevalence) if prevalence else None,
    }


def no_skill_budget(y, budget=0.10):
    y = np.asarray(y, dtype=int)
    k = max(1, int(math.ceil(len(y) * budget)))
    prevalence = float(y.mean())
    return {
        "Alerts": k,
        "True_Positives": float(k * prevalence),
        "Precision": prevalence,
        "Recall": float(k / len(y)),
        "Lift": 1.0,
    }


def metric_row(label, fold, model, split, y, score, probability=False):
    y = np.asarray(y, dtype=int)
    score = np.asarray(score, dtype=float)
    row = {
        "Label_Definition": label,
        "Fold": fold,
        "Model": model,
        "Split": split,
        "Observations": int(len(y)),
        "Events": int(y.sum()),
        "Event_Rate": float(y.mean()),
        "PR_AUC": float(average_precision_score(y, score)),
        "ROC_AUC": float(roc_auc_score(y, score)) if len(np.unique(y)) > 1 else None,
        "Brier_Score": None,
    }
    if probability:
        row["Brier_Score"] = float(brier_score_loss(y, np.clip(score, 1e-6, 1 - 1e-6)))
    budget = no_skill_budget(y) if model == "Historical Prevalence" else top_budget(y, score)
    row.update(budget)
    return row


def fit_models(train, valid, features, target, label, fold, tuning_rows):
    Xtr, ytr = train[features], train[target].astype(int)
    Xva, yva = valid[features], valid[target].astype(int)
    chosen = {}

    candidates = []
    for c in [0.01, 0.1, 1.0, 10.0]:
        model = Pipeline([
            ("scale", StandardScaler()),
            ("model", LogisticRegression(C=c, penalty="l2", solver="liblinear", max_iter=5000, random_state=42)),
        ])
        model.fit(Xtr, ytr)
        p = model.predict_proba(Xva)[:, 1]
        row = {"Label_Definition": label, "Fold": fold, "Model": "Logistic Regression",
               "Parameters": f"C={c}", "Validation_PR_AUC": float(average_precision_score(yva, p)),
               "Validation_Brier": float(brier_score_loss(yva, p))}
        tuning_rows.append(row); candidates.append((row, model))
    best_row, chosen["Logistic Regression"] = max(
        candidates, key=lambda x: (x[0]["Validation_PR_AUC"], -x[0]["Validation_Brier"])
    )

    candidates = []
    for depth in [2, 3, 4, 5]:
        for leaf in [10, 25, 50]:
            for weight in [None, "balanced"]:
                model = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=leaf,
                                               class_weight=weight, random_state=42)
                model.fit(Xtr, ytr)
                p = model.predict_proba(Xva)[:, 1]
                row = {"Label_Definition": label, "Fold": fold, "Model": "Decision Tree",
                       "Parameters": f"depth={depth}; leaf={leaf}; weight={weight}",
                       "Validation_PR_AUC": float(average_precision_score(yva, p)),
                       "Validation_Brier": float(brier_score_loss(yva, p))}
                tuning_rows.append(row); candidates.append((row, model))
    best_row, chosen["Decision Tree"] = max(
        candidates, key=lambda x: (x[0]["Validation_PR_AUC"], -x[0]["Validation_Brier"])
    )

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
                    row = {"Label_Definition": label, "Fold": fold, "Model": "Random Forest",
                           "Parameters": f"depth={depth}; leaf={leaf}; max_features={max_features}; weight={weight}",
                           "Validation_PR_AUC": float(average_precision_score(yva, p)),
                           "Validation_Brier": float(brier_score_loss(yva, p))}
                    tuning_rows.append(row); candidates.append((row, model))
    best_row, chosen["Random Forest"] = max(
        candidates, key=lambda x: (x[0]["Validation_PR_AUC"], -x[0]["Validation_Brier"])
    )
    return chosen


model_base = pd.read_csv(MODEL_INPUT, parse_dates=["Prediction_Date", "Target_Date"])
master = pd.read_csv(MASTER_INPUT, parse_dates=["Date"]).sort_values("Date")
complete = master.loc[master["Complete_Case"].eq(1), ["Date", "Abs_Dislocation_Pct"]].copy()
for q, col in [(0.90, "Threshold_90Q"), (0.95, "Threshold_95Q"), (0.975, "Threshold_97_5Q")]:
    complete[col] = complete["Abs_Dislocation_Pct"].rolling(252, min_periods=252).quantile(q)
thresholds = complete.drop(columns="Abs_Dislocation_Pct")
model_base = model_base.merge(thresholds, left_on="Prediction_Date", right_on="Date", how="left", validate="one_to_one")
assert np.allclose(model_base["Threshold_95Q"], model_base["Rolling_Threshold_95Pct"], atol=1e-8)

base_features = [c for c in model_base.columns if c.startswith("X_")]
metric_rows, tuning_rows, audit_rows, yearly_rows = [], [], [], []

for scenario in scenarios:
    label = scenario["Label"]
    data = model_base.copy()
    if scenario["kind"] == "rolling":
        threshold_col = {0.90: "Threshold_90Q", 0.95: "Threshold_95Q", 0.975: "Threshold_97_5Q"}[scenario["value"]]
        data["Scenario_Threshold"] = data[threshold_col]
    else:
        data["Scenario_Threshold"] = float(scenario["value"])
    data["Scenario_Target"] = (data["Target_Abs_Dislocation_Pct"] > data["Scenario_Threshold"]).astype(int)
    data["Scenario_Persistence"] = (data["X_Abs_Dislocation_Pct_t"] > data["Scenario_Threshold"]).astype(float)
    # Replace the label-dependent ratio feature so every scenario uses its own frozen threshold.
    data["X_Current_Abs_Gap_to_Threshold_Ratio"] = (
        data["X_Abs_Dislocation_Pct_t"] / data["Scenario_Threshold"]
    )

    for year, part in data.groupby(data["Target_Date"].dt.year):
        yearly_rows.append({"Label_Definition": label, "Target_Year": int(year),
                            "Observations": int(len(part)), "Events": int(part["Scenario_Target"].sum()),
                            "Event_Rate": float(part["Scenario_Target"].mean())})

    for spec in folds:
        fold = spec["Fold"]
        train = data[data["Target_Date"] <= pd.Timestamp(spec["Train_End"])].copy()
        valid = data[data["Target_Date"].dt.year.eq(spec["Validation_Year"])].copy()
        test = data[data["Target_Date"].dt.year.eq(spec["Test_Year"])].copy()
        train, purge_train = purge_prior(train, valid)
        valid, purge_valid = purge_prior(valid, test)
        split_counts = {
            "Train": (len(train), int(train["Scenario_Target"].sum())),
            "Validation": (len(valid), int(valid["Scenario_Target"].sum())),
            "Test": (len(test), int(test["Scenario_Target"].sum())),
        }
        bad = [name for name, (n, events) in split_counts.items() if events == 0 or events == n]
        feasible = not bad
        audit_rows.append({
            "Label_Definition": label, "Fold": fold,
            "Total_Events": int(data["Scenario_Target"].sum()),
            "Train_Rows": split_counts["Train"][0], "Train_Events": split_counts["Train"][1],
            "Validation_Rows": split_counts["Validation"][0], "Validation_Events": split_counts["Validation"][1],
            "Test_Rows": split_counts["Test"][0], "Test_Events": split_counts["Test"][1],
            "Purged_Train_Rows": purge_train, "Purged_Validation_Rows": purge_valid,
            "Feasible": feasible,
            "Reason": "" if feasible else f"No usable class variation in: {', '.join(bad)}",
        })
        if not feasible:
            continue

        models = fit_models(train, valid, base_features, "Scenario_Target", label, fold, tuning_rows)
        train_prevalence = float(train["Scenario_Target"].mean())
        for split_name, part in [("Validation", valid), ("Test", test)]:
            y = part["Scenario_Target"].astype(int).to_numpy()
            scores = {
                "Historical Prevalence": np.repeat(train_prevalence, len(part)),
                "Current Absolute Gap": part["X_Abs_Dislocation_Pct_t"].to_numpy(float),
                "Current Gap Ratio": part["X_Current_Abs_Gap_to_Threshold_Ratio"].to_numpy(float),
                "Previous Event Persistence": part["Scenario_Persistence"].to_numpy(float),
            }
            for name, model in models.items():
                scores[name] = model.predict_proba(part[base_features])[:, 1]
            for name, score in scores.items():
                metric_rows.append(metric_row(
                    label, fold, name, split_name, y, score,
                    probability=name in {"Historical Prevalence", "Logistic Regression", "Decision Tree", "Random Forest"},
                ))

metrics = pd.DataFrame(metric_rows)
audit = pd.DataFrame(audit_rows)
yearly = pd.DataFrame(yearly_rows)
tuning = pd.DataFrame(tuning_rows)

if not metrics.empty:
    test = metrics[metrics["Split"].eq("Test")].copy()
    summary = test.groupby(["Label_Definition", "Model"], as_index=False).agg(
        Feasible_Folds=("Fold", "nunique"),
        Mean_PR_AUC=("PR_AUC", "mean"),
        Minimum_PR_AUC=("PR_AUC", "min"),
        Maximum_PR_AUC=("PR_AUC", "max"),
        Mean_Precision_at_10Pct=("Precision", "mean"),
        Mean_Recall_at_10Pct=("Recall", "mean"),
        Mean_Lift_at_10Pct=("Lift", "mean"),
    )
    summary["Rank_within_Label"] = summary.groupby("Label_Definition")["Mean_PR_AUC"].rank(method="min", ascending=False).astype(int)
else:
    summary = pd.DataFrame()

metrics.to_csv(METRICS_CSV, index=False, float_format="%.17g")
summary.to_csv(SUMMARY_CSV, index=False, float_format="%.17g")
audit.to_csv(AUDIT_CSV, index=False)
tuning.to_csv(TUNING_CSV, index=False, float_format="%.17g")
yearly.to_csv(OUT / "ETF_Label_Sensitivity_Yearly_Events.csv", index=False, float_format="%.17g")

result = {
    "analysis": "Prespecified label-definition sensitivity using the purged walk-forward pipeline",
    "threshold_window": 252,
    "feasibility_rule": "Every train, validation and test partition must contain both outcome classes",
    "feature_rule": "The current-gap ratio and persistence benchmark use each scenario's threshold frozen on prediction date t",
    "feasibility": audit.replace({np.nan: None}).to_dict("records"),
    "yearly_event_counts": yearly.replace({np.nan: None}).to_dict("records"),
    "test_summary": summary.replace({np.nan: None}).to_dict("records"),
}
RESULTS_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")

# Event-count figure for all prespecified definitions.
event_totals = yearly.groupby("Label_Definition", as_index=False)["Events"].sum()
order_labels = [s["Label"] for s in scenarios]
event_totals["Label_Definition"] = pd.Categorical(event_totals["Label_Definition"], order_labels, ordered=True)
event_totals = event_totals.sort_values("Label_Definition")
fig, ax = plt.subplots(figsize=(9.2, 4.8))
bars = ax.bar(event_totals["Label_Definition"].astype(str), event_totals["Events"], color=["#5B9BD5", "#1F4E78", "#4472C4", "#A5A5A5", "#7F7F7F"])
ax.bar_label(bars, padding=3)
ax.set_title("Abnormal-event counts under prespecified label definitions")
ax.set_ylabel("Events in 1,185 modelling observations")
ax.tick_params(axis="x", rotation=18)
ax.grid(axis="y", alpha=.22)
fig.tight_layout(); fig.savefig(FIG / "ETF_Label_Sensitivity_Event_Counts.png", dpi=220, bbox_inches="tight"); plt.close(fig)

# Model ranking plot for feasible rolling labels.
plot_models = ["Current Gap Ratio", "Logistic Regression", "Decision Tree", "Random Forest"]
plot = summary[summary["Model"].isin(plot_models)].pivot(index="Label_Definition", columns="Model", values="Mean_PR_AUC")
plot = plot.reindex([s["Label"] for s in scenarios if s["kind"] == "rolling"])
ax = plot.plot(kind="bar", figsize=(10.2, 5.2), color=["#1F4E78", "#70AD47", "#4472C4", "#ED7D31"], width=.78)
ax.set_title("Mean walk-forward test PR-AUC across label definitions")
ax.set_ylabel("Mean test PR-AUC"); ax.set_xlabel("")
ax.tick_params(axis="x", rotation=0); ax.grid(axis="y", alpha=.22)
ax.legend(frameon=False, ncol=2, loc="upper left")
fig = ax.get_figure(); fig.tight_layout(); fig.savefig(FIG / "ETF_Label_Sensitivity_PR_AUC.png", dpi=220, bbox_inches="tight"); plt.close(fig)

print(json.dumps({
    "event_totals": {str(r.Label_Definition): int(r.Events) for r in event_totals.itertuples()},
    "feasible_folds": audit.groupby("Label_Definition")["Feasible"].sum().astype(int).to_dict(),
    "top_models": summary.loc[summary.groupby("Label_Definition")["Mean_PR_AUC"].idxmax(),
                              ["Label_Definition", "Model", "Mean_PR_AUC"]].to_dict("records") if not summary.empty else [],
}, indent=2))
