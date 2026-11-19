# Methodology

## Observation and timestamp

One row represents one NIFTYBEES trading date. The forecast is produced after the official NAV for date *t* becomes available. At that point the ETF close, trading activity, NIFTY 50 close, India VIX and NAV for date *t* are known. The target concerns the next actual NSE trading session.

## Price–NAV dislocation

`Price_NAV_Dislocation_Pct = 100 × (ETF_Close − NAV) / NAV`

Positive values represent a premium and negative values a discount. The event definition uses the absolute magnitude.

## Prospective event label

The threshold at date *t* is the 95th percentile of the 252 complete absolute dislocations ending on *t*. The target is 1 if the next market session's absolute dislocation exceeds that threshold.

This construction ensures that the future target cannot influence its own threshold. A row enters modelling only when:

1. A full 252-observation history exists.
2. The next actual NSE market session has a complete target.
3. Every selected predictor is available by the prediction timestamp.
4. It is not the single overlapping label interval at a chronological split boundary.

## Predictors

The 25 predictors cover:

- Current and lagged signed/absolute dislocation.
- Rolling 5-day and 20-day dislocation summaries.
- ETF, NAV and NIFTY 50 returns.
- ETF-minus-index tracking-return difference.
- India VIX level and changes.
- Volume, turnover, delivery percentage, average trade value and intraday range.

Log transforms are applied to volume and turnover. Standardisation occurs inside the logistic-regression pipeline and is fitted on training data only.

## Models

- Current-gap rule: current absolute gap divided by the rolling 95th-percentile threshold.
- Logistic regression: L2 regularisation; `C` selected from 0.01, 0.1, 1 and 10.
- Decision tree: bounded depth, minimum leaf size and optional class weighting selected on validation data.
- Random forest: 400 trees with a modest grid for depth, leaf size, feature sampling and class weighting.

All stochastic estimators use random seed 42.

## Selection and evaluation

Classifier selection uses validation PR-AUC only, with Brier score as a tie-breaker. The test period is not used for hyperparameter selection, feature selection or alert-threshold selection.

Reported evaluation includes PR-AUC, ROC-AUC, Brier score, log loss, calibration intercept/slope, five-bin expected calibration error, and precision/recall under a 10% review budget.

## Limitations

The study covers one broad-market ETF. Closing data do not capture intraday arbitrage, bid–ask spreads, order-book depth, authorised participant flows, transaction costs or creation/redemption activity. Only five abnormal events occur in validation, so model selection and calibration estimates are uncertain. The 2026 test period has a much higher event rate, showing that market conditions can shift materially.
