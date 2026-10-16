# SAT-V&V v0.9.6 — Paired random-challenge pilot

Eight deterministic seeds per challenge class and verification policy; 30 simulated minutes per campaign. **Synthetic simulator, small exploratory sample.**

| Challenge type | Fixed | Temporal | Info gain | ML-ranked | Predictive active |
|---|---:|---:|---:|---:|---:|
| Healthy control (false failures) | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| Single fault detection | 12.5% | 75.0% | 75.0% | 87.5% | 75.0% |
| Mixed fault detection | 0.0% | 50.0% | 50.0% | 50.0% | 50.0% |
| Stress / recurrence detection | 25.0% | 87.5% | 87.5% | 87.5% | 87.5% |

Each cell represents **8 campaigns**, not a large-sample estimate. All policies receive the same generated scenario for each (difficulty, seed) pair, but their executed tests can change later spacecraft trajectories.

## Observations

- No healthy-control campaigns produced a failed verification check in this small run. This **does not** establish zero false-alarm probability.
- ML-ranked test ordering is relatively effective on the tested single-fault seeds; the strength may reflect synthetic training and scheduling priors.
- Some mixed faults remain undetected within 30 minutes for every algorithm. Combined-fault diagnosis is presently incomplete and categorical.
- The radio-burst scenario can now generate a monitoring alert from downlink telemetry **during** the test, even where pre-decision snapshots were quiet.
- Posterior fault weights use handcrafted requirement signatures; they are not calibrated probabilities of ground truth.

## Scientific caveats

The random generator randomizes scenarios **within the same simulator family**. It does not create truly independent physics or flight telemetry. The stress class can contain recurring episodes of one mechanism, so the number of episodes can exceed the number of distinct fault types.
A correct highest-weight hypothesis on a compound-fault case is counted as a **partial match** if it matches *any* injected mechanism. It does not mean the model has identified every active cause.
Warnings, forecasts, and verification FAIL are recorded separately. Audits check reproducibility and data consistency, not external physical validity.

## Reproduce

```bash
python -m satvv bench-challenge --seeds 8 --budget 30
```

Full per-campaign results: `challenge_benchmark.json`; summary table: `summary.csv`; figure: `random_challenge_heatmap.png`.
