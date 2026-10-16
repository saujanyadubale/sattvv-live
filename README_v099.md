# SAT-V&V v0.9.9 release notes

- Conceptual rotatable 3D spacecraft and ground station synchronized with recorded randomized challenge verification.
- Six subsystem labels and highlight states driven only by observed test records.
- Interactive camera rotation, zoom, and auto-zoom when a failed requirement check occurs, plus a magnified area of the tested subsystem. This is **not physical fault localization**.
- Communication test animates a conceptual ground telemetry link; no actual RF simulation added.
- Magenta ground-truth highlight only after an explicit post-run reveal, at replay timestamps within the injected fault interval.
- Layouts: 3D + telemetry, 3D focus, telemetry only. Reduced-motion support.
- Expanded `/how-it-works` with the actual Isolation Forest, supervised gradient boosting classifier, gradient boosting forecasters, Random Forest ranking, Bayesian hypothesis updates, five test-selection policies, classical detectors, physics simulation and deterministic audit.
- Source-linked deep dive: `docs/v0.9.9_models_and_algorithms.md`.
- Existing research algorithms, fault generators, and test-procedure catalog remain unchanged from v0.9.8.
- Validated with 200 automated unit tests and a headless browser rendering fixture using actual Python-simulator results. Direct local HTTP navigation is restricted by the browser harness; HTTP server endpoints checked by tests.

No flight-validated probability, fault location, radio propagation, or operational performance claims.
