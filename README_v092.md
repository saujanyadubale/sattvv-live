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
