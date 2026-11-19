# Feature-group ablation results

## Question

Do market-stress and liquidity variables add out-of-time predictive value beyond current and historical price–NAV gap information?

Each classifier was retuned using validation PR-AUC separately for every feature group and every purged walk-forward fold. The subsequent test period remained untouched during tuning.

## Feature groups

| Feature group | Predictors | Included information |
|---|---:|---|
| Gap only | 6 | Current signed and absolute gap, signed gap lags and premium indicator |
| Gap history | 10 | Gap-only variables plus 5-day and 20-day summaries and current gap-to-threshold ratio |
| Gap + market stress | 15 | Gap history plus NIFTY 50 returns and India VIX level and changes |
| Gap + liquidity | 16 | Gap history plus volume, turnover, average trade value, delivery and intraday range |
| Full | 25 | Every available predictor, including ETF and NAV return variables |

## Mean walk-forward test PR-AUC

| Feature group | Logistic regression | Decision tree | Random forest |
|---|---:|---:|---:|
| Gap only | 0.160 | **0.171** | 0.169 |
| Gap history | 0.153 | 0.153 | 0.178 |
| Gap + market stress | **0.195** | 0.160 | 0.173 |
| Gap + liquidity | 0.150 | 0.163 | 0.176 |
| Full 25 predictors | 0.169 | 0.156 | **0.184** |
| Current gap-ratio reference | **0.233** | **0.233** | **0.233** |

No classifier specification exceeds the transparent current gap-ratio reference. The strongest classifier is logistic regression with gap-history and market-stress variables, with mean PR-AUC of 0.195.

## Incremental value relative to gap history

| Added information | Model | PR-AUC change | Brier improvement | 10% precision change |
|---|---|---:|---:|---:|
| Market stress | Logistic regression | **+0.042** | +0.003 | **+8.5 percentage points** |
| Market stress | Decision tree | +0.007 | **+0.032** | +0.6 points |
| Market stress | Random forest | -0.005 | -0.016 | -1.5 points |
| Liquidity | Logistic regression | -0.003 | -0.012 | +3.0 points |
| Liquidity | Decision tree | +0.010 | -0.024 | +0.9 points |
| Liquidity | Random forest | -0.001 | +0.002 | +1.2 points |

A positive Brier improvement means lower probability error than the gap-history model.

## Consistency of the logistic market-stress result

Market stress increases logistic-regression PR-AUC in all three test folds:

| Test fold | Gap history | Gap + market stress | Difference |
|---|---:|---:|---:|
| 2024 | 0.222 | 0.272 | +0.051 |
| 2025 | 0.041 | 0.046 | +0.004 |
| 2026 | 0.196 | 0.267 | +0.071 |

The mean 10% alert precision increases from 15.4% to 23.9%. Mean Brier score improves only slightly, from 0.088 to 0.085, and the Brier improvement is not uniform across every fold. The evidence therefore supports a ranking contribution from market-stress variables within logistic regression more clearly than a broad probability-calibration improvement.

## Interpretation of H2

H2 receives **partial support**. NIFTY 50 and India VIX variables add consistent ranking information to the logistic-regression model. The same variables do not improve random forest, and their gain for the decision tree is small. Liquidity variables do not show consistent incremental PR-AUC or Brier improvement across classifiers.

The results do not support the claim that more variables automatically improve prediction. The decision tree performs best with only six gap variables. Random forest obtains its highest PR-AUC with all 25 predictors, but its mean of 0.184 remains below both the market-stress logistic model and the transparent gap-ratio rule.

## Recommended report wording

> Feature ablation provides partial support for incremental market information. Adding NIFTY 50 and India VIX variables to gap-history features raises logistic-regression mean walk-forward PR-AUC from 0.153 to 0.195, with improvement in all three test folds. Liquidity variables do not produce consistent gains across classifiers. No classifier feature set exceeds the transparent current gap-ratio reference of 0.233. These results suggest that market-stress information can improve a parsimonious linear risk model, while unrestricted feature expansion does not reliably improve out-of-time performance.

## Limitations

The feature blocks are evaluated for predictive contribution, not causal effects. Correlated variables can redistribute apparent importance across a group. The comparison covers one ETF and three test periods, so small differences should not be described as universal superiority.
