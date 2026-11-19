# Reproduced results

## Data reconciliation

- 1,456 NIFTYBEES market observations.
- 1,451 official AMFI NAV observations.
- 1,446 complete merged observations.
- 1,185 leakage-safe modelling forecasts.
- 80 abnormal next-day events.

## Test metrics

| Model | PR-AUC | ROC-AUC | Brier | ECE |
|---|---:|---:|---:|---:|
| Historical prevalence | 0.159 | 0.500 | 0.144 | 0.102 |
| Current-gap rule | 0.290 | 0.642 | — | — |
| Logistic regression | 0.267 | 0.543 | 0.134 | 0.079 |
| Decision tree | 0.206 | 0.605 | 0.152 | 0.094 |
| Random forest | 0.202 | 0.599 | 0.162 | 0.118 |

## Ten-percent test alert budget

| Model | Alerts | Events found | Precision | Recall |
|---|---:|---:|---:|---:|
| Current-gap rule | 22 | 8 | 36.4% | 23.5% |
| Logistic regression | 22 | 7 | 31.8% | 20.6% |
| Decision tree | 22 | 5 | 22.7% | 14.7% |
| Random forest | 22 | 4 | 18.2% | 11.8% |

The current-gap rule provided the strongest test ranking. Logistic regression provided the best probability quality among the classifiers. Random forest's validation advantage did not generalise to the 2026 test period.
