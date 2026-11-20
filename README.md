# Does Model Complexity Improve Next-Day Price–NAV Dislocation Warnings?

## A Leakage-Controlled Walk-Forward Study of NIFTYBEES

This repository reproduces the final integrated draft of a college project on predicting unusually large next-trading-day differences between the NIFTYBEES closing price and its official net asset value (NAV).

The project is an **early-warning and risk-monitoring study**. It does not claim a risk-free arbitrage opportunity and is not an investment recommendation.

## Primary research question

Do complex machine-learning models provide more reliable next-trading-day warnings of abnormal NIFTYBEES price–NAV dislocations than transparent benchmark rules when market conditions change over time?

The second-review extension evaluates prediction, model complexity, calibration, operational alert utility and temporal stability. The additional analyses are governed by `docs/ANALYSIS_PLAN_V2.md` and are reported whether or not they improve the headline result.

### Walk-forward finding

Across three purged, subsequent-year test folds, the current gap-to-threshold ratio records the highest mean PR-AUC of **0.233**, wins two folds and produces mean alert precision of **26.8%** under a 10% review budget. Random forest is validation-selected in all three folds but wins no subsequent test fold. Complete results are in `docs/WALK_FORWARD_RESULTS.md`.

### Uncertainty finding

A paired moving-block bootstrap with 2,000 valid resamples gives the gap ratio a mean PR-AUC interval of **0.160–0.349**. Its paired advantage over the decision tree is **0.078** with a 95% interval of **0.019–0.168**. Paired intervals against logistic regression and random forest include zero, so superiority over those classifiers is not established at the 95% level. The conclusion is unchanged with 10-observation blocks. Complete results are in `docs/BOOTSTRAP_UNCERTAINTY_RESULTS.md`.

### Label-sensitivity finding

The exact PR-AUC winner changes with the rolling event threshold: random forest leads at the 90th percentile by **0.010**, the gap ratio leads at the primary 95th percentile, and random forest leads the sparse 97.5th-percentile case by **0.002**. That final margin should be treated as noise because the 2025 test fold contains only one positive event under the 97.5th-percentile label. The gap ratio nevertheless has higher mean precision, recall and lift at the 10% alert budget under all three rolling definitions. Fixed 0.50% and 1.00% labels contain only 12 and 2 events and are infeasible for the prespecified walk-forward comparison. Complete results are in `docs/LABEL_SENSITIVITY_RESULTS.md`.

### Alert-budget finding

The current gap ratio has the highest pooled precision at every prespecified review capacity. Precision is **29.7%**, **26.4%** and **19.0%** at 5%, 10% and 20% budgets, while recall rises from **16.9%** to **29.2%** and **41.5%**. Expanding from 10% to 20% adds 70 alerts but only 8 additional identified events, supporting 10% as a practical workload–coverage balance. Tied cutoff scores are handled through expected selection within the tie rather than arbitrary row order. Complete results are in `docs/ALERT_BUDGET_RESULTS.md`.

### Feature-ablation finding

Adding NIFTY 50 and India VIX variables raises logistic-regression mean walk-forward PR-AUC from **0.153 to 0.195**, with improvement in all three test folds. Liquidity variables do not provide consistent incremental gains across classifiers. The best random-forest specification uses all 25 predictors and reaches **0.184**, while the transparent current gap-ratio reference remains higher at **0.233**. Complete results are in `docs/FEATURE_ABLATION_RESULTS.md`.

### Temporal-shift finding

Abnormal-event prevalence changes from **10.7% in 2024 to 2.0% in 2025 and 15.9% in 2026**. Median validation-to-test predictor PSI is 0.141, 0.191 and 0.222, while validation-locked 10% cutoffs produce only 0.0%–5.3% alerts in 2025 but 22.9%–39.3% in 2026. Model ranking and probability calibration change materially with these regimes, supporting H4 and favouring capacity-based ranking with ongoing drift monitoring. Complete results are in `docs/TEMPORAL_SHIFT_RESULTS.md`.

