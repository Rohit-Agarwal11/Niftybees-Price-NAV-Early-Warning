# Additional robustness and operational-value results

These analyses were added after the primary design and therefore supplement,
rather than replace, the frozen walk-forward results. The event definition,
fold boundaries, purging rule and random seed remain unchanged.

## Size of next-session dislocations

The primary gap-ratio score flags the highest-ranked 10% of dates separately
within each untouched test fold. The table measures the next-session absolute
price–NAV dislocation in basis points.

| Group | Dates | Events | Mean | Median | 90th percentile | 95th percentile |
|---|---:|---:|---:|---:|---:|---:|
| Not alerted | 630 | 46 | 12.49 bps | 11.33 bps | 21.18 bps | 26.61 bps |
| Alerted | 72 | 19 | 18.49 bps | 17.20 bps | 36.56 bps | 43.34 bps |

The mean difference is **6.00 bps**. A 5,000-resample stratified
nonparametric bootstrap gives a 95% interval of **2.84 to 9.45 bps**. The
median difference is **5.87 bps**, with a 95% interval of **1.83 to 8.06 bps**.
This shows that the screen identifies larger dislocations, not merely a higher
share of binary events.

## One-trading-day delayed-NAV stress test

The delayed scenario assumes that the date-*t* ETF close and other market data
are known, but the latest official NAV is from date *t−1*. Gap, rolling-gap and
NAV-return features are rebuilt from that information. Each classifier is then
retuned using the same prior-year validation partition.

| Model | Mean PR-AUC | Range across folds | Mean 10% precision | Mean 10% recall |
|---|---:|---:|---:|---:|
| Current gap ratio | 0.160 | 0.038–0.226 | 17.1% | 19.0% |
| Logistic regression | 0.148 | 0.107–0.218 | 14.4% | 21.8% |
| Decision tree | 0.110 | 0.057–0.156 | 14.4% | 21.8% |
| Random forest | 0.161 | 0.051–0.272 | 18.1% | 20.8% |

Performance falls relative to the current-NAV analysis, and the gap ratio and
random forest become effectively tied. Timely official NAV availability is
therefore a material operating assumption. The result does not justify an
unchanged-ranking robustness claim.

## Histogram gradient boosting

A supplementary `HistGradientBoostingClassifier` was tuned on validation
PR-AUC with Brier score as the tie-breaker. The grid covers learning rates
0.05/0.10, 7/15 leaf nodes and L2 penalties 0/1.

| Test year | PR-AUC | 10% precision | Events found |
|---|---:|---:|---:|
| 2024 | 0.185 | 12.0% | 3 of 26 |
| 2025 | 0.037 | 0.0% | 0 of 5 |
| 2026 | 0.212 | 27.3% | 6 of 34 |
| **Mean** | **0.145** | **13.1%** | — |

Gradient boosting does not improve on the transparent current gap ratio's
0.233 mean PR-AUC. This closes the original proposal's model-comparison gap
without changing the central conclusion.

## Reproducible files

- `scripts/15_dislocation_size_analysis.py`
- `scripts/16_nav_timing_stress_test.py`
- `scripts/17_operational_timeline_figure.py`
- `scripts/18_gradient_boosting_comparison.py`
- `outputs/ETF_Dislocation_Size_by_Alert.csv`
- `outputs/ETF_Dislocation_Size_Bootstrap.csv`
- `outputs/ETF_NAV_Timing_Stress_Metrics.csv`
- `outputs/ETF_NAV_Timing_Stress_Summary.csv`
- `outputs/ETF_Gradient_Boosting_Metrics.csv`
- `outputs/ETF_Gradient_Boosting_Tuning.csv`
- `figures/ETF_Dislocation_Size_by_Alert.png`
- `figures/ETF_NAV_Timing_Stress_PR_AUC.png`
- `figures/ETF_Operational_Timeline.png`
