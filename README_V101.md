# SAT-V&V v1.0.1 — Scientific reliability patch

## Why this update exists

In a seeded mixed fault case (`mixed`, `exploratory`, seed `8`, verification budget `90 min`), the original **predictive-active** scheduling policy ran 32 procedures but never chose the ADCS actuator tests T17, T18 or T20. Fixed-order testing exposed the reaction-wheel weakness on T17 at minute 58. This is a test-selection starvation problem.

## Changes

- **Coverage-aware predictive-active selection:** maintains the original information-gain, forecast, criticality, warnings and cost score, but may override it to prioritize a safe, affordable, never-executed procedure after repeated checks or when test coverage would otherwise exhaust the budget.
- **No safety bypass:** electrical and thermal safety exclusions remain authoritative.
- **ADCS-specific observable risk:** tracking error, angular rate, wheel momentum and sensor consistency are used when available; absence of an actuator-exciting test limits passive detection.
- **Audit transparency:** executed records contain `coverage_guard` and `adcs_observable_risk` fields, with UI explanations when guards are activated.
- **Website case study:** adds a third, static archived replay for the corrected seed-8 case. The GitHub Pages website does **not** execute new Python simulations.

## Reproduced result

| Policy | Result | Verified at | Number of tests |
| --- | --- | --- | --- |
| Original v1.0 fixed | T17 FAIL | 58 min | 17 |
| Original v1.0 predictive-active | No verified failure | — | 32 |
| v1.0.1 predictive-active | T17 FAIL | 76 min | 24 |

This **recovers detection**, but is not faster than fixed testing in this case. The new policy is a different speed-versus-coverage trade-off, not a demonstrated universal improvement.

## Pilot research evidence

Read [`results/v1.0.1/RESULTS.md`](results/v1.0.1/RESULTS.md), the before/after CSV and the two JSON files. Across eight exploratory mixed-fault seeds at 90 minutes, predictive-active detection improved from 3/8 to 6/8. At a 35-minute budget the improvement was absent (1/6 in both versions). The pilot is small and uses shared synthetic physics.

## Run locally

```bash
conda activate satvv
python -m unittest discover -s tests -v
python -m satvv serve
```

The user interface is available at `http://127.0.0.1:8765` on the same computer. The built-in local preview server is not hardened for public access.

To reproduce the updated predictive-active and fixed-order results:

```bash
python -m satvv.benchmark_v101 --seeds 5 6 7 8 9 10 11 12 --budget 90
```

To reproduce the older v1.0 predictive-active scores, run those exact seed settings in the separately archived original v1.0 project; otherwise a patched algorithm would be incorrectly reported as the original baseline.

## GitHub Pages handoff

A static interactive showcase is in `github-pages/satvv/`. Publish the **`satvv/` directory** under the existing portfolio repository, or download the separate `SATVV_V101_GITHUB_PAGES_DROPIN.zip`. The archive now includes the corrected seed-8 demonstration. Production public simulation requires a separately deployed, secured backend.
