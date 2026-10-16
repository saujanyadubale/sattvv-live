# SAT-V&V v0.9.5 — Research Guide & Graphical Landscape

Software-only research prototype for spacecraft verification. **Not flight-tested, not calibrated against hardware, and not ECSS-certified.**

## What's new since v0.9.4

**No changes to fault simulation, test scheduling, model weights, or benchmark results.** v0.9.5 is a documentation, explanation and graphical comparison release:

1. `/how-it-works`: six-stage interactive walkthrough from spacecraft physics to evidence audit, coupled-subsystem map and a **searchable catalog of all 20 tests**. Choose a procedure to see the **actual project-defined requirement text** from the dynamic traceability matrix, including the ADCS requirements.
2. `/industry`: **documented capability matrix**, **clickable ecosystem workflow**, and **qualitative contribution lanes**. Seven entries (COSMOS, NOS3, ADAPT, HyDE, OPS-SAT-AD, ECSS and SAT-V&V) link to original public sources. This is a **functional-scope comparison**, not a performance ranking or a claim of feature absence.
3. `/`: the existing experiment engine, comparison workspace, technical evidence and old API are preserved. Original `/legacy` dashboard still works.
4. `/api/reference`: returns all twenty executable test definitions and their versioned dynamic requirement descriptions. Read-only, populated from the actual catalog and project specification file.
5. Accessible mobile-friendly pages, browser-tested tutorial controls, search/filter, ecosystem nodes and capability-matrix selections.

## Quick start on macOS

```bash
# Extract ZIP and open a terminal inside the folder SAT-VV-v0.9.5
conda activate satvv
# Dependencies if needed:
conda install -c conda-forge numpy matplotlib scikit-learn -y
python -m unittest discover -s tests -v
python -m satvv serve
```

Open **http://127.0.0.1:8765** in your browser. If an older SAT-V&V server is running, stop it with Ctrl+C first. Hard-refresh using Cmd+Shift+R.

- **Experiment:** `http://127.0.0.1:8765/`
- **How it works:** `http://127.0.0.1:8765/how-it-works`
- **Industry & research:** `http://127.0.0.1:8765/industry`
- **Technical reference:** `http://127.0.0.1:8765/#research`
- **Classic v0.x experiments:** `http://127.0.0.1:8765/legacy`

## Verification status

- **172 automated regression tests passed**, including original v0.9.4 tests plus 6 new public-research-page tests.
- HTML and JavaScript rendered in headless Chromium with page content and assets injected directly. Interactions tested: tutorial navigation, T14 requirement lookup, graphic matrix, ecosystem details and mobile layout. **Direct local URL navigation was blocked by browser administration**, so this is not equivalent to an automated browser test of a live website. HTTP GET endpoints were independently tested using a live local Python server.
- Benchmark figures and CSVs were **carried over unchanged** from v0.9.4. New screenshots are *page-rendering previews* and contain no simulated performance results.

## Credibility and limitations

The public capability matrix uses qualitative categories: *documented focus*, *related scope*, *not assessed*, and *implemented in the SAT-V&V prototype*. A blank is not evidence of absence. The website does not claim that NASA/ESA systems lack any specific capability, that our algorithm is novel, or that synthetic detection percentages can be compared with unrelated external datasets.

Read `docs/v0.9.5_landscape_sources.md` for source links and the evidence basis. Original experimental findings remain in `results/v0.9.4/RESULTS.md` and the versioned protocols under `docs/`.
