"""Paired moving-block bootstrap uncertainty for walk-forward test predictions.

The procedure follows docs/ANALYSIS_PLAN_V2.md: 2,000 valid resamples,
five-observation primary blocks, ten-observation sensitivity blocks, seed 42.
Each fold is resampled independently, while the same indices are applied to
every model so model differences remain paired.
"""
from __future__ import annotations

from pathlib import Path
import json
import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
FIG = ROOT / "figures"
OUT.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)

INPUT = OUT / "ETF_Walk_Forward_Predictions.csv"
INTERVALS_CSV = OUT / "ETF_Block_Bootstrap_Intervals.csv"
DIFFERENCES_CSV = OUT / "ETF_Paired_PR_AUC_Differences.csv"
RESULTS_JSON = OUT / "block_bootstrap_results.json"

df = pd.read_csv(INPUT, parse_dates=["Prediction_Date", "Target_Date"])
target = "Y_Abnormal_Dislocation_95Q"
folds = list(df["Fold"].drop_duplicates())
models = {
    "Historical Prevalence": "Historical_Prevalence_Score",
    "Current Absolute Gap": "Current_Absolute_Gap_Score",
    "Current Gap Ratio": "Current_Gap_Ratio_Score",
    "Previous Event Persistence": "Previous_Event_Persistence_Score",
    "Logistic Regression": "Logistic_Regression_Score",
    "Decision Tree": "Decision_Tree_Score",
    "Random Forest": "Random_Forest_Score",
}
comparators = ["Logistic Regression", "Decision Tree", "Random Forest"]
resamples = 2000


def circular_block_indices(n, block_length, rng):
    blocks = int(math.ceil(n / block_length))
    starts = rng.integers(0, n, size=blocks)
    return np.concatenate([(start + np.arange(block_length)) % n for start in starts])[:n]


def ranked_budget(y, score, budget=0.10, no_skill=False):
    y = np.asarray(y, dtype=int)
    k = max(1, int(math.ceil(len(y) * budget)))
    if no_skill:
        prevalence = float(y.mean())
        return prevalence, float(k / len(y))
    order = np.argsort(-np.asarray(score, dtype=float), kind="stable")
    chosen = y[order[:k]]
    return float(chosen.mean()), float(chosen.sum() / y.sum())


def point_metrics(part, model, score_column):
    y = part[target].to_numpy(int)
    score = part[score_column].to_numpy(float)
    precision, recall = ranked_budget(y, score, 0.10, no_skill=model == "Historical Prevalence")
    return {
        "PR_AUC": float(average_precision_score(y, score)),
        "Precision_at_10Pct": precision,
        "Recall_at_10Pct": recall,
    }


interval_rows = []
difference_rows = []
json_by_block = {}

for block_length in [5, 10]:
    rng = np.random.default_rng(42 + block_length)
    observed_fold = {
        fold: {model: point_metrics(df[df["Fold"].eq(fold)], model, column) for model, column in models.items()}
        for fold in folds
    }
    observed_mean = {
        model: {metric: float(np.mean([observed_fold[fold][model][metric] for fold in folds]))
                for metric in ["PR_AUC", "Precision_at_10Pct", "Recall_at_10Pct"]}
        for model in models
    }

    fold_dist = {
        fold: {model: {metric: [] for metric in ["PR_AUC", "Precision_at_10Pct", "Recall_at_10Pct"]}
               for model in models}
        for fold in folds
    }
    mean_dist = {model: {metric: [] for metric in ["PR_AUC", "Precision_at_10Pct", "Recall_at_10Pct"]}
                 for model in models}

    accepted = 0
    attempts = 0
    while accepted < resamples and attempts < resamples * 20:
        attempts += 1
        sampled = {}
        valid = True
        for fold in folds:
            part = df[df["Fold"].eq(fold)].reset_index(drop=True)
            idx = circular_block_indices(len(part), block_length, rng)
            boot = part.iloc[idx].reset_index(drop=True)
            if boot[target].nunique() < 2:
                valid = False
                break
            sampled[fold] = boot
        if not valid:
            continue

        for fold in folds:
            for model, column in models.items():
                values = point_metrics(sampled[fold], model, column)
                for metric, value in values.items():
                    fold_dist[fold][model][metric].append(value)

        for model in models:
            for metric in ["PR_AUC", "Precision_at_10Pct", "Recall_at_10Pct"]:
                mean_dist[model][metric].append(float(np.mean([
                    fold_dist[fold][model][metric][-1] for fold in folds
                ])))
        accepted += 1

    if accepted < resamples:
        raise RuntimeError(f"Only {accepted} valid resamples for block length {block_length}")

    for fold in folds:
        for model in models:
            for metric in ["PR_AUC", "Precision_at_10Pct", "Recall_at_10Pct"]:
                values = np.asarray(fold_dist[fold][model][metric])
                interval_rows.append({
                    "Block_Length": block_length,
                    "Scope": "Individual fold",
                    "Fold": fold,
                    "Model": model,
                    "Metric": metric,
                    "Observed": observed_fold[fold][model][metric],
                    "CI_Lower_95Pct": float(np.percentile(values, 2.5)),
                    "CI_Upper_95Pct": float(np.percentile(values, 97.5)),
                    "Valid_Resamples": accepted,
                })

    for model in models:
        for metric in ["PR_AUC", "Precision_at_10Pct", "Recall_at_10Pct"]:
            values = np.asarray(mean_dist[model][metric])
            interval_rows.append({
                "Block_Length": block_length,
                "Scope": "Mean across folds",
                "Fold": "All folds",
                "Model": model,
                "Metric": metric,
                "Observed": observed_mean[model][metric],
                "CI_Lower_95Pct": float(np.percentile(values, 2.5)),
                "CI_Upper_95Pct": float(np.percentile(values, 97.5)),
                "Valid_Resamples": accepted,
            })

    for comparator in comparators:
        gap = np.asarray(mean_dist["Current Gap Ratio"]["PR_AUC"])
        other = np.asarray(mean_dist[comparator]["PR_AUC"])
        diff = gap - other
        observed_diff = observed_mean["Current Gap Ratio"]["PR_AUC"] - observed_mean[comparator]["PR_AUC"]
        difference_rows.append({
            "Block_Length": block_length,
            "Reference_Model": "Current Gap Ratio",
            "Comparator": comparator,
            "Observed_PR_AUC_Difference": observed_diff,
            "CI_Lower_95Pct": float(np.percentile(diff, 2.5)),
            "CI_Upper_95Pct": float(np.percentile(diff, 97.5)),
            "Bootstrap_Share_Difference_GT_0": float(np.mean(diff > 0)),
            "Valid_Resamples": accepted,
        })

    json_by_block[str(block_length)] = {
        "accepted_resamples": accepted,
        "attempts": attempts,
        "observed_mean": observed_mean,
    }

