"""Recreate the two figures included in the second-review report."""
from pathlib import Path
import json

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS = json.loads((ROOT / "outputs" / "model_results.json").read_text(encoding="utf-8"))
FIGURES = ROOT / "figures"
FIGURES.mkdir(exist_ok=True)
metrics = pd.DataFrame([r for r in RESULTS["metrics"] if r["Split"] == "Test"])
budget = pd.DataFrame([r for r in RESULTS["budget_metrics"] if r["Split"] == "Test"])

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
fig, ax = plt.subplots(figsize=(7.2, 3.5))
ax.bar(metrics["Model"], metrics["PR_AUC"], color=["#A5A5A5", "#1F77B4", "#4472C4", "#70AD47", "#ED7D31"])
baseline = metrics.loc[metrics.Model.eq("Historical Prevalence"), "PR_AUC"].iloc[0]
ax.axhline(baseline, color="#7F7F7F", linestyle="--", linewidth=1, label="No-skill PR-AUC")
ax.set(ylabel="PR-AUC", title="Out-of-time test PR-AUC", ylim=(0, 0.34))
ax.grid(axis="y", alpha=.25); ax.tick_params(axis="x", rotation=18); ax.legend(frameon=False)
fig.tight_layout(); fig.savefig(FIGURES / "ETF_Test_PR_AUC.png", dpi=220, bbox_inches="tight"); plt.close(fig)

fig, ax = plt.subplots(figsize=(7.2, 3.5))
ax.bar(budget["Model"], budget["Precision_at_Budget"] * 100, color=["#1F77B4", "#4472C4", "#70AD47", "#ED7D31"])
ax.set(ylabel="Precision among alerts (%)", title="Test performance under a 10% alert budget", ylim=(0, 42))
ax.grid(axis="y", alpha=.25)
for i, (precision, events) in enumerate(zip(budget["Precision_at_Budget"] * 100, budget["True_Positives"])):
    ax.text(i, precision + 1, f"{precision:.1f}%\n{int(events)} events", ha="center", va="bottom", fontsize=9)
ax.tick_params(axis="x", rotation=12)
fig.tight_layout(); fig.savefig(FIGURES / "ETF_Alert_Budget.png", dpi=220, bbox_inches="tight"); plt.close(fig)
print("Figures recreated in figures/")
