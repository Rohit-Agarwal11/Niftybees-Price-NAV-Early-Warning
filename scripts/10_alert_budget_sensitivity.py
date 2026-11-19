"""Operational alert-budget sensitivity for walk-forward test predictions.

Evaluates the highest-scored 5%, 10% and 20% of dates separately within each
test fold. When multiple observations tie at the capacity cutoff, the primary
metrics use the expected number of positives under random selection within the
cutoff tie. A deterministic stable-order count is retained only as an audit.
"""
from __future__ import annotations

from pathlib import Path
import json
import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
FIG = ROOT / "figures"
INPUT = OUT / "ETF_Walk_Forward_Predictions.csv"
FOLD_CSV = OUT / "ETF_Alert_Budget_Fold_Metrics.csv"
SUMMARY_CSV = OUT / "ETF_Alert_Budget_Summary.csv"
RESULTS_JSON = OUT / "alert_budget_sensitivity_results.json"

target = "Y_Abnormal_Dislocation_95Q"
budgets = [0.05, 0.10, 0.20]
model_order = [
    "Historical Prevalence", "Current Absolute Gap", "Current Gap Ratio",
    "Previous Event Persistence", "Logistic Regression", "Decision Tree", "Random Forest",
]


def display_name(score_col: str) -> str:
    return score_col.removesuffix("_Score").replace("_", " ")


def tie_adjusted_budget(y, score, budget):
    """Exact capacity with expected positives when the cutoff score is tied."""
    y = np.asarray(y, dtype=int)
    score = np.asarray(score, dtype=float)
    n = len(y)
    k = max(1, int(math.ceil(n * budget)))
    order = np.argsort(-score, kind="stable")
    cutoff = float(score[order[k - 1]])
    above = score > cutoff
    tied = score == cutoff
    above_n = int(above.sum())
    tie_n = int(tied.sum())
    slots_from_tie = int(k - above_n)
    above_tp = int(y[above].sum())
    tie_events = int(y[tied].sum())
    expected_tie_tp = slots_from_tie * tie_events / tie_n
    expected_tp = float(above_tp + expected_tie_tp)
    exact_idx = order[:k]
    exact_tp = int(y[exact_idx].sum())
    prevalence = float(y.mean())
    precision = expected_tp / k
    recall = expected_tp / max(1, int(y.sum()))
    return {
        "Observations": n,
        "Events": int(y.sum()),
        "Event_Rate": prevalence,
        "Budget_Pct": budget * 100,
        "Alerts": k,
        "Expected_True_Positives": expected_tp,
        "Exact_True_Positives_Stable_Tiebreak": exact_tp,
        "Precision": float(precision),
        "Recall": float(recall),
        "Lift": float(precision / prevalence) if prevalence else None,
        "Number_Needed_to_Review": float(k / expected_tp) if expected_tp else None,
        "Cutoff_Score": cutoff,
        "Rows_Above_Cutoff": above_n,
        "Rows_Tied_at_Cutoff": tie_n,
        "Slots_Selected_from_Tie": slots_from_tie,
        "Events_in_Cutoff_Tie": tie_events,
        "Tie_Adjustment_Used": bool(tie_n > slots_from_tie),
    }


pred = pd.read_csv(INPUT)
score_cols = [c for c in pred.columns if c.endswith("_Score")]
score_map = {display_name(c): c for c in score_cols}
assert set(model_order).issubset(score_map), "Expected score columns are missing"

fold_rows = []
for budget in budgets:
    for fold, part in pred.groupby("Fold", sort=False):
        y = part[target].astype(int).to_numpy()
        for model in model_order:
            row = {"Fold": fold, "Model": model}
            row.update(tie_adjusted_budget(y, part[score_map[model]].to_numpy(float), budget))
            fold_rows.append(row)

fold_metrics = pd.DataFrame(fold_rows)
summary_rows = []
for (budget_pct, model), part in fold_metrics.groupby(["Budget_Pct", "Model"], sort=False):
    alerts = int(part["Alerts"].sum())
    expected_tp = float(part["Expected_True_Positives"].sum())
    events = int(part["Events"].sum())
    observations = int(part["Observations"].sum())
    precision = expected_tp / alerts
    recall = expected_tp / events
    prevalence = events / observations
    summary_rows.append({
        "Budget_Pct": float(budget_pct),
        "Model": model,
        "Test_Folds": int(part["Fold"].nunique()),
        "Observations": observations,
        "Events": events,
        "Total_Alerts": alerts,
        "Expected_True_Positives": expected_tp,
        "Precision": precision,
        "Recall": recall,
        "Lift": precision / prevalence,
        "Number_Needed_to_Review": alerts / expected_tp if expected_tp else None,
        "Mean_Fold_Precision": float(part["Precision"].mean()),
        "Mean_Fold_Recall": float(part["Recall"].mean()),
        "Folds_with_Cutoff_Ties": int(part["Tie_Adjustment_Used"].sum()),
    })

