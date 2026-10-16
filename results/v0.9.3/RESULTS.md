# SAT-V&V v0.9.3: pre-v1.0 pilot results

## Release gate
154 software regression tests passed. Browser layout rendered with a representative backend response; the HTTP API was separately exercised. This is a review build, not flight certification.

## Five-stage integration
Observations produced during executed tests feed causal health monitoring and voltage/temperature forecasts; test PASS/FAIL evidence updates a Bayesian fault hypothesis; the next verification procedure is selected subject to an illustrative safety guard; a separate consistency auditor checks the resulting evidence. All five stages are exercised in the same campaign.

## Held-out compound-fault comparison
Two random seeds (801 and 802) for each of five faulty and two healthy scenario families, with budgets 20, 25 and 35 simulated minutes. That gives **10 faulty and 4 healthy** campaigns per policy per budget. The policies do not share identical post-command trajectories.

| Policy | Faults detected, 20 min | Faults detected, 25 min | Faults detected, 35 min | Healthy false failures, 25 min |
|---|---:|---:|---:|---:|
| Fixed | 2/10 | 4/10 | 6/10 | 0/4 |
| Temporal Adaptive | 5/10 | 5/10 | 10/10 | 0/4 |
| Information Gain | 5/10 | 5/10 | 10/10 | 0/4 |
| Learned Risk | 4/10 | 9/10 | 10/10 | 0/4 |
| Predictive Active | 4/10 | 5/10 | 10/10 | 0/4 |

## Interpretation
At 25 minutes, predictive-active detects 5/10 faulty simulations; the offline learned-risk baseline detects 9/10. At 35 minutes, all four non-fixed strategies detect 10/10 in this small set. The new closed loop **works technically** but has **not demonstrated an improvement** in fault-detection efficiency. A larger, independent evaluation is needed before comparing scientific performance.

Healthy control campaigns had no failed executed requirements in this limited pilot. That does **not** establish zero false-failure probability.

## Caveats
- Fault labels are hidden from policies, but physical simulator and test library remain synthetic and mutually designed.
- Training, calibration and test seeds differ; held-out compounds still use the same base models.
- Posterior hypothesis weights are uncalibrated, especially inappropriate for unseen combinations not represented as hypotheses.
- Forecast intervals may not achieve nominal coverage on shifted scenarios; predicted crossing and verified failure are different.
- The evidence audit verifies internal reporting consistency and elapsed budget, not physical accuracy or compliance.
- With only two seeds per fault family, results have substantial uncertainty. These are raw counts, not inferential superiority claims.

## Reproduce
`python -m satvv bench-pipeline --seeds 2 --out results/v0.9.3`

Raw files: `benchmark.json`, `campaigns.csv`, `summary.csv`.
