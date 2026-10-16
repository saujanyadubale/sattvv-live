# v0.9.7 — Reproducible interpretation case

This release does not change the spacecraft plant, fault-selection policies, or historical benchmark results.

- Reproduction: `run_challenge('mixed', 7, 90, 'predictive_active')`.
- One generated fault, **sensor drift**, from **4580 s (76 min 20 s)** to **4930 s (82 min 10 s)**, severity **0.482** synthetic units.
- Relevant T11 ran **4860–5040 s** and overlapped the last 70 seconds of the injected episode.
- Its maximum recorded sensor disagreement was approximately **2.7 °C** against the project-defined failure limit **3.0 °C**. The check passed, consistently with the requirement. No strategy reported a failed requirement within this challenge's budget.
- This case does **not** indicate an implementation failure. A randomly generated episode need not breach a requirement, and no-detection isn't equivalent to a healthy spacecraft. The challenge generator is not independently physics-validated and does not guarantee fault observability.

## Changes

1. The industry graphic no longer encodes unsupported quantitative values with equal bars. Its role map is categorical, linked to a cited capability matrix.
2. Six navigation items consistently appear on all research pages.
3. A loading spinner is displayed while computing, explicitly *not* as a backend progress measurement.
4. Challenge replay offers selectable bus voltage, current, battery charge, load, solar power, primary/redundant temperature, temperature sensor disagreement, packet loss, and latency from actual recorded samples.
5. After revealing fault truth, the result displays onset, duration, relevant tests, overlap, and their numerical evidence where recorded.

## Validation

- 191 automated Python tests pass.
- Browser rendered the updated industry graphic and a seeded challenge using recorded backend responses; no JavaScript errors in those checks. The sandbox browser cannot directly navigate to localhost here.
- The previously reported 0.9.6 detection benchmark remains historical, not recomputed or improved by this UX release.
