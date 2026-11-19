"""Prespecified temporal-shift diagnostics for the enhanced ETF study.

Implements Section 13 of docs/ANALYSIS_PLAN_V2.md. Only validation-selected
walk-forward specifications are refitted. Test outcomes do not influence model
fitting or the locked alert cutoffs.
"""
from __future__ import annotations

from pathlib import Path
import json
import math
import re
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier


warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
DATA, OUT, FIG = ROOT / "data" / "processed", ROOT / "outputs", ROOT / "figures"
OUT.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True)
INPUT = DATA / "ETF_Modeling_Dataset_Leakage_Safe_2021_to_2026.csv"
TUNING = OUT / "ETF_Walk_Forward_Tuning.csv"
TARGET = "Y_Abnormal_Dislocation_95Q"

FILES = {
    "year": OUT / "ETF_Temporal_Shift_Year_Summary.csv",
    "model": OUT / "ETF_Temporal_Shift_Model_Metrics.csv",
    "calibration": OUT / "ETF_Temporal_Shift_Calibration.csv",
    "locked": OUT / "ETF_Temporal_Shift_Locked_Alerts.csv",
    "feature_psi": OUT / "ETF_Temporal_Shift_Feature_PSI.csv",
    "score_psi": OUT / "ETF_Temporal_Shift_Score_PSI.csv",
    "json": OUT / "temporal_shift_results.json",
}

PROBABILITY_MODELS = {"Historical Prevalence", "Logistic Regression", "Decision Tree", "Random Forest"}
MODEL_ORDER = ["Historical Prevalence", "Current Absolute Gap", "Current Gap Ratio",
               "Previous Event Persistence", "Logistic Regression", "Decision Tree", "Random Forest"]
FOLDS = [
    {"Fold": "Fold 1", "Train_End": "2022-12-31", "Validation_Year": 2023, "Test_Year": 2024},
    {"Fold": "Fold 2", "Train_End": "2023-12-31", "Validation_Year": 2024, "Test_Year": 2025},
    {"Fold": "Fold 3", "Train_End": "2024-12-31", "Validation_Year": 2025, "Test_Year": 2026},
]


def purge_prior(prior, following):
    if prior.empty or following.empty:
        return prior.copy()
    return prior.loc[prior["Target_Date"] < following["Prediction_Date"].min()].copy()


def selected_parameter(tuning, fold, model):
    rows = tuning[(tuning["Fold"] == fold) & (tuning["Model"] == model)].copy()
    return str(rows.sort_values(["Validation_PR_AUC", "Validation_Brier"],
                                ascending=[False, True]).iloc[0]["Parameters"])


def make_model(name, parameters):
    if name == "Logistic Regression":
        c = float(parameters.split("=")[1])
        return Pipeline([("scale", StandardScaler()),
                         ("model", LogisticRegression(C=c, penalty="l2", solver="liblinear",
                                                      max_iter=5000, random_state=42))])
    fields = dict(part.split("=", 1) for part in parameters.split("; "))
    depth = None if fields["depth"] == "None" else int(fields["depth"])
    weight = None if fields["weight"] == "None" else fields["weight"]
    if name == "Decision Tree":
        return DecisionTreeClassifier(max_depth=depth, min_samples_leaf=int(fields["leaf"]),
                                      class_weight=weight, random_state=42)
    max_features = fields["max_features"]
    if re.fullmatch(r"\d+(\.\d+)?", max_features):
        max_features = float(max_features)
    return RandomForestClassifier(n_estimators=400, max_depth=depth,
                                  min_samples_leaf=int(fields["leaf"]), max_features=max_features,
                                  class_weight=weight, random_state=42, n_jobs=-1)


def five_bin_ece(y, p):
    work = pd.DataFrame({"y": y, "p": p})
    try:
        work["bin"] = pd.qcut(work["p"], q=5, duplicates="drop")
    except ValueError:
        return float(abs(work["y"].mean() - work["p"].mean()))
    if work["bin"].notna().sum() == 0:
        return float(abs(work["y"].mean() - work["p"].mean()))
    return float(sum(len(g) / len(work) * abs(g["y"].mean() - g["p"].mean())
                     for _, g in work.groupby("bin", observed=True)))


