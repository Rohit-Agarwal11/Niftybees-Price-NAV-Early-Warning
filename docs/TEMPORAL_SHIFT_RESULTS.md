# Temporal-shift and calibration diagnostics

## Question

Do changes in abnormal-event prevalence and predictor distributions alter model ranking, probability calibration and operational alert volume across untouched test years?

This analysis implements the temporal-shift diagnostics frozen in Section 13 of `ANALYSIS_PLAN_V2.md`. Every classifier uses the hyperparameters selected on the preceding validation period. Validation score cutoffs are then locked and applied unchanged to the subsequent test year.

## Outcome regimes

| Test year | Observations | Events | Event prevalence | Median absolute dislocation | 95th percentile |
|---|---:|---:|---:|---:|---:|
| 2024 | 242 | 26 | 10.74% | 0.119% | 0.274% |
| 2025 | 246 | 5 | 2.03% | 0.110% | 0.193% |
| 2026 through 16 November | 214 | 34 | 15.89% | 0.123% | 0.361% |

Event prevalence changes by a factor of 7.8 between the lowest- and highest-prevalence years. The tail of the absolute-dislocation distribution also contracts in 2025 and expands in 2026.

## Ranking stability

| Model | 2024 PR-AUC | 2025 PR-AUC | 2026 PR-AUC |
|---|---:|---:|---:|
| Historical prevalence | 0.107 | 0.020 | 0.159 |
| Current absolute gap | 0.251 | **0.125** | 0.277 |
| Current gap ratio | **0.293** | 0.116 | **0.290** |
| Previous-event persistence | 0.214 | 0.056 | 0.191 |
| Logistic regression | 0.205 | 0.035 | 0.267 |
| Decision tree | 0.160 | 0.100 | 0.206 |
| Random forest | 0.274 | 0.077 | 0.202 |

The gap ratio leads in 2024 and 2026, while the current absolute gap leads in 2025. No classifier wins a test year. The random forest falls from 0.274 in 2024 to 0.077 in 2025, and logistic regression falls from 0.205 to 0.035 before recovering to 0.267 in 2026.

## Probability calibration

| Test year | Logistic: mean probability / event rate | Tree: mean probability / event rate | Forest: mean probability / event rate | Best classifier Brier score |
|---|---:|---:|---:|---:|
| 2024 | 32.32% / 10.74% | 21.15% / 10.74% | 4.52% / 10.74% | Random forest: 0.094 |
| 2025 | 2.80% / 2.03% | 18.85% / 2.03% | 10.38% / 2.03% | Logistic: 0.021 |
| 2026 | 15.12% / 15.89% | 11.20% / 15.89% | 24.78% / 15.89% | Logistic: 0.134 |

Logistic regression is close in mean calibration in 2025 and 2026, but substantially overpredicts in 2024. Its calibration slopes are 0.516, 0.372 and 0.355, all below one, indicating that its probability spread is too extreme. The random forest changes from underprediction in 2024 to overprediction in 2025 and 2026. A single fixed probability interpretation is therefore unsafe across regimes.

## Locked alert volume

The score cutoff that selected approximately the highest 10% of validation observations was applied unchanged to the following test year.

| Test year | Lowest test alert rate | Highest test alert rate | Intended rate |
|---|---:|---:|---:|
| 2024 | 15.7% | 28.1% | 10% |
| 2025 | 0.0% | 5.3% | 10% |
| 2026 | 22.9% | 39.3% | 10% |

The ranges exclude the constant historical-prevalence benchmark and the binary persistence rule, for which a percentile cutoff is not operationally meaningful because of complete score ties. In 2025, the locked logistic cutoff issues no alerts. In 2026, the locked gap-ratio cutoff alerts 39.3% of observations. This demonstrates that a fixed score cutoff does not preserve workload when score distributions change.

## Predictor and score shifts

Population Stability Index (PSI) compares each validation distribution with its subsequent test distribution. Values below 0.10 are labelled low, 0.10–0.25 moderate and at least 0.25 large. These thresholds are monitoring heuristics, not significance tests.

| Test year | Median predictor PSI | Predictors ≥0.10 | Predictors ≥0.25 | Largest predictor PSI |
|---|---:|---:|---:|---:|
| 2024 | 0.141 | 18 of 25 | 7 of 25 | 2.171 |
| 2025 | 0.191 | 23 of 25 | 8 of 25 | 2.778 |
| 2026 | 0.222 | 22 of 25 | 12 of 25 | 3.110 |

The largest changes repeatedly occur in 20-day dislocation variability, turnover, volume, the VIX level and the current gap-to-threshold ratio. Classifier score PSI is large for logistic regression in 2024 and 2025, for random forest in all three folds, and for the decision tree in 2026.

## Interpretation of H4

H4 is **supported**. Event prevalence, predictor distributions and model-score distributions change materially across test years. These changes coincide with unstable rankings, probability miscalibration and large deviations from the intended alert volume.

The operational implication is that the system should rank a fixed review capacity, such as the highest-scored 10% of dates, rather than use a permanent probability or score cutoff. Probability models require periodic calibration checks, and PSI, event prevalence, Brier score and alert rate should be monitored after deployment.

## Recommended report wording

> Temporal diagnostics support H4. Abnormal-event prevalence changes from 10.7% in 2024 to 2.0% in 2025 and 15.9% in 2026, while median predictor PSI rises from 0.141 to 0.222. Model rankings and probability calibration change with these regimes. Validation-locked 10% score cutoffs generate only 0.0%–5.3% alerts in 2025 but 22.9%–39.3% in 2026. The evidence favours capacity-based ranking with ongoing drift and calibration monitoring over permanent score thresholds.

## Limitations

The study contains only three out-of-time test periods, and 2025 contains five abnormal events. PSI depends on binning and is descriptive. The results diagnose temporal instability for NIFTYBEES; they do not establish the same pattern for other ETFs.
