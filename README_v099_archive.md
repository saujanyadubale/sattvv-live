# SAT-V&V v0.9.9 — 3D Mission Replay & Model Documentation

**This is a software-only research prototype, not flight-qualified engineering equipment.**

The simulator and test-selection algorithms remain those of v0.9.8. This release adds a conceptual, interactive perspective-3D spacecraft and ground-system visualizer synchronized with completed verification evidence, plus substantially expanded How It Works explanations for every actual ML/statistical/probabilistic/heuristic method.

## Install and run

```bash
conda activate satvv
conda install -c conda-forge numpy matplotlib scikit-learn -y
python -m unittest discover -s tests -v
python -m satvv serve
```

Visit **http://127.0.0.1:8765/challenge** for 3D Mission Replay and **http://127.0.0.1:8765/how-it-works** for detailed model explanations. The entire site is locally served by Python; no CDN, graphics package or Internet access is required.

## New visualization features

- Rotatable, zoomable spacecraft with labeled EPS, thermal, onboard computer, communications, payload, and single-axis ADCS zones.
- Ground station and animated conceptual data link during communications procedures.
- Synchronized highlights with the actual replayed procedure; failed checks highlight and magnify the tested subsystem region.
- An amber dashed marker distinguishes a *suspected* area derived from uncalibrated fault-hypothesis weights. Only after clicking **Reveal injected fault record** may the post-run ground-truth zone appear in magenta.
- Choose split view (3D + telemetry), 3D focus, or telemetry only. Camera reset and follow-active-test controls. Honors reduced-motion preferences.
- The representation is conceptual—not a CAD reconstruction, orbital simulation, exact instrument location, causal diagnosis or live ground RF stream.

## Model transparency

The How It Works guide now describes Isolation Forest, gradient-boosted fault classifier, gradient-boosted voltage/temperature regressor, Random Forest test ranker, Bayesian fault-hypothesis updater, physics/OLS/CUSUM baselines, all five verification schedules, and the evidence audit. Source references and exact hyperparameters are in `docs/v0.9.9_models_and_algorithms.md`.

## Limitations and scientific claims

- Model-specific hypotheses and decision scores are *not calibrated flight probabilities*; do not interpret the colored areas as verified component failure location.
- Actual failure is established only by an executed test violating a project-defined requirement.
- The randomized testbed is a synthetic model; independent testbeds and real spacecraft telemetry remain future validation work.
- All previous v0.9.8 scenario-generation behaviors and benchmark methods are retained.

## Code layout

- `web/mission3d.js`: 3D geometry and procedural visualization, no third-party JS.
- `web/challenge.js`: recorded-replay synchronization.
- `web/how-it-works.html`: research explanations and algorithm comparator.
- `satvv/web_server.py`: local route for the model script, existing model-backed APIs.
- `tests/test_v099_mission.py`: new integration/HTML/model-explanation contracts.
- `docs/v0.9.9_models_and_algorithms.md`: detailed engineering reference.

# SAT-V&V v0.9.8 — Verification Challenge UX

Latest features: visible calculation indicator, high-impact vs exploratory seeded fault profiles, and replay measurement readouts. See `README_v098.md`. All earlier simulation and educational functionality is preserved.

## Run

```bash
conda activate satvv
python -m unittest discover -s tests -v
python -m satvv serve
```

Open `http://127.0.0.1:8765/challenge`.

**Research limitation:** synthetic models; no hardware or flight validation. No random fault is guaranteed to cross a requirement.
