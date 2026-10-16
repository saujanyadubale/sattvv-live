# SAT-V&V v1.0.2 — Paired exploratory research pilot

**Interpretation:** These are software-only, synthetic verification campaigns. They are not flight-level validation, and the method was adjusted after an initial benchmark exposed a short-budget regression. All conclusions are exploratory.

## Exploratory mixed faults: paired seeds

| Strategy | 35 min (28 seeds) | 60 min (12 seeds) | 90 min (28 seeds) |
|---|---:|---:|---:|
| Fixed-order | 10/28* | 5/12 | 16/28 |
| Information gain | 16/28* | 6/12 | 16/28 |
| ML-ranked | 15/28* | 6/12 | 15/28 |
| Predictive greedy v1.0.1 | 18/28 | 7/12 | 20/28 |
| **Predictive planner v1.0.2** | **18/28** | **7/12** | **22/28** |

`*` 35-minute non-predictive counts are computed from `all_28_seeds.csv`. All methods receive an independent spacecraft simulation with matched seed, fault generator settings and original conditions; executed procedures can subsequently change system trajectories.

At 35 minutes v1.0.2 uses the explicitly documented legacy greedy fallback, yielding matching results rather than claiming improved lookahead. At 60 minutes the new planner detected the same number of faults as v1.0.1 but had a slower mean budget-censored detection time in this 12-seed pilot. At 90 minutes it detected two additional cases across the 28 seeds. The 90-minute gain is **not a statistically established advantage**; the paired seeds include both wins and losses.

**Wheel-fault counterexample:** Exploratory mixed seed 8; fixed-order 58 min, original v1.0.1 greedy 76 min, new planner 81 min. The new planner finds the fault, but neither adaptive method is faster than fixed order for this case.

## Stronger faults and healthy controls

High-impact mixed-fault challenges, eight paired seeds: at 35 minutes, fixed detects 5/8 and both predictive variants 6/8. At 90 minutes, fixed detects 8/8, v1.0.1 detects 7/8 and v1.0.2 detects 8/8. The planner's mean time-to-failure-or-budget at 90 minutes was 22.5 min versus 30.38 for v1.0.1 and 42.75 for fixed.

Healthy controls, six seeds: no verified requirement failures were observed for fixed, v1.0.1 or v1.0.2 at 35 or 90 minutes. Sample sizes are small, and absence of observed failures does not establish a low false-positive rate.

All tested campaign records passed the internal evidence consistency checks.

## Reproducibility

Data: `all_28_seeds.csv`, `paired_campaigns.csv`, `holdout/paired_campaigns.csv`, `short_final/paired_campaigns.csv`, `high_impact/`, and `healthy_controls/`. Visualization: `detection_by_budget.png`.

```bash
python -m satvv.benchmark_v102 --seeds 5 6 7 8 9 10 11 12 --budgets 35 60 90
```

The synthetic plant, fault signatures and procedures are deliberately simplified. The result does not demonstrate superiority over real industrial systems or generalisation to independent spacecraft physics.
