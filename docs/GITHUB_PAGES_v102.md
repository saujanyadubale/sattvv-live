# SAT-V&V v1.0.2 — GitHub Pages deployment

The static `github-pages/satvv/` directory can be copied into the root of `saujanyadubale.github.io` and published at `/satvv/`. It presents **four archived simulation replays**, including a v1.0.2 test-planner example, without executing Python in the browser. It uses the portfolio's charcoal/mint styling and bundled conceptual visualization. Do not represent this static showcase as a hosted live fault generator.

**Publishing:** extract `SATVV_v1.0.2_GITHUB_PAGES_DROPIN.zip`; copy its `satvv/` folder to the repository root; review the diff; commit/push once approved. Link to `/satvv/` from the portfolio's selected research projects section. The portfolio repository is **not modified by this packaging step**.

**Backend:** The local Python server provided in the complete project is for local research. Running Python simulations for public visitors requires a separately secured backend, request budgeting, process isolation, concurrency protections and HTTPS; GitHub Pages cannot host Python services. Do not expose the local preview server to the Internet.

**Research status:** Simplified synthetic physics, expert-specified uncalibrated risks, limited benchmark seeds, no flight qualification or safety guarantee. Archived examples are illustrations, not evidence that every fault is detected or the new planner dominates all baselines.
