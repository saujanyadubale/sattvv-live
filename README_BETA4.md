# SAT-V&V v1.0 Beta.4 — Usability & 3D Model Reliability

This is a **synthetic, software-only research prototype**, not a flight-qualified spacecraft verification system.

## Changes

### 1. Compare Methods works without running a separate experiment

- Choose experiment/challenge mode, intensity, seed and budget in the **Configure experiment** controls.
- Click **02 · Compare methods** in the top navigation, or the **Compare 5 strategies** control.
- The comparison section is always visible at the `/#compare-workspace` anchor.
- Click **Compare all five methods**. The server runs five independent, reproducible campaigns using the selected settings.
- Per-policy progress text is displayed while results arrive. Partial results remain visible if a later policy fails. Settings changes clear the previous table to prevent misleading reuse.
- This is an internal paired **synthetic** benchmark. Strategies can affect the simulated trajectory differently. It is not a head-to-head comparison with NASA/ESA systems.

### 2. Two working, bundled spacecraft shapes

The geometry selector now offers:

- **Solar-array satellite · bundled:** a larger conceptual spacecraft with deployed rectangular solar arrays.
- **Compact 6U CubeSat · bundled:** a distinct, compact spacecraft with body-mounted solar cells and a different payload/antenna silhouette.
- **Custom GLB · loaded locally:** visible after a successful import.

Both built-in models work without any NASA model download, provided the Three.js WebGL renderer loads. The remote NASA ICECube selector was removed because a compressed model that fails to load is not a meaningful selectable option. NASA assets can still be downloaded from https://science.nasa.gov/3d-resources/ and imported through the local GLB control.

Imported meshes must be binary glTF 2.0 (.glb), non-empty and <=30 MB. The decoder is configured for Draco-compressed geometry (decoder may need network access). Import still uses **conceptual diagnostic zones**, not automatically inferred model-specific component geometry. See `docs/GLB_IMPORT_SPEC.md`.

### 3. Backdrop stars

The Three.js renderer now uses a transparent background over a subdued CSS starfield. Stars are visually **behind** the model, not opaque particles floating in front of spacecraft components. When the WebGL engine is unavailable, the existing schematic fallback continues to work.

### 4. What was not changed

No changes were made to the spacecraft dynamics, 20 verification procedures, forecasting models, trained ML policies or fault-diagnosis logic. The synthetic benchmark results from earlier releases are therefore not replaced or reinterpreted.

## Run on Mac

```sh
conda activate satvv
conda install -c conda-forge numpy matplotlib scikit-learn -y
python -m unittest discover -s tests -v
python -m satvv serve
```

Open http://127.0.0.1:8765/ . Stop an older server first with Ctrl+C. Refresh with Cmd+Shift+R if an older UI appears.

## Validation

- 232 Python unit tests passed, including six Beta.4 UI contracts.
- JavaScript files passed Node syntax checks.
- A dynamic JavaScript handler test simulated the Compare Methods button without a previous run and confirmed five requests, five rows, and restored controls.
- The `/api/unified` backend returned valid results for all five policies in the same single-fault campaign.
- Live WebGL interaction on the user's Mac remains to be checked: the isolated Chromium instance here blocks navigation to local HTTP and `file://` URLs.

## Further work

Before the public release, prioritize a repeatable Mac browser acceptance check (especially WebGL models), an accessible textual comparison summary, stronger fault-detectability benchmark design, and independent physical validation.
