# SAT-V&V v0.1 — Experimental protocol (pilot)

## Population

10 named, singly injected synthetic faults: undervoltage, overcurrent, thermal runaway, stuck thermal sensor, payload startup failure, packet loss, delayed telemetry, failed watchdog, illegal transition, packet corruption. Control: no fault.

There are 12 test procedures covering five subsystem labels; 11 project-defined requirement IDs. All procedures use a simplified cold-start model and share the same assertion predicates and synthetic execution costs.

## Compared methods

1. **Fixed:** original catalog order. This is a simple benchmark *not* necessarily industrial expert practice.
2. **Random:** one random permutation of the test catalog per seed. This is not yet true property-based exploration.
3. **Model-fixed:** greedy preplanned sequence using the same requirements, transition novelty, risk and cost model as the adaptive strategy, **without telemetry feedback**. Essential for attributing gains to adaptation rather than better ordering.
4. **Adaptive:** recompute the greedy ranking after every test using requirements checked, transitions visited, cost, preassigned criticality and *observed* risk clues such as an abnormal but passing bus voltage. The strategy cannot read `Fault` or its hidden class label.

## Exact benchmark

- Budgets: 8, 12, 16, 20, 26, 33 **synthetic time units**.
- 30 seeds per fault/policy/budget for the pilot. Each method sees the same seed/fault/budget pairs.
- One latent fault per campaign, or none for negative control.
- Stop at first failed requirement check, or at the campaign budget.
- Fixed/random/model-fixed sequences cannot reorder at run time. Adaptive can select a feasible test and consume leftover budget.
- Common requirement oracles across policies.
- An undervoltage fault causes a subthreshold voltage warning at low load and a failed voltage-limit check at high load. This precursor is **an illustrative model assumption**, not a calibrated flight signature.

## Primary metrics

- **Fault-case detection rate**: fraction of (fault, seed) runs detecting at least one test requirement failure within budget.
- **False-fail rate**: fraction of healthy control campaigns with any failed check.
- **Conditional detection cost**: mean consumed test units until first failure **among detected campaigns only**. This is selection-biased; compare detection-rate curves first.
- **Requirement coverage**: fraction of project-defined requirement IDs assessed, not necessarily passed.
- **Transition coverage**: distinct enumerated legal transition edges traversed; 4 legal edges total in v0.1.

## Interpretive guardrails

- An apparent lead on these toy cases **does not establish** a superior algorithm for spacecraft hardware. These tests are co-designed with faults; targeted mutation/held-out tests must follow.
- 30 repetitions of the same synthetic fault are not 30 independent engineering fault scenarios. Do not put naive confidence intervals across 300 rows and pretend we sampled real spacecraft failures.
- The short time units do **not** correspond to execution seconds; no HIL throughput claim is permitted.
- Detecting a limit violation is not causal diagnosis. The evaluator knows the fault label, the policy does not.
- A zero false-fail rate in healthy toy data is a weakness of this pilot, not a validated operational guarantee.
- The fixed baseline may be weak. The model-fixed ablation provides an informative stronger control. An expert curated fixed baseline is required before publication.
- v0.1 is intentionally light on stochastic sensor dynamics, missing data, calibration, environmental uncertainty and multi-fault interactions.

## Next decisive experiment

Construct *held-out* faults with incipient warning signatures, evaluate both `model_fixed` and `adaptive` on exactly matched scenarios, and predefine a minimum detectable effect. Compare probability of detection and detection-cost distributions within engineering-relevant test budgets. Then port the same test abstraction to UART HIL and measure actual wall-clock time.