### Operational magnitude and robustness findings

At the primary 10% gap-ratio budget, alerted dates have a mean next-session
absolute dislocation of **18.49 bps**, compared with **12.49 bps** on
non-alerted dates. The difference is **6.00 bps** with a stratified-bootstrap
95% interval of **2.84–9.45 bps**. Under a deliberately adverse one-trading-day
NAV delay, performance falls and the gap ratio (**0.160 mean PR-AUC**) is
effectively tied with random forest (**0.161**), showing that timely official
NAV availability is material. A validation-tuned histogram gradient-boosting
model reaches only **0.145 mean PR-AUC**, below the original gap ratio's
**0.233**. Complete results are in `docs/ROBUSTNESS_AND_OPERATIONAL_RESULTS.md`.

## Final sample

| Stage | Observations |
|---|---:|
| NIFTYBEES market rows | 1,456 |
| Official AMFI NAV rows | 1,451 |
| Complete merged observations | 1,446 |
| Leakage-safe modelling observations | 1,185 |
| Abnormal next-day events | 80 |

Study period: **1 January 2021 to 16 November 2026**.

## Models and headline results

The primary code compares a transparent current-gap rule with logistic
regression, a bounded decision tree and a random forest. A supplementary,
validation-tuned histogram gradient-boosting model closes the original
proposal comparison without changing the frozen label or folds. Hyperparameters
are selected using prior-year validation data; each subsequent test fold remains
untouched until selection is complete.

| Model | Test PR-AUC | Test ROC-AUC | Test Brier score |
|---|---:|---:|---:|
| Historical prevalence | 0.159 | 0.500 | 0.144 |
| Current-gap rule | **0.290** | **0.642** | Not applicable |
| Logistic regression | 0.267 | 0.543 | **0.134** |
| Decision tree | 0.206 | 0.605 | 0.152 |
| Random forest | 0.202 | 0.599 | 0.162 |

Random forest achieved the highest validation PR-AUC and was therefore the validation-selected classifier, but it did not retain that advantage in the untouched test period. Under a 10% test alert budget, the current-gap rule issued 22 alerts and identified 8 of 34 abnormal events (36.4% precision; 23.5% recall).

## Repository structure

```text
config/                 Project parameters and split dates
data/processed/         Official cleaned inputs and reproducible analytical datasets
data/raw/README.md      Exact download instructions for the original official sources
docs/                   Methodology, source register, data dictionary and model card
figures/                Figures used in the report
outputs/                Audit workbooks, row-level predictions and model results
paper/                  Submitted PDF
scripts/                Numbered end-to-end analysis scripts
notebooks/              Complete Steps 1–8 Jupyter workflow
```

## Quick reproduction

Python 3.11 or 3.12 is recommended.

