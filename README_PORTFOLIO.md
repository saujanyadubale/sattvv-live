**v1.0.2 update:** The GitHub Pages showcase now includes a fourth replay from the new bounded planner. This is prerecorded synthetic evidence. For instructions see [`docs/GITHUB_PAGES_v102.md`](docs/GITHUB_PAGES_v102.md).

# SAT-V&V v1.0 — Portfolio Edition

This edition provides **two deliberately separate experiences**:

1. **Full research engine** — Python simulator, five scheduling methods, interactive local web dashboard and the existing reproducible tests. Run with `python -m satvv serve`. This is **not** directly deployable on GitHub Pages.
2. **GitHub Pages research showcase** — the `github-pages/satvv/` directory contains a fully static, interactive replay of archived synthetic simulations, together with research context, the methodology and comparative results. It uses no Python API.

## Design system

Matched against the portfolio's actual `styles.css` on `saujanyadubale/saujanyadubale.github.io`:
- Background `#080d17`, surfaces `#101a27`
- Ink `#f5f3ef`, muted `#9aa9bb`
- Mint `#b5ecdf`, lime `#ccf4b5`
- Headings `Space Grotesk`, body `DM Sans` (with local system fallbacks)

### Fixed UI defects

The reported spacing issue was inside **expanded algorithm explanation panels**, where the details paragraph appeared flush with its borders. These panels now have an inset content area, a divider below the summary, generous bottom padding and safe code wrapping. Form selectors have uniform insets as well.

The spacecraft background includes a higher-contrast deep starfield and distant atmospheric limb behind both the WebGL and offline canvas renderer. The backdrop is aesthetic, not orbital data.

## Publish as `https://saujanyadubale.github.io/satvv/`

1. Extract **SATVV_GITHUB_PAGES_DROPIN.zip**.
2. Copy the enclosed **`satvv/`** folder to the root of the `saujanyadubale.github.io` repository. Preserve its relative asset paths.
3. Commit and push to `main` (or use your existing GitHub Pages deployment workflow).
4. Open `https://saujanyadubale.github.io/satvv/` and check the replay, file download, stars and mobile layout.
5. Add a portfolio project card pointing to `/satvv/`. An optional ready-to-adapt card snippet is provided in the drop-in ZIP.

**Important:** The static scenario picker switches between three *recorded simulations*. It is not a live fault generator. New simulation experiments need the separate Python app or a deliberately deployed, secured backend. Do not point the GitHub Pages frontend at `localhost` or expose the built-in Python preview server publicly.

## Full simulation locally

```bash
conda activate satvv
python -m unittest discover -s tests -v
python -m satvv serve
```

Open `http://127.0.0.1:8765` on the same machine. For public simulation, deploy a separate production API with HTTPS, authentication/rate limiting where needed, resource and concurrency budgets, and observability.

## Research limitations

All campaign data are synthetic. The visualizer is conceptual subsystem geometry and does not localize physical faults. The Bayesian hypothesis weights are uncalibrated, and the test-selection methods have not been independently flight-validated. The benchmark section compares our algorithms only, under a common synthetic protocol.