intervals = pd.DataFrame(interval_rows)
differences = pd.DataFrame(difference_rows)
intervals.to_csv(INTERVALS_CSV, index=False, float_format="%.8f")
differences.to_csv(DIFFERENCES_CSV, index=False, float_format="%.8f")

result = {
    "method": "Paired circular moving-block bootstrap within each walk-forward test fold",
    "resamples": resamples,
    "random_seed_rule": "42 + block length",
    "block_lengths": [5, 10],
    "blocks": json_by_block,
    "model_intervals": intervals.to_dict("records"),
    "paired_pr_auc_differences": differences.to_dict("records"),
}
RESULTS_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")

# Primary five-day-block figures.
plot = intervals[(intervals["Block_Length"].eq(5)) & (intervals["Scope"].eq("Mean across folds")) & (intervals["Metric"].eq("PR_AUC"))].copy()
order = ["Current Gap Ratio", "Current Absolute Gap", "Random Forest", "Logistic Regression", "Decision Tree", "Previous Event Persistence", "Historical Prevalence"]
plot["Order"] = plot["Model"].map({name: i for i, name in enumerate(order)})
plot = plot.sort_values("Order", ascending=False)
lower = plot["Observed"] - plot["CI_Lower_95Pct"]
upper = plot["CI_Upper_95Pct"] - plot["Observed"]
fig, ax = plt.subplots(figsize=(8.8, 5.2))
ax.errorbar(plot["Observed"], plot["Model"], xerr=[lower, upper], fmt="o", color="#1F4E78", ecolor="#7F8C8D", capsize=4)
ax.set_title("Mean walk-forward PR-AUC with 95% block-bootstrap intervals")
ax.set_xlabel("Mean test PR-AUC"); ax.grid(axis="x", alpha=.25)
fig.tight_layout(); fig.savefig(FIG / "ETF_Bootstrap_PR_AUC_Intervals.png", dpi=220, bbox_inches="tight"); plt.close(fig)

diff_plot = differences[differences["Block_Length"].eq(5)].copy().sort_values("Observed_PR_AUC_Difference")
lower = diff_plot["Observed_PR_AUC_Difference"] - diff_plot["CI_Lower_95Pct"]
upper = diff_plot["CI_Upper_95Pct"] - diff_plot["Observed_PR_AUC_Difference"]
fig, ax = plt.subplots(figsize=(8.2, 3.8))
ax.errorbar(diff_plot["Observed_PR_AUC_Difference"], diff_plot["Comparator"], xerr=[lower, upper], fmt="o", color="#1F4E78", ecolor="#7F8C8D", capsize=4)
ax.axvline(0, color="#C00000", linestyle="--", linewidth=1)
ax.set_title("Paired PR-AUC difference: gap ratio minus classifier")
ax.set_xlabel("Mean PR-AUC difference with 95% interval"); ax.grid(axis="x", alpha=.25)
fig.tight_layout(); fig.savefig(FIG / "ETF_Bootstrap_Paired_Differences.png", dpi=220, bbox_inches="tight"); plt.close(fig)

primary_intervals = intervals[(intervals.Block_Length.eq(5)) & (intervals.Scope.eq("Mean across folds"))]
print(json.dumps({
    "primary_mean_intervals": primary_intervals.to_dict("records"),
    "paired_differences": differences[differences.Block_Length.eq(5)].to_dict("records"),
    "accepted_resamples": json_by_block["5"]["accepted_resamples"],
}, indent=2))
