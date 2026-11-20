# Model card

## Intended use

Rank NIFTYBEES trading dates by the risk of an abnormally large next-day price–NAV dislocation so an analyst can prioritise review.

## Users

Students, researchers, ETF analysts and risk-monitoring teams studying transparent early-warning systems.

## Not intended for

- Automatic trade execution.
- Claims of risk-free arbitrage.
- Forecasting general NIFTY 50 returns.
- Automatic application to another ETF without rebuilding its NAV, benchmark and trading-history panel.

## Inputs

Twenty-five features available after date-*t* close and NAV publication, including price–NAV gaps, returns, liquidity, delivery activity, NIFTY 50 movement and India VIX.

## Output

Each classifier produces a next-day risk score or probability. Operational evaluation ranks dates and flags only the highest-scored 10%.

## Validation

Chronological training: 2022–2024 targets. Validation: 2025 targets. Untouched test: 2026 targets through 16 November.

## Main findings

Random forest was validation-selected, but the current-gap rule achieved the strongest test PR-AUC. Logistic regression had the best test Brier score among the classifiers. This makes the transparent rule the preferred ranking benchmark and logistic regression the preferred probability model.

At the 10% gap-ratio budget, alerted dates have a 6.00-bps larger mean
next-session absolute dislocation than non-alerted dates (bootstrap 95% CI:
2.84–9.45 bps). When the current official NAV is delayed by one trading day,
the gap ratio and random forest are effectively tied and overall performance
falls. Timely NAV availability is therefore a material operating assumption.
Supplementary histogram gradient boosting does not improve the main ranking.

## Monitoring requirements

- Track event prevalence, alert volume and score distribution.
- Recalculate calibration diagnostics on a documented schedule.
- Review special trading sessions and extreme values manually.
- Retrain only after an approved drift or scheduled-review trigger.
- Preserve an untouched future holdout for each material model update.
- Record the actual NAV publication timestamp and activate the delayed-NAV
  fallback whenever the current official NAV is unavailable.

## Ethical and practical considerations

Feature importance and regression coefficients describe predictive associations, not causal effects. Alerts should initiate analyst review rather than trigger an automatic trade.
