# SAT-V&V v1.0 Beta.2 — Unified Experiment & Explainable Telemetry

**Status: synthetic research demonstration, not a spacecraft operations tool.**

## Run

In the extracted folder:

```bash
conda activate satvv
python -m unittest discover -s tests -v
python -m satvv serve
```

Open <http://127.0.0.1:8765/>. The original standalone experiment dashboard is preserved under `/classic`; both random and manually selected scenarios now share the **homepage**, 3D visualization, replay, telemetry and compare panel. `/challenge` is an alias of this same page.

## New unified modes

- **Random challenges:** choose control, single, mixed or stress, an intensity profile, seed and time budget. Only post-run evaluation can reveal the generator's hidden injected fault record.
- **Configured scenario:** select a known spacecraft condition, onset, severity, starting battery charge, eclipse condition, prediction horizon, monitoring method, verification strategy, seed and budget. This mode is not a blind hidden-fault challenge: you deliberately chose the scenario.
- **Compare:** all five policies operate on independent copies of the same configured or seeded environment. The policies can change their respective simulated trajectories.

All previous research endpoints are retained. The new unified API endpoint is `POST /api/unified` with `mode` set to `random` or `manual`.

## Telemetry interpretation

The telemetry graphs now support:

- Raw measured values and selected project-defined reference/requirement lines.
- Expected/reference compared with measured signals **only where a defensible reference is modeled** (battery load- and charge-conditioned voltage; redundant thermal sensor as a cross-check). These references are *not* calibrated flight-normal envelopes.
- Residual/deviation or point-to-point changes, including a fallback point-to-point difference when there is no expectation model.
- Debounced early-warning event markers and a synchronized cursor for paired charts.
- A plain-language explanation of the selected signals, their units and their limits.

**Warning model:** `satvv/insights_v11.py` analyses observable telemetry without reading injected fault labels. It tests persistent sensor disagreement >=1.20 °C across three consecutive recorded samples, voltage residual >0.16 V across three samples, and packet loss >0.08 during downlink across three samples. It also surfaces already-recorded procedure-window communications warnings. These thresholds are **illustrative**, not calibrated or validated anomaly false-alarm rates. Sampling cadence affects the meaning of "three consecutive observations." The existing classical/learned monitors remain as before.

Formal verification PASS/FAIL is still assigned **only by executed project-defined requirements**. Early warnings are independent review indicators; the beta.2 added warnings do **not** influence the existing test-selection algorithm. The policy scheduler remains unchanged.

## Review-only engineering recommendations

The advisory panel uses the current replay's observable warning events and requirement failures to suggest next diagnostic tests and potential human-reviewed mitigations for EPS, THERMAL, COMMS, OBC, PAYLOAD and ADCS. It does **not** issue commands, automate repairs, infer physical root cause with certainty, or claim safety approval. A suspected subsystem is not a confirmed fault location.

## Reproducible examples

**Weak injected fault:** Random → Mixed → Exploratory → seed 7 → 90 min → Predictive active. The generator injects thermal sensor drift between ~76.3 and 82.2 min. The existing T11 verification records ~2.7 °C maximum disagreement, beneath its 3 °C requirement limit; no requirement fails. The beta.2 supplementary monitoring layer signals a persistent sensor discrepancy near 77 min. This is a targeted synthetic case study, not an independent generalization result.

**Healthy control:** Random → Healthy control → seed 7 → 35 min → Fixed. The monitored control case did not produce a spurious supplementary warning during the check performed for this release.

## What is unchanged

The same synthetic spacecraft dynamics, 20 procedures, five schedulers, 3D conceptual model, NASA optional online asset selection and offline fallback, research/industry pages and prior historical results are preserved. Neither a new ML model nor a statistically validated detector has been introduced in this release. Dedicated backend regression tests cover the warnings, avoidance of oracle leakage, API mode validation, and unchanged requirement status interpretation.

## Remaining limitations

- Mode-conditioned voltage expectation is a simplified physical model; temperature sensor comparison is **not** a forecast of true hardware temperature.
- Thresholds, persistence and suggested mitigations require independent evaluation, false-alarm calibration and operational approval before any real use.
- The learned ranker and diagnostic hypothesis weights are trained/defined using simplified synthetic fault families; diagnosis remains uncalibrated.
- 3D overlays are conceptual subsystem zones. WebGL and NASA optional asset load depend on external browser resources; an offline renderer remains available.
- Screenshot/browser checking used recorded simulation results because direct local browser navigation can be restricted in this environment. Python HTTP tests ran against the actual server.
