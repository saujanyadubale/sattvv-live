# SAT-V&V v0.9.8 — Challenge clarity and loading feedback

- Added a visible spinner on the Generate & Run button and a loading status by the simulation output. These indicate **backend activity**, never percent completion.
- Added a high-impact challenge intensity option with earlier, longer, stronger physical fault episodes. For a mixed challenge it creates **exactly two distinct mechanisms**. The older exploratory profile and seeded cases remain available unchanged.
- Added six compact time-synchronized measurement readouts to the replay alongside the selectable telemetry plots.
- The complete simulator, test strategies and research pages are preserved.

## Interpretation

In the original exploratory `mixed / seed 7 / 90 min` challenge, a sensor drift starts at 76m20s and ends at 82m10s. T11 overlaps the episode but measures 2.7 °C disagreement, below its 3 °C requirement limit. This is a correctly missed *requirement failure*, not necessarily a missed detectable violation. In high-impact mode, this seed generates two sustained faults and is a separate experimental condition. **No detection is guaranteed by either mode.** Comparisons must match challenge profile, seed, budget and environment. Strong scenarios must not be used to inflate performance metrics relative to the exploratory benchmark.

Run `python -m unittest discover -s tests -v` then `python -m satvv serve`. Open `/challenge`.
