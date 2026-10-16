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

---

# SAT-V&V v0.9.2 — Clearer experiment interface

This release redesigns the browser into **Experiment · Compare methods · Research & evidence** while keeping the full original research dashboard at `/legacy`. It does not change the physics or test-selection algorithms from v0.9.1.

## What changed
- Plain-English fault and policy names; fault onset in **minutes**, not seconds.
- Standard settings for scenario, policy, time budget, onset and seed; advanced settings for severity, initial SOC, eclipse, forecast horizon and detector selection. The latter two become active in the combined pipeline in v0.9.3. Environment/severity controls are disabled for randomized stress presets rather than silently ignored.
- Visible verification outcome, estimated cause (not ground truth), evidence trace, telemetry and probability trends.
- Side-by-side controlled policy comparison runs with matched configuration.
- `/legacy` retains the five older dashboards and previous APIs.

## Run
`conda activate satvv` followed by `python -m satvv serve`, then open `http://127.0.0.1:8765`.

## Regression
139 automated tests passed. Earlier UI assertions now check `/legacy`, and new tests check the redesigned homepage, 20-test catalog and assets.

## Scope
Synthetic simulation only; test scheduling, fault recognition, diagnostic probabilities and verification evidence are different outputs and must not be conflated. No flight validation.

---

# SAT-V&V v0.9.1 — Research Lab dashboard fix

This patch release corrects the **Unknown stress case** error in v0.9: the
v0.9 HTML dropdown offered only earlier scenario values, but `/api/research`
expected `STRESS_CASES`. The experiment switch now populates valid fault
scenarios and valid policies. The stress-case API now respects the requested
`onset_s`, and changing experiments clears stale displayed results.

Run `python -m unittest discover -s tests -v` and `python -m satvv serve`, then
reload `http://127.0.0.1:8765` after stopping any previously running server.

---

# SAT-V&V v0.9 — Coupled Verification, Learning and Robustness Lab

**Executable, all-software research prototype. No flight validation, hardware EGSE, or ECSS certification.**

## Evolution
- **v0.7:** Bayesian fault-hypothesis updates and information-gain test selection on 16 verification procedures.
- **v0.8:** Coupled 1D ADCS/EPS/thermal plant, with 4 new ADCS procedures T17–T20, for **20 executable procedures** in one campaign.
- **v0.9:** Offline-trained Random Forest test-risk ranker and held-out **compound-fault stress benchmark**, including healthy eclipse/load changes and new mixtures absent from model fitting.
- Previous v0.1–v0.6 simulation, forecast, ML monitoring, and dashboards remain available.

## Run on macOS
Open Terminal in the *extracted* `SAT-VV-v0.9` directory; you do not need to `cd` into it again.

```bash
conda activate satvv
conda install -c conda-forge numpy matplotlib scikit-learn -y
python -m unittest discover -s tests -v
python -m satvv serve
```

Visit `http://127.0.0.1:8765`; choose the **Research lab v0.9** tab for v0.7/v0.8/v0.9 experiments. Use `Ctrl+C` to shut down. If port 8765 is busy, use `python -m satvv serve --port 8766`.

## Command-line research

```bash
python -m satvv active-v07 --scenario resistance_ramp --budget 35
python -m satvv integrated-v08 --scenario adcs_gyro_bias --budget 45
python -m satvv adcs-suite --scenario adcs_star_dropout --onset 0
python -m satvv stress-v09 --case dual_resistance_sensor --policy learned_risk --budget 25
python -m satvv bench-stress --seeds 4 --out results/v0.9
```

Main result files: `results/v0.9/RESULTS.md`, `stress_runs.csv`, `stress_summary.csv`, `benchmark.json`, and `ood_detection_by_budget.png`.

## Scientific interpretation
- Policies share the same 20-procedure catalog and simulation model; test ordering changes the system's trajectory and outcome.
- The learned ranker was fitted on separate synthetic seeds **171–173**; Bayesian diagnostic tables were fitted on seeds **301–303 and 451–453**; the OOD benchmark evaluates unseen combinations on **801–804**.
- No hidden injected fault name is used as a model input. **Warnings and probability scores are not formal PASS/FAIL verification evidence.**
- Fault-detection rates are percentages of synthetic campaigns with a failed executed check; they are not root-cause accuracy.
- 132 tests (release regression run) exercise software invariants. Statistical advantage and generalization to actual spacecraft remain unproven.
- The learned test-failure probabilities are not calibrated; intervals in the stress report are exploratory scenario-cluster bootstraps.

See `docs/v0.9_protocol.md` for scope, validity threats, and planned next steps.
