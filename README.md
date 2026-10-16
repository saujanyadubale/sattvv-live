# SAT-V&V v1.0.2 — Risk-aware verification planning

**Current patch notes:** [`README_V102.md`](README_V102.md). The preserved v1.0.1 baseline is documented in [`README_V101.md`](README_V101.md). The unified Python experiment application and a separate static GitHub Pages showcase are included. The project is synthetic and not flight-validated.

# SAT-V&V v1.0 — Final local research showcase

For final release instructions and deployment limitations, read [README_RELEASE.md](README_RELEASE.md) and [V1_PUBLIC_RELEASE_CHECKLIST.md](docs/V1_PUBLIC_RELEASE_CHECKLIST.md).

# SAT-V&V v1.0 beta.3

Latest changes and validation: [README_BETA3.md](README_BETA3.md)

# SAT-V&V v1.0 beta.1 — Mission Replay Refinement

This release builds on v1.0 beta. It retains the simulation, twenty test procedures, five policies, random challenge generator and evidence audit, and improves the visual research experience.

- Ground station: parabolic dish surface, stiffening ribs, elevation yoke, feed support and RF enclosure; positioned farther from the spacecraft. This geometry is generated locally and is **not an imported real antenna CAD model**.
- Optional NASA ICECube spacecraft model and local GLB upload remain available, with source attribution and offline schematic fallback.
- Subsystem labels: **Clean (active only)**, Annotated (all), or Hidden; smaller overlays avoid obscuring the model.
- Engineering system architecture: a real directed SVG flowchart, with monitor/forecast branches, explicit feedback from executed tests, and a separate offline-trained-model lane. Interactive nodes explain their methods.
- The physics models, ML algorithms, fault generator and benchmark scripts are unchanged from v1.0 beta.

**Quick start:** `conda activate satvv`, then `python -m unittest discover -s tests -v`, then `python -m satvv serve`. Open `/challenge` for mission replay and `/how-it-works` for the diagram.

**Research boundary:** Visualization does not constitute flight hardware CAD, verified antenna geometry or a measured radio link. Test highlighting indicates a checked subsystem, not proven fault-root-cause localization. Recorded results are synthetic.

See `README_BETA.md` and `docs/v1.0-beta.1_release_notes.md` for more details.

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

The online viewer retrieves a GLB from NASA's public GitHub resource if available. The official binary is **not** bundled with this project. Select **Enhanced conceptual spacecraft** to use the built-in WebGL geometry. If third-party JS dependencies are unavailable, the app falls back to the fully local pre-existing projection viewer. Source links and attribution do not imply NASA/ESA involvement, approval, or endorsement of SAT-V&V.

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

This beta is for review before a final 1.0 release.

---

Earlier v0.9.9 technical release: `README_v099_archive.md`.

## Latest review release: v1.0 Beta.2

The homepage unifies the manually selected experiment and seeded random challenge workflows, with shared 3D replay, explanatory telemetry charts and review-only next-action suggestions. See [README_BETA2.md](README_BETA2.md) for the new features, controls, limitations and the reproducible 90-minute subtle-drift example.

## Beta.4 update

See [README_BETA4.md](README_BETA4.md) for the fixed comparison workflow, two bundled spacecraft visual models and starfield design.
