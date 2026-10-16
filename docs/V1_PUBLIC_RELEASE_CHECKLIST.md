# SAT-V&V v1.0 — Public release and deployment checklist

## Intended claims

SAT-V&V is a **software-only research prototype** exploring adaptive spacecraft verification. It contains simplified, coupled subsystem physics, twenty project-defined verification procedures, five test-selection strategies, ML anomaly/forecasting baselines, heuristic early warnings, and recorded evidence/replay. The interactive 3D spacecraft and ground terminal are conceptual visualizations, not flight CAD or validated fault localization. The research results are synthetic, diagnosis weights are uncalibrated, and no flight or hardware qualification has been performed.

## Local quick-start

From the extracted project directory, activate a Python environment containing NumPy, matplotlib, and scikit-learn. Run:

```shell
python -m unittest discover -s tests -v
python -m satvv serve
```

Visit `http://127.0.0.1:8765`. Main pages: experiment `/`, comparison `/#compare-workspace`, workflow `/how-it-works`, industry `/industry`, reference `/reference`, and optional classic archive `/classic`.

## Public hosting: **not** a production server

The bundled `ThreadingHTTPServer` listens on `127.0.0.1` and is meant for a local demo. **Do not simply bind it to `0.0.0.0` and expose it on a public website.** There is no authentication, cross-user workload isolation, concurrency admission control, or infrastructure rate limiting. The simulation endpoints can consume material CPU/time per request. Before hosting publicly:

- Put compute requests behind a production application service with request-size limits, per-user/anonymous quotas, concurrency limits, timeouts, and monitored job execution.
- Validate all public input bounds server-side and check error handlers for uncontrolled exceptions. Keep the experiment engine isolated from other host services.
- Serve static content through a hardened HTTPS static host/reverse proxy with appropriate Content Security Policy, logging, and caching; bundle or allowlist the Three.js dependencies.
- Set up reproducible builds, dependency pinning, vulnerability/license review, uptime checks, and monitored error logging. Test mobile/desktop and keyboard navigation.
- Make a prominent, permanent disclosure that all experiment telemetry and model decisions are synthetic and not flight-qualified. Never call suggested actions validated spacecraft repairs.
- Perform a privacy and permissions review before adding user accounts, telemetry uploads, analytics or data sharing. Do not upload proprietary flight telemetry without authorization.

## Credits and assets

Two bundled spacecraft geometries and the ground dish are generated procedurally in source. The starfield is an original static SVG. The optional local GLB importer expects a valid glTF 2.0 GLB (consult `docs/GLB_IMPORT_SPEC.md`). NASA binaries are **not** bundled. Where a third-party model is used later, review its actual license and attribution requirements. Three.js is loaded from a CDN for optional WebGL; a dependency-free canvas view is retained as fallback.

## Scientific acceptance gate

- Demonstrate a healthy control without false verification failure.
- Demonstrate a known injected fault with an actual failed requirement and numerical evidence.
- Demonstrate a weak injected fault which remains within formal limits but may produce a separate warning.
- Reproduce method comparison at a fixed seed, budget and initial scenario; report detection delay, false positives and hypothesis accuracy **separately**.
- Avoid comparative superiority claims based on a small or synthetic-only benchmark.

## UI acceptance gate

- Verify five main navigation destinations, direct Compare Methods, all scenario types, replay, reset, 3D/data view switching and GLB import failure feedback.
- Confirm final v1.0 branding, the six decision icons, all dropdown padding, the decorative background starfield, and reduced-motion/keyboard behavior.
- Confirm charts, reports and downloads are meaningful when experiments produce no failed requirement.

The public website integration should be done as a separate, security-reviewed deployment task. Passing unit tests and local UI checks does **not** establish production security or scientific validation.
