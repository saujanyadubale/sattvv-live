# SAT-V&V v0.9.7 — Interpretation & Interface Correction

This release corrects presentation and adds **post-run diagnosability transparency**, without altering the spacecraft plant, scheduling algorithms, or historical benchmark datasets.

- **Industry page**: deleted equal-length colored bars. Replaced with a non-numeric role diagram. The existing cited focus matrix remains the qualitative comparison; no external performance comparisons are asserted.
- **Navigation**: six labels are present in the same sequence across pages: Experiment, Compare, Random Challenge, How It Works, Industry & Research, Technical Reference. `/#research` now works when navigated to from other pages.
- **Processing indicator**: animation shown while server computes in Experiment and Challenge. It explicitly does not claim backend phase progress. Recorded experiment replay remains separate.
- **Telemetry selection**: two changeable charts offer voltage, main/redundant temperature, sensor disagreement, current, battery SOC, load, solar power, packet loss, and link latency. Signals use actual previously recorded server telemetry, not invented readings.
- **Missed-fault explanation**: after revealing oracle truth, the page displays generated episode onset, end, severity, relevant tests, whether relevant tests overlapped the episode, their outcomes, and recorded numerical measurements/thresholds when available. An overlap or warning is not automatically a failed requirement.

## Reproducing the reported v0.9.6 problem

`mixed, seed 7, budget 90` generates one temperature sensor drift episode active from **4580s to 4930s** with severity **0.482**. It overlaps **T11 from 4860s to 5040s**; the recorded sensor disagreement is approximately **2.7°C** and the project limit is **≤ 3.0°C**, so T11 properly reports PASS. No policy finds a failed check in that case. This is a weak/short injected fault relative to our acceptance criterion, not proof the algorithms or simulator have stopped working. A 90-minute budget does not guarantee a verifiable fault.

## Scope and limitations

The episode-exposure diagnostic uses injected ground truth **after** the run and is never available to the policy. It checks overlap and recorded checks, not mathematical diagnosability of every episode. This is a user-interface/interpretation release, not a method-quality improvement. Historic benchmark percentages remain v0.9.6 results.

Run `python -m unittest discover -s tests -v` and `python -m satvv serve`, then visit `/challenge`, `/industry`, and `/`.
