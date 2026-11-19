# Frozen analysis plan for the enhanced final submission

**Frozen on:** 17 November 2026  
**Study security:** NIFTYBEES, NSE series EQ  
**Study period:** 1 January 2021 to 16 November 2026  
**Purpose:** Strengthen the second-review study through prespecified robustness and temporal-stability analyses.

This plan was written after the initial train/validation/test analysis and before executing the additional walk-forward, bootstrap, label-sensitivity, ablation and alert-budget analyses. All prespecified results will be reported, including weak, negative and inconclusive findings.

## 1. Revised title

**Does Model Complexity Improve Next-Day Price–NAV Dislocation Warnings? A Leakage-Controlled Walk-Forward Study of NIFTYBEES**

## 2. Decision problem

After the official NAV for trading date *t* becomes available, an analyst must decide which dates deserve additional review for the risk of an abnormally large NIFTYBEES price–NAV dislocation on the next actual NSE trading session.

The system is a risk-screening tool. It does not forecast general equity returns, prove an executable arbitrage opportunity or automatically recommend a trade.

## 3. Research questions

### Primary question

Do complex machine-learning models provide more reliable next-trading-day warnings of abnormal NIFTYBEES price–NAV dislocations than transparent benchmark rules when market conditions change over time?

### Secondary questions

1. Does the current price–NAV gap contain persistent information about next-day abnormal dislocation risk?
2. Do market-stress and liquidity variables add predictive value beyond gap-history variables?
3. Which model provides the most stable PR-AUC across walk-forward test periods?
4. Which probability model provides the most stable Brier score and calibration?
5. How sensitive are model rankings to the abnormal-event definition?
6. How does operational performance change under 5%, 10% and 20% alert budgets?

## 4. Hypotheses

### H1 — Persistence

Larger current price–NAV dislocations are associated with a higher probability of an abnormal dislocation on the next trading day.

### H2 — Incremental information

Market-stress and liquidity features provide predictive information beyond current and lagged price–NAV gap features.

### H3 — Complexity

Complex nonlinear classifiers do not consistently outperform transparent benchmark rules in out-of-time evaluation.

### H4 — Temporal shift

Changes in event prevalence and predictor distributions materially affect probability calibration and alert volume.

### H5 — Operational utility

Ranking dates under a limited alert budget identifies abnormal events at a higher rate than random review at the same capacity.

## 5. Primary outcome and label

The primary outcome remains the existing leakage-controlled label:

```text
Y(t+1) = 1 when absolute dislocation(t+1)
         exceeds the rolling 95th percentile of the
         252 complete observations ending on prediction date t.
```

The target date cannot influence its own threshold. Features use date *t* or earlier only. Samples are assigned by target date, and overlapping next-day label intervals are purged at chronological boundaries.

## 6. Models and benchmarks

The following approaches will be evaluated:

1. Historical-prevalence probability benchmark.
2. Current absolute-gap score.
3. Current-gap-to-rolling-threshold ratio.
4. Previous-event persistence rule.
5. L2-regularised logistic regression.
6. Bounded decision tree.
7. Random forest.

No neural network or highly flexible boosting model will be added because the primary dataset contains only 80 abnormal events.

## 7. Primary metric

PR-AUC is the primary ranking metric because abnormal events are uncommon. Supporting measures are:

- ROC-AUC
- Brier score
- Log loss
- Calibration intercept and slope
- Five-bin expected calibration error
- Precision, recall, lift and number needed to review at fixed alert budgets

## 8. Purged walk-forward design

Three expanding-window evaluations will be attempted:

| Fold | Training targets | Validation targets | Test targets |
|---|---|---|---|
| 1 | Through 2022 | 2023 | 2024 |
| 2 | Through 2023 | 2024 | 2025 |
| 3 | Through 2024 | 2025 | 2026 through 16 November |

At every fold:

- Samples are assigned by target date.
- One overlapping next-day interval is purged at each boundary.
- Preprocessing is fitted on training data only.
- Hyperparameters are selected on validation PR-AUC only, with Brier score as tie-breaker.
- Test labels are not used for feature, hyperparameter or threshold selection.
- A fold with an unusable class count will be reported as infeasible rather than silently removed.

## 9. Block-bootstrap uncertainty

- Resamples: 2,000
- Random seed: 42
- Primary block length: 5 consecutive trading observations
- Sensitivity block length: 10 observations
- Interval: percentile 95% confidence interval

Intervals will be reported for test PR-AUC, precision at 10%, recall at 10%, and paired PR-AUC differences between the current-gap ratio and each classifier.

## 10. Label sensitivity

The complete modelling pipeline will be evaluated under:

- Rolling 90th percentile
- Rolling 95th percentile, primary definition
- Rolling 97.5th percentile
- Fixed 0.50% next-day absolute dislocation
- Fixed 1.00% next-day absolute dislocation

Every analysis will report the available number of events. A threshold with insufficient positive observations will be labelled infeasible for model comparison.

## 11. Alert-budget sensitivity

Operational performance will be reported for the highest-scored:

- 5% of test dates
- 10% of test dates, primary setting
- 20% of test dates

Measures will include alerts, true positives, precision, recall, lift over event prevalence and number needed to review.

## 12. Feature-group ablation

| Feature group | Included information |
|---|---|
| Gap only | Current and lagged signed/absolute dislocations |
| Gap history | Gap-only plus rolling dislocation summaries and threshold ratio |
| Gap + market stress | Gap history plus NIFTY 50 and India VIX features |
| Gap + liquidity | Gap history plus volume, turnover, delivery and intraday-range features |
| Full | All 25 predictors |

The same chronological procedures and model settings will be used for every feature group.

## 13. Temporal-shift diagnostics

The study will report by year or fold:

- Abnormal-event prevalence
- Dislocation distribution
- Model PR-AUC
- Brier score for probability models
- Mean predicted probability
- Locked-threshold alert rate
- Predictor and score distribution changes

## 14. Interpretation rules

- Results will be described as predictive associations, not causal effects.
- A classifier will not be declared superior from a small point-estimate difference alone.
- Test results will not be used to revise model-selection rules.
- Overlapping bootstrap intervals will be described cautiously.
- Findings apply directly to NIFTYBEES only.
- Trading profitability will not be claimed without transaction-cost and execution evidence.

## 15. Planned contribution statement

First, the study formulates ETF price–NAV monitoring as a prospective next-trading-day warning problem using a defined post-NAV timestamp. Second, it compares complex classifiers with transparent benchmark rules using purged chronological and walk-forward evaluation. Third, it examines whether ranking, calibration and alert utility remain stable when abnormal-event prevalence changes over time.
