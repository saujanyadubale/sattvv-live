# SAT-V&V · GLB asset import specification (v1.0 beta.3)

- **Accepted file:** GLB, binary glTF 2.0 (`.glb`), 1–30 MB; empty or oversized files rejected.
- **Textures:** embedded images/materials only for portable, offline loading. External textures or `.gltf` companion `.bin` files are not supported by the one-file picker.
- **Scene:** at least one non-empty mesh, finite bounds; loader normalizes uniform scale and centers model at the origin.
- **Best practice:** export from Blender via *File → Export → glTF 2.0 → glTF Binary (.glb)*; apply transforms, reduce detail for browser performance, avoid Draco/KTX2 compression unless explicitly supported by the renderer.
- **Coordinates:** arbitrary scale is normalized. Align spacecraft longitudinal axes with the preview orientation when possible.
- **Subsystem markers:** diagnostic overlays are generic fixed positions defined for the conceptual craft. They are **not** automatically retargeted to uploaded NASA/custom mesh components. A custom model does not carry validated EPS, ADCS or thermal mapping.
- **Fallback:** remote NASA ICECube URL requires access to GitHub raw content; if unavailable, the UI keeps the current local model and displays a clear error; import a downloaded GLB using the local picker instead.
- **Security/privacy:** browser reads the user-selected file and creates a temporary object URL. The file is not posted to the Python service. Only load models from trustworthy sources.
- **Source:** NASA ICECube https://science.nasa.gov/3d-resources/cubesat-icecube/ ; NASA 3D Resources https://github.com/nasa/NASA-3D-Resources . Respect NASA usage guidance.
