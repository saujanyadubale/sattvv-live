# SAT-V&V v0.9.4 — Pilot results

Synthetic paired benchmark: 8 scenario families × 3 seeds × 2 budgets × 5 policies = 240 campaigns.
Six fault families and two healthy controls. Fault onset minute 5.

## Detection within budget

| Strategy | 20 min (of 18 faults) | 26 min (of 18 faults) | Healthy failures (of 12 across both budgets) |
|---|---:|---:|---:|
| fixed | 4/18 (22.2%) | 4/18 (22.2%) | 0/12 |
| temporal_adaptive | 11/18 (61.1%) | 13/18 (72.2%) | 0/12 |
| information_gain | 14/18 (77.8%) | 14/18 (77.8%) | 0/12 |
| learned_risk | 9/18 (50.0%) | 15/18 (83.3%) | 0/12 |
| predictive_active | 13/18 (72.2%) | 14/18 (77.8%) | 0/12 |

## Reproduced battery load-step failure (single example)

Parameters: `resistance_ramp`, seed 7, onset 5 min, severity 2.0, initial SOC 100%, budget 26 min, ML-ranked policy.
T01, T05 and T04 pass; T14 completes at 11 min with two failed requirements:
- `REQ-EPS-R`: max absolute voltage deviation **0.5652 V**, allowed **≤0.2600 V**, fails by **0.3052 V**.
- `REQ-EPS-REC`: absolute voltage recovery error **0.2844 V**, allowed **≤0.1800 V**, fails by **0.1044 V**.
Neither failure independently proves the physical root cause; both establish failures of the current synthetic requirements under this test.

## Interpretation

At 20 minutes, Bayesian information gain and predictive active perform better than ML-ranked in this specific benchmark. At 26 minutes, ML-ranked slightly leads. The policy that wins changes with time budget and fault composition. All policies miss the three heater faults within both budgets. Zero observed false verification failures across a total of 12 healthy campaigns per policy (six per budget) does not establish a near-zero false-failure rate.

The ML model was trained on the same synthetic plant and related fault patterns. It includes test IDs as inputs, so test-order advantages may reflect repeated patterns in the synthetic catalog, not learned causal understanding. The top-hypothesis probabilities are explicitly uncalibrated. A genuine independent physical testbed and more seeds/families are required before making generalization claims.

## Research limitations

Numerical audit independently recomputes threshold comparisons from the stored measured values, but the stored values and original PASS/FAIL decisions still come from the same simulator. This is internal consistency, not independent physical evidence.

Results stored in `benchmark.json`, `campaigns.csv`, `summary.csv`; plot `pilot_comparison.png`.
