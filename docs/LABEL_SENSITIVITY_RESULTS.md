# Label-definition sensitivity results

## Question

Does the model ranking remain stable when an abnormal next-day price–NAV dislocation is defined differently?

The analysis follows the definitions frozen in `docs/ANALYSIS_PLAN_V2.md`:

- rolling 90th percentile of the previous 252 complete observations;
- rolling 95th percentile, the primary definition;
- rolling 97.5th percentile;
- fixed next-day absolute dislocation above 0.50%; and
- fixed next-day absolute dislocation above 1.00%.

For every rolling definition, the threshold is calculated through prediction date *t*. The target date *t+1* never contributes to its own threshold. The current-gap ratio and event-persistence benchmark are recalculated using the threshold for the scenario being tested. Classifier hyperparameters are retuned using validation data only in every scenario and fold.

## Event availability and feasibility

| Label definition | Events in 1,185 observations | Feasible walk-forward folds | Assessment |
|---|---:|---:|---|
| Rolling 90th percentile | 138 | 3 of 3 | Feasible |
| Rolling 95th percentile | 80 | 3 of 3 | Feasible |
| Rolling 97.5th percentile | 41 | 3 of 3 | Feasible but fragile |
| Fixed 0.50% | 12 | 0 of 3 | Infeasible |
| Fixed 1.00% | 2 | 0 of 3 | Infeasible |

The fixed definitions cannot support the prespecified model-comparison procedure. At least one validation or test partition has no positive event in every fold. Training or selecting a classifier under those conditions would produce misleading results, so the analysis reports their event counts and infeasibility rather than forcing estimates.

The rolling 97.5th-percentile analysis passes the minimum two-class rule, but Fold 2 has only one event in its test set and some validation periods also have one event. Its model ranking is therefore highly sensitive to the position of individual observations.

## Mean walk-forward test performance

| Rolling label | Current gap ratio | Logistic regression | Decision tree | Random forest | Highest mean PR-AUC |
|---|---:|---:|---:|---:|---|
| 90th percentile | 0.289 | 0.266 | 0.222 | **0.299** | Random forest |
| 95th percentile | **0.233** | 0.169 | 0.156 | 0.184 | Current gap ratio |
| 97.5th percentile | 0.284 | 0.122 | 0.130 | **0.286** | Random forest |

The headline winner changes with the event definition. Random forest leads the 90th-percentile case by only **0.010 PR-AUC** and the 97.5th-percentile case by only **0.002 PR-AUC**. The current gap ratio leads the primary 95th-percentile case by **0.049 PR-AUC** over random forest.

These are point-estimate rankings. The 97.5th-percentile difference is especially uninformative because one test fold contains only a single event. The earlier paired bootstrap analysis also showed that the primary gap-ratio difference over random forest was not established at the 95% level.

## Operational performance at a 10% alert budget

| Rolling label | Model | Mean precision | Mean recall | Mean lift |
|---|---|---:|---:|---:|
| 90th percentile | Current gap ratio | **35.2%** | **31.1%** | **3.04×** |
| 90th percentile | Random forest | 32.5% | 26.3% | 2.57× |
| 95th percentile | Current gap ratio | **26.8%** | **32.7%** | **3.19×** |
| 95th percentile | Random forest | 18.1% | 26.2% | 2.56× |
| 97.5th percentile | Current gap ratio | **21.1%** | **63.4%** | **6.19×** |
| 97.5th percentile | Random forest | 12.7% | 49.9% | 4.89× |

Although random forest has the highest mean PR-AUC for two alternative rolling labels, the gap ratio has higher mean precision, recall and lift under the fixed 10% review budget in all three rolling-label analyses.

## Interpretation

The exact PR-AUC winner is sensitive to the abnormal-event definition. Therefore, the report should not state that one model is universally best. The more robust conclusion is that additional model complexity does not provide a consistent or practically large advantage over the transparent gap-ratio rule. The gap ratio remains first or a close second in every feasible rolling-label analysis and provides the strongest operational alert results.

The fixed 0.50% and 1.00% definitions also show that economically large daily price–NAV dislocations are too rare in this single-ETF sample for dependable supervised model comparison. A future fixed-threshold study would need more ETFs, a longer history or both.

## Recommended report wording

> Model ranking varies with the abnormal-event definition. Random forest records marginally higher mean PR-AUC under the rolling 90th- and 97.5th-percentile labels, while the current gap ratio leads under the primary 95th-percentile label. The random-forest margins are small, and the 97.5th-percentile result is based on extremely sparse validation and test events. Across all feasible rolling definitions, the transparent gap ratio delivers higher precision, recall and lift at the 10% alert budget. The evidence therefore does not show a consistent practical advantage from added model complexity.
