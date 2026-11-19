# Alert-budget sensitivity results

## Purpose

The project is an operational screening system. An analyst cannot review every trading date, so the relevant question is how many abnormal next-day dislocations are captured when alerts are limited to a fixed share of the highest-scored dates.

The analysis uses the untouched test predictions from all three purged walk-forward folds and the primary rolling 95th-percentile event definition. Budgets of 5%, 10% and 20% were prespecified in `docs/ANALYSIS_PLAN_V2.md`.

## Tie handling

The current gap ratio, current absolute gap, logistic regression and random forest provide essentially continuous rankings at the tested cutoffs. Historical prevalence, the binary persistence rule and some decision-tree outputs contain large score ties.

For a tied cutoff, the primary calculation:

1. selects every observation strictly above the cutoff;
2. calculates the remaining alert capacity;
3. assigns the expected number of positives from the tied group to those remaining slots.

This prevents chronological row order from deciding the reported performance of tied scores. The exact stable-order count is retained in the fold-level audit but is not used as the primary comparison.

## Current gap-ratio trade-off

Across 702 test observations containing 65 abnormal events:

| Alert budget | Alerts | Events identified | Precision | Recall | Lift | Number needed to review |
|---:|---:|---:|---:|---:|---:|---:|
| 5% | 37 | 11 | **29.7%** | 16.9% | **3.21×** | **3.36** |
| 10% | 72 | 19 | **26.4%** | 29.2% | **2.85×** | **3.79** |
| 20% | 142 | 27 | **19.0%** | 41.5% | **2.05×** | **5.26** |

The expected no-skill precision is approximately 9.3%. The gap-ratio rule remains above twice the no-skill rate even when 20% of dates are reviewed.

## Comparison with other models

| Budget | Highest-precision method | Precision | Next-best precision | Random-forest precision |
|---:|---|---:|---:|---:|
| 5% | Current gap ratio | **29.7%** | 27.0%, current absolute gap | 18.9% |
| 10% | Current gap ratio | **26.4%** | 23.8%, persistence rule | 18.1% |
| 20% | Current gap ratio | **19.0%** | 18.3%, current absolute gap | 16.9% |

The current gap ratio ranks first by pooled precision at every tested budget. This result is more operationally stable than relying on a single 10% capacity assumption.

## Diminishing returns

- Increasing the budget from 5% to 10% adds 35 alerts and identifies 8 additional events. The marginal precision of the extra alerts is **22.9%**.
- Increasing the budget from 10% to 20% adds 70 alerts but identifies the same 8 additional events. Marginal precision falls to **11.4%**, only modestly above the pooled event prevalence of 9.3%.

The 5% budget is suitable when analyst time is highly constrained and precision matters most. The 20% budget captures more events but requires reviewing almost twice as many additional dates for each extra event. The primary 10% budget provides a reasonable balance between review workload and event coverage.

## Recommended report wording

> The current gap-ratio rule remains the highest-precision screening method under 5%, 10% and 20% alert budgets. At the primary 10% budget, it flags 72 of 702 walk-forward test dates and identifies 19 of 65 abnormal events, producing 26.4% pooled precision, 29.2% recall and 2.85 times lift over prevalence. Expanding the budget to 20% raises recall to 41.5% but reduces precision to 19.0%. The marginal yield of alerts beyond the 10% budget falls sharply, supporting 10% as a practical monitoring capacity rather than an outcome-optimized threshold.

## Limitations

The alert budget is an assumed review capacity rather than an observed staffing constraint. Results measure event identification, not investment profitability. They do not incorporate transaction costs, intraday execution or the financial cost of false positives and missed events.
