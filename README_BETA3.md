# SAT-V&V v1.0 beta.3 — usability and research comparison corrections

## Changes

1. Telemetry-only layout leaves its layout selector and other controls visible. In this mode only the 3D view is hidden, so it can be restored without a reload.
2. Subsystem cards now use local vector SVG icons, rather than emoji glyphs.
3. Offline-calibration-to-runtime arrows were simplified to remove the overlapping diagonal in the architecture. ML artifacts are loaded before a campaign; calibration does not flow live into telemetry.
4. A new live Technical Reference page (`/reference`) replaces the archived six-tab UI as the primary reference, retaining the previous dashboard at `/classic`.
5. Industry & Research now includes explicit method-by-method comparison plus actual, reproducible within-SAT-V&V synthetic performance bars (v0.9.4; 18 faulty cases per budget per method). External NASA/ESA methods were **not** run in those experiments; no head-to-head superiority claim is made.
6. NASA ICECube loading errors are surfaced; model selection is reverted on failure instead of silently showing the conceptual model while claiming NASA is displayed. ICECube requires external model and Three.js CDN access. Local GLB imports are supported; README and UI document valid format/size, geometry, textures and subsystem-marker limitations.

## Run

`conda activate satvv`

`python -m unittest discover -s tests -v`

`python -m satvv serve`

Then open `http://127.0.0.1:8765`.

## Scientific limitations

This is still a synthetic spacecraft and an interface/presentation release. No physical dynamics, verification procedures or learned model weights were changed. The internal benchmark remains limited to the simulated plant and fault families.

See `docs/GLB_IMPORT_SPEC.md` for GLB import guidance.

## Asset switching limitations
If the hosted Three.js CDN cannot load, the two GLB controls are disabled and the original offline renderer remains visible. If the NASA ICECube download fails, a visible error explains the model was not switched. Download the NASA ICECube file from its source and use **Import local GLB** (with working WebGL) instead. The user-loaded or NASA mesh is not registered to real physical subsystem regions.
