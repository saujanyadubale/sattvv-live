# SAT-V&V v1.0.3 — Weak-fault sensitivity and reproducibility

## Main conclusion

The new low-impact observer **improves the reporting of sustained sub-threshold deviations** in the coupled synthetic simulator, notably heater faults. **It did not increase formal verified-failure detections in the paired 28-seed test**. An advisory warning must never be described as a verified requirement failure or confirmed root cause.

### Reproduced difficult case: exploratory mixed seed 7 (90 minutes)

- Injected fault: thermal sensor drift, onset **4580 s (76 min 20 s)**, termination **4930 s (82 min 10 s)**.
- New weak-signal event: **4610 s (76 min 50 s)**, only 30 seconds after onset; metric: persistent signed sensor-pair bias.
- The planner receives a non-oracle THERMAL relevance cue and selects **T11 at 4620 s** and **T16 at 4800 s**.
- Neither executed test verifies a failure because its project-defined requirements are not breached. **This is not a software failure or evidence of a healthy spacecraft.**

### Controlled low-severity telemetry experiment

- Synthetic severity **0.50**, fault start **420 s**, duration **2400 s**, 10-second sampling, seeds **500–519** held out from the detector settings, three operating modes.
- For each applicable mode, the new observer warns in **20/20** cases for sensor drift, battery resistance increase and heater fault; radio bursts warn in **20/20** cases in DOWNLINK only. Other modes generate no packet-loss evidence and correctly return no radio warning.
- The previous simple heuristic warned for heater faults in **0/20** per mode, compared with **20/20** for the new heat-balance innovation monitor. Battery warnings in NOMINAL mode increase from **14/20 to 20/20**. Sensor drift was already detectable by the previous monitor in these controlled simulations.
- Across **120 synthetic healthy and normal-load control runs** (20 seeds × 3 modes × 2 controls), the new observer reported **zero warnings**. This is not a field false-alarm-rate guarantee; all runs share project-defined physics and noise assumptions.
- The new detector contains fixed, heuristic thresholds. It is **not a newly trained supervised ML model** and has not been calibrated against real spacecraft telemetry.

### Paired scheduler evaluation

- **28 exploratory mixed-fault seeds (5–32), 90-minute budget**, same initial generated conditions per pair. Same v1.0.2 risk-aware planner; only the contribution of weak-signal subsystem priority differs.
- Formal verified detections: **22/28 without monitor-priority feedback vs 22/28 with feedback**.
- Warning during an injected fault window with new monitor: **13/28**. The remainder includes fault mechanisms not observable through the four monitoring signals, such as an unexcited reaction-wheel actuator.
- The internal evidence auditor passed for all runs. No new formal detection gain was observed in this sample.

### What we have *not* solved

- Predictive verification is not guaranteed to outperform fixed-order testing at every seed or time budget.
- A weak fault that does not cross a requirement limit **cannot honestly produce a formal FAIL** merely because an anomaly monitor is sensitive.
- Actuator faults can be unidentifiable without an active maneuver; communication faults require an observable downlink. Different fault types can produce similar residuals and signatures are **not calibrated causal diagnoses**.
- Shared generator/monitor assumptions create optimistic sensitivity compared with transfer to independent spacecraft models, sensors or real missions. Additional controlled false-alarm and independent domain-shift studies are required.

The machine-readable full study is in `benchmark.json` and is regenerated with `python -m satvv.benchmark_v103 --seeds 28`.
