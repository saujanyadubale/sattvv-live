# SAT-V&V v0.9.3 — Integrated predictive verification (research preview)

**This is the pre-v1.0 review release.** v0.9.2 established the simplified three-workspace interface; v0.9.3 connects detection, forecasting, Bayesian fault hypothesis updates, active verification and independent evidence consistency checks in one persistent spacecraft campaign.

## Run locally
Open the extracted `SAT-VV-v0.9.3` folder in Terminal:

```bash
conda activate satvv
conda install -c conda-forge numpy matplotlib scikit-learn -y
python -m unittest discover -s tests -v
python -m satvv serve
```

Open `http://127.0.0.1:8765`. Stop a previous local SAT-V&V server first (`Ctrl+C`), and hard-refresh to load the new version. The old experiment dashboard remains at `http://127.0.0.1:8765/legacy`.

## Controls and terms
- **Experiment:** choose a friendly spacecraft condition, five scheduling policies, budget, onset, seed; expand Advanced for severity, battery SOC, eclipse, horizon and anomaly detector.
- **Compare methods:** runs each selected policy separately under the same requested starting conditions.
- **Research & evidence:** catalog of 20 procedures, algorithms, research limitations and old UI link.
- **Warning or forecast risk ≠ FAIL**; only an executed requirement check can produce FAIL.
- **Best-matching hypothesis ≠ confirmed physical root cause.** An audit pass means the log is internally consistent, not that a spacecraft is flight-safe.

## CLI
```bash
python -m satvv pipeline-v093 --scenario resistance_ramp --policy predictive_active --budget 30 --onset 600
python -m satvv bench-pipeline --seeds 2 --out results/v0.9.3
```

Read `docs/v0.9.3_protocol.md` for model assumptions, limitations, and the pilot benchmark. The older v0.1–v0.9.1 commands, APIs and dashboard remain supported.
