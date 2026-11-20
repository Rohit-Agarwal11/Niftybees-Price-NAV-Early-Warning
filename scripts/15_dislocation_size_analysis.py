"""Compare next-session dislocation size on alerted and non-alerted days.

Uses untouched walk-forward test predictions. The primary alert is the current
gap-ratio ranking at a 10% within-fold review budget. Uncertainty is estimated
by a stratified bootstrap that resamples alerted and non-alerted observations
separately, preserving the observed group sizes.
"""
from __future__ import annotations

from pathlib import Path
import json
import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT, FIG = ROOT / "outputs", ROOT / "figures"
INPUT = OUT / "ETF_Walk_Forward_Predictions.csv"
SUMMARY_CSV = OUT / "ETF_Dislocation_Size_by_Alert.csv"
BOOTSTRAP_CSV = OUT / "ETF_Dislocation_Size_Bootstrap.csv"
RESULTS_JSON = OUT / "dislocation_size_results.json"
RNG = np.random.default_rng(42)


def top_budget(score: np.ndarray, budget: float = 0.10) -> np.ndarray:
    k = max(1, int(math.ceil(len(score) * budget)))
    order = np.argsort(-np.asarray(score, float), kind="stable")
    alert = np.zeros(len(score), dtype=bool)
    alert[order[:k]] = True
    return alert


pred = pd.read_csv(INPUT, parse_dates=["Prediction_Date", "Target_Date"])
parts = []
for fold, part in pred.groupby("Fold", sort=False):
    part = part.copy()
    part["Alert"] = top_budget(part["Current_Gap_Ratio_Score"].to_numpy(float))
    parts.append(part)
work = pd.concat(parts, ignore_index=True)
work["Target_Abs_Dislocation_bps"] = work["Target_Abs_Dislocation_Pct"] * 100.0

summary_rows = []
for alert, part in work.groupby("Alert", sort=False):
    x = part["Target_Abs_Dislocation_bps"].to_numpy(float)
    summary_rows.append({
        "Group": "Alerted" if alert else "Not alerted",
        "Observations": int(len(x)),
        "Events": int(part["Y_Abnormal_Dislocation_95Q"].sum()),
        "Mean_Abs_Dislocation_bps": float(np.mean(x)),
        "Median_Abs_Dislocation_bps": float(np.median(x)),
        "P90_Abs_Dislocation_bps": float(np.quantile(x, 0.90)),
        "P95_Abs_Dislocation_bps": float(np.quantile(x, 0.95)),
    })
summary = pd.DataFrame(summary_rows)

a = work.loc[work["Alert"], "Target_Abs_Dislocation_bps"].to_numpy(float)
n = work.loc[~work["Alert"], "Target_Abs_Dislocation_bps"].to_numpy(float)
reps = []
for i in range(5000):
    aa = RNG.choice(a, len(a), replace=True)
    nn = RNG.choice(n, len(n), replace=True)
    reps.append({
        "Replicate": i + 1,
        "Mean_Difference_bps": float(np.mean(aa) - np.mean(nn)),
        "Median_Difference_bps": float(np.median(aa) - np.median(nn)),
    })
boot = pd.DataFrame(reps)
mean_diff = float(np.mean(a) - np.mean(n))
median_diff = float(np.median(a) - np.median(n))
effect = {
    "Mean_Difference_bps": mean_diff,
    "Mean_Difference_95Pct_CI": [float(x) for x in np.quantile(boot["Mean_Difference_bps"], [0.025, 0.975])],
    "Median_Difference_bps": median_diff,
    "Median_Difference_95Pct_CI": [float(x) for x in np.quantile(boot["Median_Difference_bps"], [0.025, 0.975])],
    "Probability_Mean_Difference_Positive": float((boot["Mean_Difference_bps"] > 0).mean()),
}

summary.to_csv(SUMMARY_CSV, index=False, float_format="%.17g")
boot.to_csv(BOOTSTRAP_CSV, index=False, float_format="%.17g")
RESULTS_JSON.write_text(json.dumps({
    "analysis": "Next-session absolute dislocation size by primary 10% gap-ratio alert",
    "unit": "basis points; one percentage point equals 100 bps",
    "summary": summary.to_dict("records"),
    "effect": effect,
    "bootstrap": {"resamples": 5000, "seed": 42, "method": "stratified nonparametric bootstrap"},
}, indent=2), encoding="utf-8")

fig, ax = plt.subplots(figsize=(7.6, 4.5))
plot = summary.set_index("Group").loc[["Not alerted", "Alerted"]]
bars = ax.bar(plot.index, plot["Mean_Abs_Dislocation_bps"], color=["#A5A5A5", "#1F4E78"], width=.58)
ax.bar_label(bars, labels=[f"{v:.1f} bps" for v in plot["Mean_Abs_Dislocation_bps"]], padding=4)
ax.set_ylabel("Mean next-session absolute gap (bps)")
ax.set_title("Operational alerts identify larger next-session dislocations")
ax.grid(axis="y", alpha=.25)
fig.tight_layout()
fig.savefig(FIG / "ETF_Dislocation_Size_by_Alert.png", dpi=220, bbox_inches="tight")
plt.close(fig)

print(json.dumps({"summary": summary.to_dict("records"), "effect": effect}, indent=2))