Exact numerical reproduction requires the package versions pinned in
`requirements.txt`; newer library versions can change floating-point results,
tie handling or model defaults. The full `run_all.py` workflow retunes all
models across the walk-forward, label-sensitivity and feature-ablation grids,
so expect a runtime of tens of minutes on a typical laptop. Runtime varies with
CPU core count and available memory.

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
python run_all.py
```

The final command executes these steps:

1. Merge and audit the four cleaned official inputs.
2. Construct the rolling 252-observation label and leakage-safe features.
3. Tune and compare the three primary classifiers using chronological validation.
4. Recreate the report figures.
5. Run the prespecified walk-forward and paired block-bootstrap analyses.
6. Test label sensitivity, alert budgets, feature groups and temporal shift.
7. Test operational dislocation magnitude, delayed-NAV timing and gradient boosting.
8. Verify the reported counts and metrics and rebuild both report drafts.

The same workflow is available as `notebooks/ETF_Project_Complete_Steps_1_to_8.ipynb`. Its cells reproduce all numbered scripts in execution order and rebuild the final reports.

A successful run ends with:

```text
PASS: all data counts, split counts, reported metrics and added robustness results match the final paper.
```

## Prediction and label design

For prediction date *t*:

```text
signed dislocation_t = 100 × (ETF close_t − NAV_t) / NAV_t
absolute dislocation_t = |signed dislocation_t|
```

An abnormal event equals 1 when the next actual NSE trading day's absolute dislocation exceeds the rolling 95th percentile of the 252 complete observations available through date *t*.

All predictor names start with `X_`; future labels start with `Y_`. Features use date *t* or earlier only. One overlapping label interval is purged at each train/validation and validation/test boundary.

## Chronological design

| Partition | Target period | Rows | Events |
|---|---|---:|---:|
| Training | 12 Jan 2022–30 Dec 2024 | 725 | 41 |
| Validation | 1 Jan–30 Dec 2025 | 246 | 5 |
| Testing | 1 Jan–16 Nov 2026 | 214 | 34 |

PR-AUC is the primary ranking metric because abnormal events are uncommon. ROC-AUC, Brier score, log loss, calibration measures and 10% alert-budget performance are reported as supporting diagnostics.

## Official data sources

- [NSE security-wise price, volume and delivery data](https://www.nseindia.com/report-detail/eq_security)
- [AMFI historical NAV download](https://www.amfiindia.com/net-asset-value/nav-download)
- [NSE Indices historical index reports](https://www.niftyindices.com/reports)
- [NSE historical index data](https://www.nseindia.com/reports-indices-historical-index-data)

The exact files, fields, identifiers and download instructions are recorded in `docs/SOURCES_AND_REFERENCES.md`, `docs/source_register.csv` and `data/raw/README.md`.

## Important data-quality decisions

- Eight special/Muhurat market sessions had an exchange record but no matching AMFI NAV.
- India VIX values for 12 February 2021 and 30 March 2021 were source-zero anomalies and were excluded from complete cases.
- The maximum retained absolute price–NAV dislocation was 3.010% on 4 June 2024.
- Scheme identity was checked using AMFI scheme code `140084`, scheme name and ISIN.
- Random seed `42` is fixed for all stochastic models.

## Interpretation

The strongest test ranking came from the simple current-gap rule. Logistic regression produced the best probability estimates among the classifiers. The result supports a transparent risk-screening workflow with drift and calibration monitoring. It does not support automated trading or automatic generalisation to other ETFs.

## Paper and supporting evidence

- [`paper/main.pdf`](paper/main.pdf): submitted paper.
- [`CHANGELOG.md`](CHANGELOG.md): dated record of repository and paper revisions.
- [`notebooks/ETF_Project_Complete_Steps_1_to_8.ipynb`](notebooks/ETF_Project_Complete_Steps_1_to_8.ipynb): complete executed workflow with saved outputs.
- [`logs/verification_summary.txt`](logs/verification_summary.txt): successful reproduction summary.
- [`outputs/ETF_Model_Comparison_Predictions_2022_to_2026.csv`](outputs/ETF_Model_Comparison_Predictions_2022_to_2026.csv): row-level holdout scores and alert flags.
- [`outputs/ETF_Walk_Forward_Predictions.csv`](outputs/ETF_Walk_Forward_Predictions.csv): row-level walk-forward predictions.
- [`outputs/ETF_Logistic_Standardized_Coefficients.csv`](outputs/ETF_Logistic_Standardized_Coefficients.csv): fold-specific standardized coefficients from each selected logistic model.
- [`docs/EXPLAINABILITY_RESULTS.md`](docs/EXPLAINABILITY_RESULTS.md): interpretation limits and the paper's coefficient-table audit trail.
- [`outputs/ETF_Block_Bootstrap_Intervals.csv`](outputs/ETF_Block_Bootstrap_Intervals.csv): block-bootstrap uncertainty intervals.
- [`outputs/ETF_Paired_PR_AUC_Differences.csv`](outputs/ETF_Paired_PR_AUC_Differences.csv): paired model-comparison intervals.
- [`outputs/ETF_Label_Sensitivity_Metrics.csv`](outputs/ETF_Label_Sensitivity_Metrics.csv): fold-level label-sensitivity results.
- [`outputs/ETF_Alert_Budget_Fold_Metrics.csv`](outputs/ETF_Alert_Budget_Fold_Metrics.csv): fold-level 5%, 10% and 20% alert results.
- [`outputs/ETF_Feature_Ablation_Deltas.csv`](outputs/ETF_Feature_Ablation_Deltas.csv): PR-AUC, Brier-score and alert-precision changes relative to gap history.
- [`outputs/ETF_Temporal_Shift_Calibration.csv`](outputs/ETF_Temporal_Shift_Calibration.csv): Brier score, calibration intercept/slope and five-bin ECE.
- [`outputs/ETF_Temporal_Shift_Locked_Alerts.csv`](outputs/ETF_Temporal_Shift_Locked_Alerts.csv): validation-locked cutoff performance and test alert rates.
- [`outputs/ETF_Dislocation_Size_by_Alert.csv`](outputs/ETF_Dislocation_Size_by_Alert.csv): next-session gap magnitude on alerted and non-alerted dates.
- [`outputs/ETF_NAV_Timing_Stress_Summary.csv`](outputs/ETF_NAV_Timing_Stress_Summary.csv): walk-forward results when only the preceding trading date's NAV is available.
- [`outputs/ETF_Gradient_Boosting_Metrics.csv`](outputs/ETF_Gradient_Boosting_Metrics.csv): validation-tuned histogram gradient-boosting results.
- [`outputs/model_results.json`](outputs/model_results.json): machine-readable metrics, tuning results, calibration and feature explanations.

### Paper-table reproduction map

| Paper table | Reproducible repository evidence |
|---|---|
| Table I — source reconciliation | `outputs/modeling_dataset_summary.json` and the processed data audits |
| Table II — walk-forward folds and validation events | `outputs/walk_forward_results.json` (`fold_audit`) and `outputs/ETF_Walk_Forward_Metrics.csv` |
| Table III — test PR-AUC | `outputs/ETF_Walk_Forward_Metrics.csv` |
| Table IV — pooled alert precision | `outputs/ETF_Alert_Budget_Summary.csv` |
| Table V — standardized logistic coefficients | `outputs/ETF_Logistic_Standardized_Coefficients.csv` |
| Table VI — dislocation magnitude | `outputs/ETF_Dislocation_Size_by_Alert.csv` and `outputs/dislocation_size_results.json` |
| Table VII — delayed-NAV and boosting robustness | `outputs/ETF_NAV_Timing_Stress_Summary.csv` and `outputs/ETF_Gradient_Boosting_Metrics.csv` |

Table II is a walk-forward split audit. It is not sourced from the feature-ablation outputs.

## AI-use disclosure

Generative AI assisted literature discovery, code drafting, language editing and formatting. The student authors selected the research design, reviewed the cited sources, verified the official data, executed the analysis and remain responsible for all interpretations and errors. No confidential personal data were supplied to the tools.

## Authors

- Ansh Kotwal — B2026006
- Anish Mayya — B2026005
- Rohit Agarwal — B2026037

Goa Institute of Management, PGDM Big Data Analytics.

## Licence and data terms

The analysis code is released under the MIT License. The included source-derived datasets remain subject to the terms of their respective publishers (NSE, NSE Indices and AMFI) and are not relicensed by this repository.


## Submitted paper and audit entry points

- Paper: [`paper/main.pdf`](paper/main.pdf)
- Complete notebook: [`notebooks/ETF_Project_Complete_Steps_1_to_8.ipynb`](notebooks/ETF_Project_Complete_Steps_1_to_8.ipynb)
- Reproduction instructions: [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md)
- Data provenance: [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md)
