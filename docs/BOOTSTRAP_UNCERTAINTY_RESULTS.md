# Paired moving-block bootstrap uncertainty

## Purpose

The walk-forward comparison gives point estimates, but the number of abnormal events changes substantially across years. This analysis measures the uncertainty around those estimates while preserving short-range time dependence and the paired nature of the model comparison.

## Prespecified method

- The three untouched walk-forward test folds are resampled separately.
- Circular moving blocks preserve local sequences of trading observations.
- The primary block length is 5 observations; 10 observations is a sensitivity check.
- Each analysis uses 2,000 valid resamples and the seed `42 + block length`.
- The same resampled indices are applied to every model within a fold. Differences are therefore paired.
- Resamples without both outcome classes in every fold are rejected and redrawn.
- The reported statistic is the equal-weight mean of the three fold-specific metrics.
- Percentile 95% confidence intervals are reported.
- For alert metrics, the highest-scoring 10% of dates are flagged within each resample.

This procedure is implemented in `scripts/08_block_bootstrap_uncertainty.py`. Machine-readable results are in `outputs/block_bootstrap_results.json`.

## Primary five-observation block results

| Model | Observed mean PR-AUC | 95% interval |
|---|---:|---:|
| Current gap ratio | **0.233** | 0.160–0.349 |
| Current absolute gap | 0.218 | 0.145–0.330 |
| Random forest | 0.184 | 0.139–0.281 |
| Logistic regression | 0.169 | 0.120–0.250 |
| Decision tree | 0.156 | 0.109–0.226 |
| Previous-event persistence | 0.154 | 0.099–0.235 |
| Historical prevalence | 0.096 | 0.070–0.122 |

The current gap ratio has the highest observed mean PR-AUC, but its marginal interval overlaps those of the classifiers. Marginal interval overlap is descriptive; the paired differences below provide the direct comparisons.

## Paired comparisons

The difference is the current gap ratio PR-AUC minus the classifier PR-AUC.

| Comparator | Observed difference | Paired 95% interval | Bootstrap share above zero | 95% conclusion |
|---|---:|---:|---:|---|
| Logistic regression | +0.064 | -0.012–0.164 | 94.7% | Superiority not established |
| Decision tree | **+0.078** | **0.019–0.168** | 99.5% | Gap ratio is higher |
| Random forest | +0.049 | -0.024–0.128 | 90.0% | Superiority not established |

Only the comparison with the decision tree excludes zero at the 95% level. The observed ranking favours the gap ratio, but the evidence is insufficient to claim statistically established superiority over logistic regression or random forest.

## Operational uncertainty

At a 10% alert budget, the current gap ratio has mean precision of **26.8%** with a 95% interval of **16.4%–37.2%**. Mean recall is **32.7%**, with a 95% interval of **16.2%–51.7%**. The wide intervals show that alert performance remains uncertain across the limited event sample.

## Block-length sensitivity

Using 10-observation blocks does not change the substantive conclusion. The paired interval excludes zero only against the decision tree:

| Comparator | Paired 95% interval with 10-observation blocks |
|---|---:|
| Logistic regression | -0.011–0.161 |
| Decision tree | **0.023–0.164** |
| Random forest | -0.029–0.125 |

## Defensible interpretation

The transparent current gap ratio is the strongest observed ranking rule and is more reliable than the bounded decision tree in this sample. The study cannot yet conclude that it is superior to logistic regression or random forest at the 95% level. This qualified finding is stronger than reporting point estimates alone because it distinguishes an observed ranking from an uncertainty-supported comparison.
