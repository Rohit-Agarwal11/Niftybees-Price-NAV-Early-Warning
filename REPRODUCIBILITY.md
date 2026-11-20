# Reproducibility

## Fast verification

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python run_all.py
```

The workflow rebuilds the merged panel, constructs leakage-safe next-day
labels, trains the baseline and classifier models, runs purged walk-forward
validation, moving-block bootstrap uncertainty, label sensitivity,
alert-budget evaluation, feature ablation, temporal-shift diagnostics,
dislocation-size analysis, delayed-NAV timing stress and supplementary gradient
boosting, and regenerates report figures.

## Notebook route

Open `notebooks/ETF_Project_Complete_Steps_1_to_8.ipynb` from the repository root and run all cells in order. The notebook contains the complete analysis for inspection.

## Expected core checks

- Market rows: 1,456
- NAV rows: 1,451
- Complete analysis rows: 1,446
- Leakage-safe modeling rows: 1,185
- Total abnormal events: 80
- Frozen 2026 test events: 34
- 2026 PR-AUC: current gap ratio 0.290; logistic regression 0.267; decision tree 0.206; random forest 0.202; historical prevalence 0.159
- Alerted versus non-alerted mean next-session gap: 18.49 versus 12.49 bps
- Delayed-NAV mean PR-AUC: gap ratio 0.160; random forest 0.161
- Gradient-boosting mean PR-AUC: 0.145

All dates are chronological. Features use information available at date *t* or earlier; the outcome is defined for the next market date. Fixed seeds and tuning grids are stored in `config/project_config.json` and the numbered scripts.
