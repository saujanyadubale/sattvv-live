# SAT-V&V v1.0 beta.1 — Research Visualization & Transparency

**Beta release** · Research prototype · Not flight-validated or ECSS certified.

## What's new

- Optional realistic spacecraft geometry: locally generated detailed 3D conceptual bus with solar cells, frame, avionics surfaces, plus a separately positioned procedural parabolic ground terminal and feed assembly, rendered with WebGL via Three.js. On capable networks the viewer can load a **NASA CubeSat ICECube GLB** (not bundled). A user can also upload their own local .glb under 30 MB. Existing offline canvas viewer remains the fallback.
- Replay synchronization: markers correspond to the *subsystem being tested*, a checked requirement can fail, and after deliberate reveal the generated injected fault locations can be highlighted. These are **conceptual subsystem region annotations**, not known geometric instrument coordinates or physically validated fault localization.
- How It Works: interactive, truly directed SVG flowchart with eight runtime stages, parallel monitoring/forecasting branches, feedback from verification results, and separate offline training/calibration lanes. Every node describes the actual method in use.
- Industry Research: improved professional contribution framing; graphical capability map remains grounded in published documentation, not synthetic performance comparisons.
- Existing fault generation, spacecraft physics, 20-procedure catalog, five test selection strategies, quantitative results, historical benchmarks and deterministic audit preserved.

## Run

From this folder:

```bash
conda activate satvv
python -m unittest discover -s tests -v
python -m satvv serve
```

Open:
- http://127.0.0.1:8765/challenge — challenge generator and mission viewer
- http://127.0.0.1:8765/how-it-works — architecture and model guide
- http://127.0.0.1:8765/industry — research landscape

## 3D model availability and attribution

**NASA model:** NASA 3D Resources, *CubeSat – ICECube*, model source NASA/Christopher R. Meaney.
- Official source and download: https://science.nasa.gov/3d-resources/cubesat-icecube/
- Source repository: https://github.com/nasa/NASA-3D-Resources
- NASA media usage guidelines: https://www.nasa.gov/nasa-brand-center/images-and-media/

The online viewer retrieves a GLB from NASA's public GitHub resource if available. The official binary is **not** bundled with this project. Select **Detailed local spacecraft** to use the built-in WebGL geometry. If third-party JS dependencies are unavailable, the app falls back to the fully local pre-existing projection viewer. Source links and attribution do not imply NASA/ESA involvement, approval, or endorsement of SAT-V&V.

The optional renderer depends on browser access to `cdn.jsdelivr.net` for Three.js and on GitHub Raw for NASA geometry. If fully offline demonstration is essential, use the bundled original viewer. The beta does not silently download executables.

## Science and safety limitations

- This is a synthetic, software-only verification testbed. No flight CAD, orbital dynamics, calibrated hardware telemetry or live ground-station RF connection.
- The NASA ICECube is not the physical spacecraft underlying our generic simulator. It is visual reference geometry. Subsystem hotspots are intentionally approximate and do not claim any specific NASA component location.
- A red region corresponds to a **failed requirement check for a tested subsystem**. It does not establish the root cause or prove a local hardware failure.
- A separate ground-truth annotation is allowed only after post-run reveal; no hidden label is accessible to the live verification scheduler.
- Machine learning models are trained on synthetic campaigns; hypothesis weights and forecast bands are not calibrated to flight data.
- Public internet hosting requires additional resource limiting and security hardening. Local server is intended for trusted use.

## Implementation

- `web/mission_beta.js` — optional WebGL renderer and GLB loader, not spacecraft physics.
- `web/mission3d.js` — retained offline fallback for the same replay.
- `web/workflow_beta.js` — descriptions and click interactions for the live/offline architecture.
- `web/how-it-works.html` — sourced model methods and clickable flow.
- `web/industry.html` — documented-capability comparison and research framing.
- `tests/test_v10_beta.py` — release contracts.

This beta.1 review release refines presentation without modifying simulated physics or model training.