def calibration_stats(y, p):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6); y = np.asarray(y, int)
    mean_p, rate = float(p.mean()), float(y.mean())
    cil = float(np.log(rate / (1 - rate)) - np.log(mean_p / (1 - mean_p)))
    if np.ptp(p) < 1e-12:
        intercept, slope = cil, None
    else:
        logits = np.log(p / (1 - p)).reshape(-1, 1)
        recal = LogisticRegression(penalty=None, solver="lbfgs", max_iter=5000).fit(logits, y)
        intercept, slope = float(recal.intercept_[0]), float(recal.coef_[0, 0])
    return {"Mean_Predicted_Probability": mean_p, "Observed_Event_Rate": rate,
            "Calibration_in_the_Large": cil, "Calibration_Intercept": intercept,
            "Calibration_Slope": slope, "Five_Bin_ECE": five_bin_ece(y, p),
            "Brier_Score": float(brier_score_loss(y, p))}


def psi(reference, current, bins=10):
    reference, current = np.asarray(reference, float), np.asarray(current, float)
    reference, current = reference[np.isfinite(reference)], current[np.isfinite(current)]
    if not len(reference) or not len(current):
        return float("nan")
    edges = np.unique(np.quantile(reference, np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:
        lo, hi = min(reference.min(), current.min()), max(reference.max(), current.max())
        if lo == hi:
            return 0.0
        edges = np.linspace(lo, hi, min(bins, 5) + 1)
    edges[0], edges[-1] = -np.inf, np.inf
    ref = np.clip(np.histogram(reference, bins=edges)[0] / len(reference), 1e-6, None)
    cur = np.clip(np.histogram(current, bins=edges)[0] / len(current), 1e-6, None)
    return float(np.sum((cur - ref) * np.log(cur / ref)))


def severity(value):
    if not np.isfinite(value): return "Unavailable"
    if value < .10: return "Low"
    if value < .25: return "Moderate"
    return "Large"


df = pd.read_csv(INPUT, parse_dates=["Prediction_Date", "Target_Date"])
tuning = pd.read_csv(TUNING)
features = [c for c in df.columns if c.startswith("X_")]
year_rows, model_rows, calibration_rows, locked_rows, feature_psi_rows, score_psi_rows = [], [], [], [], [], []

for spec in FOLDS:
    fold = spec["Fold"]
    train = df[df["Target_Date"] <= pd.Timestamp(spec["Train_End"])].copy()
    valid = df[df["Target_Date"].dt.year.eq(spec["Validation_Year"])].copy()
    test = df[df["Target_Date"].dt.year.eq(spec["Test_Year"])].copy()
    train, valid = purge_prior(train, valid), purge_prior(valid, test)
    Xtr, ytr = train[features], train[TARGET].astype(int).to_numpy()
    yva, yte = valid[TARGET].astype(int).to_numpy(), test[TARGET].astype(int).to_numpy()
    models = {}
    for name in ["Logistic Regression", "Decision Tree", "Random Forest"]:
        model = make_model(name, selected_parameter(tuning, fold, name)).fit(Xtr, ytr)
        models[name] = model
    prevalence = float(ytr.mean())

    def get_scores(part):
        result = {
            "Historical Prevalence": np.repeat(prevalence, len(part)),
            "Current Absolute Gap": part["X_Abs_Dislocation_Pct_t"].to_numpy(float),
            "Current Gap Ratio": part["X_Current_Abs_Gap_to_Threshold_Ratio"].to_numpy(float),
            "Previous Event Persistence": (part["X_Abs_Dislocation_Pct_t"] >
                                           part["Rolling_Threshold_95Pct"]).astype(float).to_numpy(),
        }
        for name, model in models.items(): result[name] = model.predict_proba(part[features])[:, 1]
        return result

    va_scores, te_scores = get_scores(valid), get_scores(test)
    abs_target = test["Target_Abs_Dislocation_Pct"].to_numpy(float)
    year_rows.append({"Fold": fold, "Test_Year": spec["Test_Year"], "Observations": len(test),
                      "Events": int(yte.sum()), "Event_Rate": float(yte.mean()),
                      "Mean_Abs_Dislocation_Pct": float(np.mean(abs_target)),
                      "Median_Abs_Dislocation_Pct": float(np.median(abs_target)),
                      "P95_Abs_Dislocation_Pct": float(np.quantile(abs_target, .95)),
                      "Maximum_Abs_Dislocation_Pct": float(np.max(abs_target))})

    for name in MODEL_ORDER:
        score, valid_score = te_scores[name], va_scores[name]
        model_rows.append({"Fold": fold, "Test_Year": spec["Test_Year"], "Model": name,
                           "Observations": len(test), "Events": int(yte.sum()),
                           "Event_Rate": float(yte.mean()),
                           "PR_AUC": float(average_precision_score(yte, score)),
                           "ROC_AUC": float(roc_auc_score(yte, score)),
                           "Mean_Score": float(np.mean(score)), "Score_SD": float(np.std(score, ddof=1))})
        if name in PROBABILITY_MODELS:
            calibration_rows.append({"Fold": fold, "Test_Year": spec["Test_Year"], "Model": name,
                                     **calibration_stats(yte, score)})
        k = max(1, int(math.ceil(.10 * len(valid_score))))
        cutoff = float(np.sort(valid_score)[::-1][k - 1])
        alert = score >= cutoff; tp = int(np.sum(alert & (yte == 1)))
        locked_rows.append({"Fold": fold, "Validation_Year": spec["Validation_Year"],
                            "Test_Year": spec["Test_Year"], "Model": name,
                            "Validation_Locked_Cutoff": cutoff, "Test_Alerts": int(alert.sum()),
                            "Test_Alert_Rate": float(alert.mean()),
                            "Alert_Rate_Deviation_from_10Pct": float(alert.mean() - .10),
                            "Test_True_Positives": tp,
                            "Test_Precision": float(tp / alert.sum()) if alert.sum() else None,
                            "Test_Recall": float(tp / yte.sum()) if yte.sum() else None})
        value = psi(valid_score, score)
        score_psi_rows.append({"Fold": fold, "Validation_Year": spec["Validation_Year"],
                               "Test_Year": spec["Test_Year"], "Model": name,
                               "Score_PSI": value, "PSI_Severity": severity(value)})
    for feature in features:
        value = psi(valid[feature], test[feature])
        feature_psi_rows.append({"Fold": fold, "Validation_Year": spec["Validation_Year"],
                                 "Test_Year": spec["Test_Year"], "Feature": feature,
                                 "Feature_PSI": value, "PSI_Severity": severity(value)})

year_summary, model_metrics = pd.DataFrame(year_rows), pd.DataFrame(model_rows)
calibration, locked = pd.DataFrame(calibration_rows), pd.DataFrame(locked_rows)
feature_psi, score_psi = pd.DataFrame(feature_psi_rows), pd.DataFrame(score_psi_rows)
model_metrics["PR_AUC_Rank"] = model_metrics.groupby("Fold")["PR_AUC"].rank(method="min", ascending=False).astype(int)

for frame, key in [(year_summary, "year"), (model_metrics, "model"), (calibration, "calibration"),
                   (locked, "locked"), (feature_psi, "feature_psi"), (score_psi, "score_psi")]:
    frame.to_csv(FILES[key], index=False, float_format="%.17g")

feature_fold = feature_psi.groupby(["Fold", "Test_Year"], as_index=False).agg(
    Median_Feature_PSI=("Feature_PSI", "median"), Maximum_Feature_PSI=("Feature_PSI", "max"),
    Features_Moderate_or_Large=("Feature_PSI", lambda s: int((s >= .10).sum())),
    Features_Large=("Feature_PSI", lambda s: int((s >= .25).sum())))
result = {"analysis": "Prespecified temporal-shift and calibration diagnostics",
          "psi_interpretation": {"low": "<0.10", "moderate": "0.10 to <0.25", "large": ">=0.25"},
          "year_summary": year_summary.to_dict("records"),
          "feature_shift_summary": feature_fold.to_dict("records"),
          "model_metrics": model_metrics.to_dict("records"),
          "calibration": calibration.replace({np.nan: None}).to_dict("records"),
          "locked_alerts": locked.replace({np.nan: None}).to_dict("records"),
          "score_psi": score_psi.to_dict("records")}
FILES["json"].write_text(json.dumps(result, indent=2), encoding="utf-8")

sns.set_theme(style="whitegrid")
fig, ax1 = plt.subplots(figsize=(8.6, 4.9)); x = np.arange(len(year_summary))
ax1.bar(x, 100 * year_summary["Event_Rate"], color="#1F4E78", width=.55)
ax1.set_ylabel("Abnormal-event prevalence (%)", color="#1F4E78")
ax1.set_xticks(x, year_summary["Test_Year"].astype(str)); ax1.set_xlabel("Untouched test year")
ax2 = ax1.twinx(); ax2.plot(x, year_summary["P95_Abs_Dislocation_Pct"], color="#ED7D31", marker="o", linewidth=2.2)
ax2.set_ylabel("95th percentile absolute dislocation (%)", color="#C65911")
ax1.set_title("Outcome regime changes across walk-forward test years")
fig.tight_layout(); fig.savefig(FIG / "ETF_Temporal_Shift_Outcomes.png", dpi=220, bbox_inches="tight"); plt.close(fig)

heat = model_metrics.pivot(index="Model", columns="Test_Year", values="PR_AUC").reindex(MODEL_ORDER)
fig, ax = plt.subplots(figsize=(7.3, 5.4)); sns.heatmap(heat, annot=True, fmt=".3f", cmap="Blues",
                                                         linewidths=.5, cbar_kws={"label": "PR-AUC"}, ax=ax)
ax.set_title("Model ranking changes across test years"); ax.set_xlabel("Test year"); ax.set_ylabel("")
fig.tight_layout(); fig.savefig(FIG / "ETF_Temporal_Shift_PR_AUC.png", dpi=220, bbox_inches="tight"); plt.close(fig)

plot_cal = calibration[calibration["Model"].ne("Historical Prevalence")]
fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.8), sharex=True, sharey=True)
for ax, (model, part) in zip(axes, plot_cal.groupby("Model", sort=False)):
    ax.plot([0, .20], [0, .20], linestyle="--", color="#7F8C8D", linewidth=1)
    for _, row in part.iterrows():
        ax.scatter(row["Observed_Event_Rate"], row["Mean_Predicted_Probability"], s=65)
        ax.annotate(str(int(row["Test_Year"])), (row["Observed_Event_Rate"], row["Mean_Predicted_Probability"]),
                    xytext=(5, 4), textcoords="offset points", fontsize=8)
    ax.set_title(model); ax.set_xlabel("Observed event rate")
