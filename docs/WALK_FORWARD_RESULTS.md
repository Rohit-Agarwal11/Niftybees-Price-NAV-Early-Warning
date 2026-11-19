# Step 2 — Purged walk-forward evaluation

## Design

Three expanding-window folds were evaluated. Classifier hyperparameters were selected using validation PR-AUC only; the subsequent calendar period was tested once. Samples were assigned by target date, and any prior sample whose label reached the next partition's feature date was purged.

| Fold | Training | Validation | Test | Test rows | Test events |
|---|---|---|---|---:|---:|
| 1 | Through 2022 | 2023 | 2024 | 242 | 26 |
| 2 | Through 2023 | 2024 | 2025 | 246 | 5 |
| 3 | Through 2024 | 2025 | 2026 through 16 Nov | 214 | 34 |

Random forest achieved the highest validation PR-AUC among the classifiers in all three folds. It did not win any subsequent test fold.

## Test stability summary

| Model | Mean PR-AUC | SD | Minimum | Maximum | Fold wins | Mean precision @10% | Mean lift @10% |
|---|---:|---:|---:|---:|---:|---:|---:|
| Current gap ratio | **0.233** | 0.102 | 0.116 | 0.293 | **2** | **26.8%** | **3.19x** |
| Current absolute gap | 0.218 | 0.081 | 0.125 | 0.277 | 1 | 22.4% | 2.88x |
| Random forest | 0.184 | 0.100 | 0.077 | 0.274 | 0 | 18.1% | 2.56x |
| Logistic regression | 0.169 | 0.120 | 0.035 | 0.267 | 0 | 18.6% | 1.41x |
| Decision tree | 0.156 | 0.053 | 0.100 | 0.206 | 0 | 20.9% | 3.85x |
| Previous-event persistence | 0.154 | 0.085 | 0.056 | 0.214 | 0 | 27.9% | 3.88x |
| Historical prevalence | 0.096 | 0.070 | 0.020 | 0.159 | 0 | 9.6% expected | 1.00x |

## Interpretation

The current gap-to-threshold ratio is the strongest and most consistent ranking method in this three-fold comparison. It has the highest mean test PR-AUC, wins two test folds and provides mean alert precision of 26.8% under a 10% review budget. Its average alert lift is 3.19, meaning flagged dates contain abnormal events at approximately 3.19 times the unconditional rate within the corresponding test periods.

The result supports H1: current price–NAV dislocation information persists into next-day abnormal-event risk. It also supports H3: the tested nonlinear classifiers do not consistently outperform the transparent rule. Random forest is validation-selected in all three folds but does not win a subsequent test period.

The results also support the temporal-shift concern in H4. Test event prevalence changes sharply across years: 10.74% in 2024, 2.03% in 2025 and 15.89% in 2026. Model rankings and probability quality therefore vary materially by period.

## Important limitation

The 2023 validation period contains only two abnormal events, and the 2025 validation period contains five. Hyperparameter selection is therefore uncertain. Step 3 will use paired moving-block bootstrap confidence intervals to quantify uncertainty around PR-AUC and alert performance before any claim of model superiority is made.

## Reproducible evidence

- `scripts/07_walk_forward_validation.py`
- `outputs/ETF_Walk_Forward_Validation.xlsx`
- `outputs/ETF_Walk_Forward_Metrics.csv`
- `outputs/ETF_Walk_Forward_Predictions.csv`
- `outputs/ETF_Walk_Forward_Tuning.csv`
- `outputs/walk_forward_results.json`
- `figures/ETF_Walk_Forward_PR_AUC.png`
- `figures/ETF_Walk_Forward_Stability.png`
