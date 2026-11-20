# Explainability results

The term **explainable** refers first to the paper's primary warning score,
the current absolute price–NAV gap divided by its rolling abnormality
threshold. Both inputs are directly observable, the formula is fixed before
testing, and a higher score has a single operational meaning: today's gap is
closer to or beyond the recent abnormality boundary.

For a secondary classifier diagnostic, `scripts/07_walk_forward_validation.py`
also exports every standardized coefficient from the selected logistic model
in each walk-forward fold. Because the model is a `StandardScaler` followed by
logistic regression, coefficient magnitudes are comparable within a fold.
They should not be interpreted causally, and correlated predictors can produce
offsetting coefficients.

## Selected 2026-fold logistic model

The classifier was trained through 2024, tuned on 2025 and tested once on
2026. The selected regularization value was `C = 0.1`.

| Absolute rank | Feature | Standardized coefficient |
|---:|---|---:|
| 1 | Log ETF turnover | +0.389 |
| 2 | One-day India VIX change | -0.245 |
| 3 | India VIX level | +0.216 |
| 4 | Delivery percentage | +0.174 |
| 5 | One-day signed dislocation lag | +0.136 |

Positive coefficients increase the fitted log-odds after holding the other
standardized features fixed; negative coefficients decrease them. The mix of
turnover, volatility and lagged gap features is consistent with the paper's
feature-ablation finding that market-stress information can help logistic
ranking, while it does not establish a causal mechanism.

The complete audit table is
`outputs/ETF_Logistic_Standardized_Coefficients.csv`.
