# SAT-V&V v1.0 — Final local demonstration release

This builds on v1.0 Beta.4 and **does not change spacecraft simulation equations or verification/ML algorithms**. The final polish adds:

1. Six consistent SVG line icons for the closed-loop Detect / Predict / Diagnose / Verify / Audit / Boundary overview.
2. Uniform, accessible dropdown spacing and dark, native-independent chevron styling across the five-page interface.
3. A denser but unobtrusive starfield and atmospheric-color depth background behind both WebGL and the dependency-free 3D fallback, never in front of the spacecraft.
4. Final v1.0 branding on the primary pages and in API health and experiment metadata.
5. Additional presentation/asset tests and a public-hosting checklist.

Run `python -m unittest discover -s tests -v` and `python -m satvv serve`. Open `http://127.0.0.1:8765`. See `docs/V1_PUBLIC_RELEASE_CHECKLIST.md` before any public deployment. This server is a **local preview**, not a production web service.

Limitations remain: the toy simulator is not flight-calibrated; ML and Bayesian outputs are not calibrated physical fault probabilities; some injected faults are intentionally too weak or brief to violate any requirement; runtime Three.js requires network access for optional enhanced graphics, with an offline renderer fallback. Previous synthetic benchmark results are included for reproducibility, not as evidence of superiority over industry tools.
