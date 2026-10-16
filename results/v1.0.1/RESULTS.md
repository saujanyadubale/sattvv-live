# SAT-V&V v1.0.1 — Anti-starvation verification pilot

This is a controlled *synthetic* before/after comparison using the original v1.0 Portfolio Edition and the corrected v1.0.1 source, both running the same seeded scenarios and identical 20-test catalog. We compare identical named policies, and do **not** interpret this as validation on flight data.

## Reproduced counterexample

- Mixed exploratory, seed 8, budget 90 min; injected reaction-wheel weakness starts at about 44.5 min.
- v1.0 fixed-order: T17 attitude hold FAIL at minute **58**.
- v1.0 predictive-active: no failure; T17, T18 and T20 were never executed.
- v1.0.1 predictive-active: T17 FAIL at minute **76**; 24 tests executed; audit passes.
- The scheduling guard was invoked and recorded as `coverage_budget_reserve` / `repeat_streak_limit`. No hidden fault labels were used for selection.

## Paired pilot, exploratory mixed faults (90-minute budget)

| Controller | Version | Verified failures | Average distinct procedures per campaign |
|---|---|---:|---:|
| Predictive-active | Original v1.0 | 3 / 8 | 9.4 |
| Predictive-active | v1.0.1 | 6 / 8 | 15.1 |

The additional detections occur in seeds **8, 9 and 10**. For existing detections, some verification times become longer (seed 5: 61→81 minutes; seed 6: 36→37 minutes). At the 35-minute exploratory budget both versions detected 1 of 6 cases. Four high-impact mixed scenarios at 90 min remained 4/4 detected. Four exploratory stress scenarios at 60 min remained 4/4 detected, with some detection delays increasing by 1–3 minutes.

**Limitations:** This is a small hand-inspected pilot containing the seed-8 counterexample, not a blind held-out estimate. All cases share the same simplified simulator, randomized fault mechanisms, and policies calibrated on synthetic data. Coverage guards may delay detection of acute/recurring faults; this does not establish overall algorithm superiority.

## Changes implemented

1. **Repeat-streak safeguard:** after two consecutive repeated procedures, choose a safe, affordable, previously unexecuted procedure where one exists.
2. **Coverage-budget reserve:** when a remaining-time window permits all still-untested safe checks, avoid spending that last opportunity repeating earlier checks.
3. **ADCS observable risk:** attitude tracking error, high wheel momentum, gyro/star discrepancy or star availability can raise ADCS priority, but only on measured values. Passive telemetry cannot reliably prove wheel weakness without an actuator-exciting procedure.
4. **Auditability:** the evidence trace records which coverage safeguard caused an override and the observed ADCS risk score. Existing physical safety exclusions remain authoritative.

## Reproduce

Run:

```bash
python -m unittest discover -s tests -v
python -m satvv.benchmark_v101 --seeds 5 6 7 8 9 10 11 12 --budget 90
```

For the **original v1.0** baseline, separately run the same seeds using the archived source from `SATVV_v1.0_PORTFOLIO_COMPLETE.zip`. The archived result data are supplied as `original_v1.0_records.json` and the v1.0.1 results as `v101_records.json`. The pairing CSV contains both. Do not regenerate the older scores with the patched policy and call them baseline scores.
