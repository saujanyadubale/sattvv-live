# SAT-V&V v1.0.2 — Risk-aware verification planning

**Scientific status:** simulation-only research prototype; not a flight-qualified verification system, not physically validated fault diagnosis, and not a universal improvement over fixed testing.

## What changed

- `satvv/planner_v102.py` introduces deterministic **bounded beam search over sequences of up to three distinct tests**, with a beam width of 12 candidates. This is **receding-horizon test-schedule planning**, not a forward simulation of spacecraft dynamics and not reinforcement learning.
- Each test's heuristic value combines expert-specified requirement-failure likelihood, Bayesian information gain, new requirement coverage, subsystem diversity, test duration, model/warning risk, and time since a previously passing check. Every decision is replanned **after real recorded evidence**.
- The existing `predictive_active` interface uses this planner when the **initial campaign budget exceeds 35 minutes**. At **35 minutes or below**, it uses the v1.0.1 greedy method as an explicit short-budget fallback, because the first lookahead implementation degraded short-window fault detection. The `decision.scheduler_mode` field tells you which branch was used.
- The previous scheduler is retained as the separate research baseline `predictive_greedy_v101` (not added as a sixth main dashboard button).
- Every planner decision exposes `planned_sequence`, `plan_objective`, `candidate_sequences_evaluated`, `scheduler_mode`, and `plan_assumptions` in its audit trace. The proposed plan is not executed blindly: only its first test runs, and the remaining sequence is replanned after observing its outcome.
- The simulator's safety exclusions, formal requirement PASS/FAIL logic and evidence audits remain unchanged.
- The GitHub Pages showcase adds an optional **archived** v1.0.2 replay. The live Python simulation engine still requires local execution or a separately hosted backend.

## Benchmark overview

See `results/v1.0.2/RESULTS.md`, `paired_campaigns.csv`, `holdout/`, `short_final/`, `high_impact/` and `healthy_controls/`.

A paired experiment evaluated 28 synthetic exploratory mixed-fault seeds at 35 and 90 minutes; 60-minute numbers are available for the first 12 seeds. At **90 minutes**, the updated policy detected 22/28 cases, the v1.0.1 greedy baseline 20/28, and fixed order 16/28. At **35 minutes**, the explicit fallback yields 18/28 for both newer and older predictive policies. These small, model-dependent observations do **not** establish generalization or statistically significant superiority.

The original seed-8 wheel weakness is found at minute **81** by the new planner versus **76** by v1.0.1 and **58** by fixed testing. This regression is not concealed. The objective is expected performance across uncertain faults, not universal speed for every test.

## Install and run

```bash
python -m unittest discover -s tests -v
python -m satvv serve
# in a separate terminal, to reproduce the comparison:
python -m satvv.benchmark_v102 --seeds 5 6 7 8 9 10 11 12 --budgets 35 60 90
```

Open `http://127.0.0.1:8765`. Select **Risk-aware predictive planner v1.0.2** and expand the decision replay to inspect sequences.

## Important limitations

1. Risk scores are **uncalibrated expert-signature heuristics**, not true failure probabilities.
2. The lookahead assumes a **frozen current observation/model** for candidate plans; it does not simulate unknown future trajectories. Actual physical safety is rechecked at every executed decision.
3. The fault generator, diagnostic signatures and verification model share a simplified synthetic environment. More independent simulators, real telemetry and uncertainty calibration are required before research-performance claims.
4. Safe broad coverage is a trade-off: it can delay detection of specific early faults.
5. Healthy-control runs showed no formal false fails in the small tested sample. That does not establish a low operational false-alarm probability.