summary = pd.DataFrame(summary_rows)
summary["Precision_Rank_within_Budget"] = summary.groupby("Budget_Pct")["Precision"].rank(method="min", ascending=False).astype(int)

# Diminishing-return audit for the primary gap-ratio rule.
gap = summary[summary["Model"].eq("Current Gap Ratio")].sort_values("Budget_Pct").copy()
gap["Additional_Alerts_vs_Prior_Budget"] = gap["Total_Alerts"].diff()
gap["Additional_Expected_TP_vs_Prior_Budget"] = gap["Expected_True_Positives"].diff()
gap["Marginal_Precision_vs_Prior_Budget"] = (
    gap["Additional_Expected_TP_vs_Prior_Budget"] / gap["Additional_Alerts_vs_Prior_Budget"]
)

fold_metrics.to_csv(FOLD_CSV, index=False, float_format="%.17g")
summary.to_csv(SUMMARY_CSV, index=False, float_format="%.17g")
gap.to_csv(OUT / "ETF_Alert_Budget_Gap_Ratio_Tradeoff.csv", index=False, float_format="%.17g")

clean = lambda d: d.astype(object).where(pd.notna(d), None).to_dict("records")
result = {
    "analysis": "Alert-budget sensitivity on untouched walk-forward test predictions",
    "budgets_pct": [5, 10, 20],
    "tie_rule": "Select all rows above the cutoff and use expected positives for the remaining slots within the cutoff tie",
    "fold_metrics": clean(fold_metrics),
    "pooled_summary": clean(summary),
    "gap_ratio_tradeoff": clean(gap),
}
RESULTS_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")

# Pooled precision and recall curves.
core = ["Current Gap Ratio", "Logistic Regression", "Decision Tree", "Random Forest"]
colors = {"Current Gap Ratio": "#1F4E78", "Logistic Regression": "#4472C4",
          "Decision Tree": "#70AD47", "Random Forest": "#ED7D31"}
fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.7))
for model in core:
    p = summary[summary["Model"].eq(model)].sort_values("Budget_Pct")
    axes[0].plot(p["Budget_Pct"], p["Precision"] * 100, marker="o", label=model, color=colors[model])
    axes[1].plot(p["Budget_Pct"], p["Recall"] * 100, marker="o", label=model, color=colors[model])
axes[0].set_title("Precision decreases as alert capacity expands")
axes[1].set_title("Recall increases as alert capacity expands")
for ax, ylabel in zip(axes, ["Pooled precision (%)", "Pooled recall (%)"]):
    ax.set_xlabel("Alert budget (% of dates)"); ax.set_ylabel(ylabel)
    ax.set_xticks([5, 10, 20]); ax.grid(alpha=.25)
axes[0].legend(frameon=False, fontsize=8)
fig.tight_layout(); fig.savefig(FIG / "ETF_Alert_Budget_Precision_Recall.png", dpi=220, bbox_inches="tight"); plt.close(fig)

# Gap-ratio capacity trade-off.
fig, ax = plt.subplots(figsize=(8.3, 4.8))
ax.plot(gap["Budget_Pct"], gap["Precision"] * 100, marker="o", linewidth=2.2, label="Precision")
ax.plot(gap["Budget_Pct"], gap["Recall"] * 100, marker="o", linewidth=2.2, label="Recall")
ax.set_title("Current gap ratio: operational capacity trade-off")
ax.set_xlabel("Alert budget (% of dates)"); ax.set_ylabel("Performance (%)")
ax.set_xticks([5, 10, 20]); ax.grid(alpha=.25); ax.legend(frameon=False)
fig.tight_layout(); fig.savefig(FIG / "ETF_Gap_Ratio_Budget_Tradeoff.png", dpi=220, bbox_inches="tight"); plt.close(fig)

print(json.dumps({
    "gap_ratio": gap[["Budget_Pct", "Total_Alerts", "Expected_True_Positives", "Precision", "Recall", "Lift", "Number_Needed_to_Review"]].to_dict("records"),
    "top_precision_model_by_budget": summary.loc[summary.groupby("Budget_Pct")["Precision"].idxmax(), ["Budget_Pct", "Model", "Precision"]].to_dict("records"),
}, indent=2))
