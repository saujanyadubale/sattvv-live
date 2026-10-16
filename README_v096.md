# SAT-V&V v0.9.6 — Robust Diagnosis and Random Challenge Lab

**Release status:** functional software prototype, synthetic simulator. This is not spacecraft qualification or independently validated diagnosis.

This version builds on v0.9.5. It adds requirement-level Bayesian updates, in-procedure communications monitoring, seeded single/multi-fault generation, a replay interface, and a reproducible exploratory benchmark. It preserves the earlier experiment, comparison, guide, industry landscape, technical reference and legacy pages.

## Quick start

```bash
conda create -n satvv -c conda-forge python=3.11 numpy matplotlib scikit-learn -y
conda activate satvv
python -m unittest discover -s tests -v
python -m satvv serve
```

Open **http://127.0.0.1:8765/challenge**. Other pages are reachable from the navigation. If upgrading from an existing `satvv` environment, activate it instead of creating a new one.

For a paired challenge benchmark:

```bash
python -m satvv bench-challenge --seeds 8 --budget 30
```

Outputs: `results/v0.9.6/challenge_benchmark.json` and `results/v0.9.6/summary.csv`.

## New features

- **Requirement-level diagnosis:** Failed communication packet loss (REQ-COM-L) now updates the radio-fault hypothesis rather than using only the T05 overall PASS/FAIL result. All diagnostic weights remain explicitly *uncalibrated*. Naïve independence and a single dominant-cause hypothesis set can be wrong for compound faults.
- **In-test communications monitoring:** T05/T08 record packet-loss peak and onset timestamps from actual sampled downlink telemetry, including faults that begin during the procedure. The audit checks interval consistency and match to the monitor flag. The anomaly alert does not constitute a verification FAIL.
- **Random Challenge mode:** Deterministic `seed` + difficulty (`control`, `single`, `mixed`, `stress`) generates physical fault episodes, severity, ramp, recurrence, initial charge and eclipse settings. For paired comparisons each policy receives an independently initialized copy of precisely the same challenge. Oracle labels are not given to the policy and are revealed only in post-run evaluation.
- **Animated post-run replay:** Timed progression through recorded tests, scenario timeline, subsystem cards, requirement map, measured voltage and temperature, fault hypothesis weights, decision provenance and seeded challenge results. Playback is based on completed server-side results, not streaming live spacecraft telemetry. Includes reduced-motion support.
- **Five-policy visual comparison:** Detection times plotted alongside results. Healthy controls and missed faults remain visible. At present, the posterior is a categorical best-cause ranking, not reliable multi-fault identification.

## Scientific boundaries

1. The training and random-challenge environments share simplified spacecraft physics. Randomizing faults does **not** establish out-of-distribution generalization to real flight hardware.
2. The scenario generator chooses scripted fault distributions; these are not real-world failure priors.
3. Faults that are too weak, too late, or invisible in selected modes can be missed. That is a valid outcome rather than a software error.
4. A specific requirement failure is not synonymous with proving the physical root cause.
5. Strongly correlated verification outcomes violate the naïve independence assumption in posterior updates. Probabilities must not be interpreted as calibrated risk estimates.
6. This release has not been independently verified on actual spacecraft telemetry or a hardware testbed.
7. A visual replay is explicitly labeled as **recorded evidence**, not simulated real-time computation. It never invents new telemetry samples.

## Documentation

- `docs/v0.9.6_protocol.md` — experimental design and test plan.
- `results/v0.9.6/RESULTS.md` — observed pilot and limitations.
- `results/v0.9.6/random_challenge_heatmap.png` — paired pilot visualization.
