# SAT-V&V v1.0.3 — Weak-fault monitoring (research update)

## Scientific boundary

**An injected fault, a warning, and a verified requirement violation are different events.** A weak drift may remain within acceptable tolerances, so forcing T11 to FAIL would be an invalid way to improve fault-detection statistics.

The new **causal weak-signal observer** (`satvv/weak_monitor_v103.py`) uses 60–100 second rolling histories and three-sample persistence. It evaluates four *observable-only* quantities:

| Indicator | Computation | Synthetic advisory threshold |
|---|---|---|
| Thermal sensor drift | Absolute rolling mean of *signed* temperature sensor difference | > 0.43°C |
| Battery degradation | Rolling predicted-minus-measured voltage, conditioned on load and state of charge | > 0.050 V |
| Thermal innovation | Difference between observed common-mode temperature and nominal integrated heat-balance model | > 0.62°C |
| Communication bursts | Mean downlink loss minus nominal 0.012 baseline | > 0.045 |

These numbers are fixed **prototype heuristic settings**, neither statistically calibrated on flight data nor mission limits. The monitor does not accept injected fault labels. It works causally on telemetry as samples are produced, retaining event timestamps. Reported weak-signal warnings *never* change formal PASS/FAIL.

Long-budget predictive scheduling can use a *soft*, decaying subsystem-priority cue from the warnings. Existing safety exclusions and affordable-test constraints remain enforced. The scheduler is not guaranteed to detect every fault or perform better on average; its proof of effectiveness would require external or independently generated validation.

The dashboard now distinguishes a **verified requirement failure**, an **early warning without a failed requirement**, and **no observed evidence**. The methods comparison separately reports warning times and formal detection times. The static portfolio showcase includes an archived v1.0.3 weak thermal-drift run.

## Reproducing

```bash
python -m unittest discover -s tests -v
python -m satvv serve
python -m satvv.benchmark_v103 --seeds 28 --budget 90
```

See `results/v1.0.3/RESULTS.md` for the outcome and limitations. The local server is development-only; GitHub Pages runs archived interactive replays, not a live Python simulation.
