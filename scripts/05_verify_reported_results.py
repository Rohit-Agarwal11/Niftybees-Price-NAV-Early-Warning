"""Fail loudly if a reproduced value differs from the second-review report."""
from pathlib import Path
import json

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = ROOT / "outputs"

market = pd.read_csv(DATA / "NIFTYBEES_EQ_Market_Data_2021_to_2026_Clean.csv")
nav = pd.read_csv(DATA / "NIFTYBEES_NAV_AMFI_official_2021_to_2026_Updated.csv")
master = pd.read_csv(DATA / "ETF_Master_Merged_2021_to_2026.csv")
analysis = pd.read_csv(DATA / "ETF_Analysis_Ready_2021_to_2026.csv")
model = pd.read_csv(DATA / "ETF_Modeling_Dataset_Leakage_Safe_2021_to_2026.csv")
results = json.loads((OUT / "model_results.json").read_text(encoding="utf-8"))

assert len(market) == 1456
assert len(nav) == 1451
assert len(master) == 1456
assert len(analysis) == 1446
assert len(model) == 1185
assert int(model["Y_Abnormal_Dislocation_95Q"].sum()) == 80

expected_splits = {"Train": (725, 41), "Validation": (246, 5), "Test": (214, 34)}
for split, (rows, events) in expected_splits.items():
    part = model[model["Chronological_Split"].eq(split)]
    assert len(part) == rows
    assert int(part["Y_Abnormal_Dislocation_95Q"].sum()) == events

test = {r["Model"]: r for r in results["metrics"] if r["Split"] == "Test"}
expected_pr_auc = {
    "Historical Prevalence": 0.159,
    "Current Gap Rule": 0.290,
    "Logistic Regression": 0.267,
    "Decision Tree": 0.206,
    "Random Forest": 0.202,
}
for name, expected in expected_pr_auc.items():
    # The report presents model metrics to three decimals. Rebuilding the merged
    # CSV can alter later floating-point digits without altering a reported value.
    assert round(test[name]["PR_AUC"], 3) == expected, (name, test[name]["PR_AUC"], expected)

assert round(test["Logistic Regression"]["Brier_Score"], 3) == 0.134
assert round(test["Decision Tree"]["Brier_Score"], 3) == 0.152
assert round(test["Random Forest"]["Brier_Score"], 3) == 0.162

budget = {r["Model"]: r for r in results["budget_metrics"] if r["Split"] == "Test"}
assert budget["Current Gap Rule"]["Alerts"] == 22
assert budget["Current Gap Rule"]["True_Positives"] == 8
assert abs(budget["Current Gap Rule"]["Precision_at_Budget"] - 8 / 22) < 1e-12
assert results["selected_model"] == "Random Forest"
print("PASS: all data counts, event counts, split counts and reported test results match the second-review draft.")
