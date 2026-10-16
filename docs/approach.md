# Project 1 — Technical approach and execution backlog

## Hypothesis and contribution

**H0:** A state/requirement-aware adaptive test policy does not improve probability of detecting a fault within a limited campaign time over competitive fixed and random test strategies on the same test bench.

**H1:** Adaptive selection increases detection probability, or reduces test effort at equivalent detection probability, when telemetry can reveal useful but non-failing precursors of latent faults.

The contribution is the **evaluation methodology**: explicit state and requirement models, observable-only policy input, diverse test-selection controls, measured cost/coverage curves, event evidence and reproducible faults. It is *not* claiming that any one greedy score is scientifically novel.

## Hardware-independent architecture

| Component | Input | Output | v0.1 | Next revision |
|---|---|---|---|---|
| Test strategy | Past checks, state/transition coverage, sensor observations, remaining budget | Next test procedure | Implemented | Explainable priority/audit trail |
| Procedure catalog | Precondition, test goal, expected checks, cost | Scripted state sequence | Implemented | Declarative YAML/JSON procedures |
| Emulator adapter | Procedure + hidden environmental/fault configuration | Public telemetry, state transitions | Implemented | Stateful event/command loop |
| Assertion engine | Required check + telemetry/observed state | PASS/FAIL with evidence | Implemented | Limits, tolerances, timestamped events |
| Benchmark harness | Fault/scenario grid, policies, seeds | CSV summary and plot | Implemented | Confidence intervals clustered by fault scenario |
| Serial interface | Framed commands and packets | Hardware telemetry | Not started | Pico/ESP32 UART first, CAN optional |
| Visualization | Traces and metrics | Interactive EGSE dashboard | Static chart only | Live Streamlit or web UI |

## Five-stage implementation roadmap

### Phase A — Research-ready simulated MVP (COMPLETE)
- [x] Test catalog with requirement IDs and synthetic costs.
- [x] Spacecraft operational mode traversal.
- [x] Fault injection isolated from strategy input.
- [x] Scripted, randomized and adaptive selection strategies.
- [x] Stronger model-planned-static control.
- [x] Repeatable benchmark and evidence export.
- [x] Automated test suite and basic chart.

### Phase B — Credible simulation (NEXT)
- [ ] Move from cold-start procedures to time-stepped, persistent spacecraft state.
- [ ] Model battery state of charge, bus rail dynamics, thermal inertia, payload duty cycle, radio link conditions, finite telemetry buffering.
- [ ] Separate simulator dynamics from assertion/oracle definitions to reduce benchmark circularity.
- [ ] Create packet schema: command ID, sequence number, timestamp, CRC, ACK/NACK; event log with monotonic simulation time.
- [ ] Add severity sweeps and intermittent faults, noisy/missing telemetry, and clean-vs-fault matched scenarios.
- [ ] Introduce fixed **expert-prioritized** campaigns and randomized property-based command generation.
- [ ] Add a risk model, explicit coverage reward ablation, and a no-feedback version for every adaptive experiment.

### Phase C — EGSE + hardware-in-the-loop
- [ ] Microcontroller firmware with safe nominal mode/state machine and UART telemetry.
- [ ] Python serial adapter implementing the same public emulator interface.
- [ ] Safe low-voltage test fixtures; isolate fault injection and prevent destructive shorts/overheating.
- [ ] Test repeatability, real elapsed duration, packet/USB latency, synchronization, and power consumption.
- [ ] Evidence per run: firmware SHA, code SHA, operator, date, setup revision, test inputs, telemetry, verdict.

### Phase D — Experimental campaign
- [ ] Freeze requirements, failure modes and baseline definitions before comparisons.
- [ ] Measure detection probability vs **wall-clock** campaign duration; compare at matched false-failure constraints.
- [ ] Vary seeds and fault severity, grouped by fault family and run batch; include unseen modes for held-out robustness.
- [ ] Bootstrap at scenario/fault-family level rather than misreporting repeated random seeds as independent examples.
- [ ] Report failure modes, regression cases, effect sizes and detection-time distributions.

### Phase E — Engineering communication
- [ ] Requirement/verification control matrix and reviewable report.
- [ ] Evidence explorer dashboard, mode diagram, plot and reproducible HIL demo video.
- [ ] Publish source, synthetic dataset and hardware-safe instructions.

## Core engineering questions to settle before buying hardware

1. Is the target job family mostly AIT/EGSE, flight software V&V, or systems-test automation? It controls how ambitious our HIL must be.
2. Is ESP32 or Pico available already, and do we have basic multimeter + 3.3V/5V power setup?
3. How many hours per week can we dedicate? A 2-week focused prototype and a 6-week slower build are both possible, but have different evidence quality.

## Acceptance gates

- **Gate 1 (today):** reproducible synthetic benchmark, runnable source and explicit scientific caveats.
- **Gate 2:** stable requirement/telemetry schema, no hidden fault labels in strategy, validated independent scenario harness.
- **Gate 3:** HIL produces timestamped reproducible traces and no-fault campaigns pass across repeated runs.
- **Gate 4:** robust conclusions survive stronger baseline and sensitivity experiments.
