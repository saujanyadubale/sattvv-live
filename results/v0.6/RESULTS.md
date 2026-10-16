# SAT-V&V v0.6 — Seeded synthetic forecast pilot

**Configuration:** 5-minute-ahead point forecast; 28 training, 28 independent calibration, and 28 held-out evaluation campaigns. Seven scenario families; altered onset and severity at evaluation. Values below are produced by `python -m satvv bench-forecast --train-seeds 4 --calibration-seeds 4 --eval-seeds 4`.

| Predictor | Voltage MAE (V) ↓ | Temperature MAE (°C) ↓ |
|---|---:|---:|
| Persistence | 0.0546 | 3.1591 |
| Physics baseline | **0.0545** | 1.1534 |
| Linear trend | 0.0941 | **0.7114** |
| Gradient boosting | 0.0621 | 1.1553 |

**The learned regressor is not the best model on either signal in this pilot.** The linear trend is notably effective for this smooth thermal simulator, but it creates 33 spurious voltage crossing predictions and misses the sole actual sampled voltage future violation.

For temperature, among 20 eligible future-violation **points** in the evaluation trajectories, gradient boosting predicted 15 (75% recall) and linear trend predicted 14 (70% recall). Both have 0 false forecast-positive points in this small benchmark, giving 100% event precision among their predicted positives. Forecast points within a campaign are correlated; these are *not* 20 independent events. The small count precludes a reliable safety claim. The first correctly predicted warning in applicable runs preceded threshold crossing by a median 225 s for ML and 210 s for linear trend.

Voltage has only **1** eligible future threshold-violation point in these pilot evaluation scenarios. Precision and recall are uninformative for flight prognostics. The experiment needs longer/higher-load, physically justified scenarios and independent validation.

The learned model's nominal **90% whole-campaign interval target** achieved:

| Signal | Point coverage | Entire-campaign coverage |
|---|---:|---:|
| Voltage | 96.1% | **82.1%** |
| Temperature | 98.7% | **92.9%** |

Voltage coverage is **below target** at the whole-campaign level under shifted evaluation conditions. This is not a flaw to conceal; it flags that the calibration assumption is imperfect. These coverage rates are empirical, not probabilities of individual faults.

### Changes validated

- Model-fixed ordering now precommits to a catalog schedule without telemetry feedback.
- 1.30 A dynamic simulator article has explicit versioned requirement traceability; 2.60 A remains in the historical v0.1 model for reproducibility.
- T14 voltage tolerance now uses absolute residual.
- The v0.6 forecast inputs are causal and the predictor never receives future samples or hidden failure labels.
- Backend smoke tests and JavaScript rendering checks passed (browser preview is based on the same exported Python result data).

**Limitations:** purely synthetic uncalibrated spacecraft simulator; shared fault families across splits; time-correlated evaluation points; forecast models not yet connected to scheduling; no physical or real-flight validation.