axes[0].set_ylabel("Mean predicted probability")
fig.suptitle("Probability calibration shifts by test year", y=1.03)
fig.tight_layout(); fig.savefig(FIG / "ETF_Temporal_Shift_Calibration.png", dpi=220, bbox_inches="tight"); plt.close(fig)

plot_locked = locked[~locked["Model"].isin(["Historical Prevalence", "Previous Event Persistence"])]
fig, ax = plt.subplots(figsize=(9.4, 5.0))
sns.lineplot(data=plot_locked, x="Test_Year", y="Test_Alert_Rate", hue="Model", marker="o", ax=ax)
ax.axhline(.10, linestyle="--", color="#7F8C8D", label="Intended 10% rate")
ax.set_ylabel("Test alert rate"); ax.set_xlabel("Test year")
ax.set_title("Validation-locked cutoffs do not preserve alert volume")
ax.set_xticks([2024, 2025, 2026], ["2024", "2025", "2026"])
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}"); ax.legend(frameon=False, fontsize=8, ncol=2)
fig.tight_layout(); fig.savefig(FIG / "ETF_Temporal_Shift_Locked_Alerts.png", dpi=220, bbox_inches="tight"); plt.close(fig)

print(json.dumps({"year_summary": result["year_summary"],
                  "feature_shift_summary": result["feature_shift_summary"],
                  "largest_locked_alert_deviations": locked.loc[~locked["Model"].eq("Historical Prevalence")]
                  .assign(abs_dev=lambda d: d["Alert_Rate_Deviation_from_10Pct"].abs())
                  .nlargest(8, "abs_dev")[["Fold", "Test_Year", "Model", "Test_Alert_Rate",
                                            "Alert_Rate_Deviation_from_10Pct"]].to_dict("records")}, indent=2))
