# SAT-V&V v0.9 — Independent-combination pilot

Results use handcrafted **synthetic** fault families held out from the model calibration, not flight data.
The intervals are **exploratory family-cluster bootstraps** and can be unstable with five faulty families.

| Budget | Fixed | Temporal | Information gain | Learned risk |
|---:|---:|---:|---:|---:|
| 20 | 20% [0%, 60%] | 50% [10%, 90%] | 50% [10%, 90%] | 40% [0%, 80%] |
| 25 | 40% [0%, 80%] | 55% [15%, 95%] | 60% [20%, 100%] | 90% [70%, 100%] |
| 30 | 40% [0%, 80%] | 60% [20%, 100%] | 60% [20%, 100%] | 90% [70%, 100%] |
| 45 | 100% [100%, 100%] | 100% [100%, 100%] | 100% [100%, 100%] | 100% [100%, 100%] |

## Healthy controls
Two healthy families (one including eclipse/load changes) test the false-failure behavior of the procedures.
None of the tested healthy campaigns produced a failed requirement in this pilot; this is not a zero-error guarantee.

## Main limitations

- Compound faults are novel mixtures but still use the same underlying toy physics, so generalization is limited.
- Calibrated response likelihoods do not explicitly depend on failure onset, current mode or test history.
- Some procedures reset ADCS conditions deliberately; this is a controlled test, not a fully passive flight simulation.
- Early stop on first failed requirement prevents complete root-cause discrimination.
- Learned ranking scores are **uncalibrated** and are not safety-qualified.
- Comparisons use small synthetic families. More independent physics and external data are required.
