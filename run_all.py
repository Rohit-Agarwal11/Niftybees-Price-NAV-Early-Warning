"""Execute the complete reproducible workflow in its required order."""
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
steps = [
    "01_merge_and_audit_data.py",
    "02_build_leakage_safe_dataset.py",
    "03_train_and_evaluate_models.py",
    "07_walk_forward_validation.py",
    "08_block_bootstrap_uncertainty.py",
    "09_label_sensitivity.py",
    "10_alert_budget_sensitivity.py",
    "11_feature_group_ablation.py",
    "12_temporal_shift_diagnostics.py",
    "04_make_report_figures.py",
    "05_verify_reported_results.py",
    "06_build_second_review_report.py",
    "13_build_final_integrated_report.py",
    "14_build_overleaf_style_report.py",
]
for step in steps:
    print(f"\n=== Running {step} ===", flush=True)
    subprocess.run([sys.executable, str(ROOT / "scripts" / step)], cwd=ROOT, check=True)
print("\nReproduction completed successfully.")
