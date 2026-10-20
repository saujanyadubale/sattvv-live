"""EXPERIMENTAL: causal Isolation Forest + supervised fault-state telemetry watcher.

Inputs are observable time-series samples ONLY; thresholds and models come
from the original v0.5 synthetic training protocol. No inferred fault labels,
flight-qualified anomaly probabilities, or formal PASS/FAIL values are produced.

A classifier answers "active fault-like behaviour?", NOT which subsystem failed.
Subsystem soft cues require an independent *observable* signature. The two
models use shared features/training physics, so agreement is not independent
statistical evidence and the two probabilities must not be multiplied.
"""
from __future__ import annotations
from collections import deque
from math import isfinite
from .monitoring import engineer_features, feature_matrix


class FusedTelemetryMonitor:
    """Observe each NEW telemetry timestamp (during and between test decisions)."""
    def __init__(self, models, persistence=2):
        if persistence < 1:
            raise ValueError('persistence must be positive')
        self.models = models
        self.rows = deque(maxlen=25)  # >= 180 s lookback at 10-second cadence
        self.events = []
        self.last_time = -1.0
        self.latest = {}
        self.active_cues = {}
        self._hits = 0
        self._latched = False
        self.samples = 0
        self.persistent = persistence

    def update(self, observation, weak_risks=None):
        t = float(observation['time_s'])
        if not isfinite(t) or t <= self.last_time:
            return None  # avoid duplicate timestamp and RNG-independent double counting
        self.last_time = t
        self.samples += 1
        # Explicit whitelist: hidden fault episodes, oracle, future rows are unavailable.
        allowed = ('time_s', 'mode', 'battery_soc_pct', 'load_w', 'bus_voltage_v',
                   'bus_current_a', 'temperature_c', 'redundant_temperature_c',
                   'packet_loss_fraction', 'solar_w', 'alarms')
        self.rows.append({k:observation[k] for k in allowed})
        features = engineer_features(list(self.rows))[-1]
        vector = feature_matrix([features])
        if_score = float(-self.models['isolation_forest'].score_samples(vector)[0])
        gb_score = float(self.models['gradient_boosting'].predict_proba(vector)[0,1])
        if_flag = if_score > float(self.models['iforest_threshold'])
        gb_flag = gb_score > float(self.models['gb_threshold'])
        # Alert if either model fires (higher sensitivity, may have more false warnings).
        flagged = if_flag or gb_flag
        self._hits = self._hits + 1 if flagged else 0
        self._latched = self._latched and flagged
        self.latest = {'time_s':t,'iforest_score':round(if_score,5),
            'iforest_threshold':round(float(self.models['iforest_threshold']),5),
            'iforest_warning':if_flag,'supervised_fault_score':round(gb_score,5),
            'supervised_threshold':round(float(self.models['gb_threshold']),5),
            'supervised_warning':gb_flag,'warning':flagged,
            'warning_persistent':self._hits>=self.persistent}
        # The models do NOT classify the cause. Physical weak-signal indicators
        # instead identify a candidate subsystem, without consulting fault truth.
        cues = {}
        if self._hits>=self.persistent:
            if features['residual_v']>.05:
                cues['EPS'] = 2.5
            if features['sensor_disagreement_c']>.43:
                cues['THERMAL'] = 2.5
            if features['mode_downlink'] and features['packet_loss']>.057:
                cues['COMMS'] = 2.5
            # Optional independent model-residual soft cues can localize common
            # heating even when thermometers agree. This is not fault diagnosis.
            for subsystem, value in (weak_risks or {}).items():
                cues[subsystem] = max(cues.get(subsystem,0.), min(3.,float(value)))
            if if_flag and gb_flag:
                cues = {key:min(4.,value+0.5) for key,value in cues.items()}
        self.active_cues = cues
        if self._hits>=self.persistent and not self._latched:
            event = {'time_s':int(t), 'kind':'ml_telemetry_warning',
                'isolation_forest':if_flag,'supervised_fault_state':gb_flag,
                'candidate_subsystems':sorted(cues),
                'meaning':'Synthetic, advisory model warning; NOT a verified requirement failure.'}
            self.events.append(event)
            self._latched = True
            return event
        return None

    def risks(self):
        return dict(self.active_cues)

    def summary(self):
        return {'sample_count':self.samples,'warning_events':list(self.events),
            'warning_count':len(self.events), 'latest':dict(self.latest),
            'model_scope':'12 engineering features; no trained ADCS fault classifier',
            'fusion':'either model warning with causal persistence; observable subsystem localization only',
            'formal_verification_unchanged':True,
            'limitations':'Shared synthetic training physics; uncalibrated warnings; operating-mode confounding and domain shift.'}
