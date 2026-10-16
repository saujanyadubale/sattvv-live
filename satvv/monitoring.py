"""v0.5 alert detectors. Alerts are NEVER verification PASS/FAIL outcomes.

All algorithms operate exclusively on telemetry, with no access to fault episodes.
Feature windows are causal. Supervised training labels remain isolated in benchmark.
"""
from __future__ import annotations
from math import isfinite
from statistics import median
from .coupled import predict_nominal_voltage

FEATURE_NAMES = ('residual_v','residual_slope_v_min','voltage_v','current_a',
                 'temperature_c','sensor_disagreement_c','packet_loss',
                 'soc_pct','load_w','solar_w','mode_payload','mode_downlink')


def _ols_slope(times, values) -> float:
    if len(times)<3: return 0.
    mt = sum(times)/len(times); mv = sum(values)/len(values)
    denom = sum((t-mt)**2 for t in times)
    return sum((t-mt)*(v-mv) for t,v in zip(times,values))/denom if denom else 0.


def engineer_features(telemetry: list[dict]) -> list[dict]:
    residuals=[]; result=[]
    for i,p in enumerate(telemetry):
        v_expected = predict_nominal_voltage(p['battery_soc_pct']/100, p['load_w'])
        residual = v_expected-p['bus_voltage_v']
        residuals.append(residual)
        # last 3 min only, causal sliding window; times in minutes.
        valid = [j for j in range(i,-1,-1) if p['time_s']-telemetry[j]['time_s']<=180]
        valid.reverse()
        slope=_ols_slope([telemetry[j]['time_s']/60 for j in valid],
                         [residuals[j] for j in valid])
        row={'time_s':p['time_s'], 'residual_v':residual,
             'residual_slope_v_min':slope, 'voltage_v':p['bus_voltage_v'],
             'current_a':p['bus_current_a'], 'temperature_c':p['temperature_c'],
             'sensor_disagreement_c':abs(p['temperature_c']-p['redundant_temperature_c']),
             'packet_loss':p['packet_loss_fraction'], 'soc_pct':p['battery_soc_pct'],
             'load_w':p['load_w'], 'solar_w':p['solar_w'],
             'mode_payload':int(p['mode']=='PAYLOAD'),
             'mode_downlink':int(p['mode']=='DOWNLINK'),
             'threshold_warning':bool(p['alarms'])}
        result.append(row)
    return result


def classical_detector(features: list[dict], method: str) -> list[bool]:
    """Baselines fixed before evaluation; calibrated ML threshold separate."""
    if method not in ('limit', 'trend', 'cusum', 'physics_residual'):
        raise ValueError('Unknown detector method')
    out=[]; acc=0.
    for row in features:
        if method=='limit': flag=row['threshold_warning']
        elif method=='trend':
            flag=(row['time_s'] >= 180 and row['residual_slope_v_min'] > .010)
        elif method=='physics_residual':
            flag=row['residual_v'] > .13 or row['sensor_disagreement_c'] > 1.5
        else:
            acc=max(0., acc + row['residual_v']-.030)
            flag=acc>.30
        out.append(bool(flag))
    return out


def alerts_to_episodes(flags: list[bool], times: list[float], consecutive: int=2) -> list[float]:
    """Debounce alerts and report episode onset times (not number of positive samples)."""
    found=[]; count=0; latched=False
    for on,t in zip(flags,times):
        count=count+1 if on else 0
        if count>=consecutive and not latched:
            found.append(t); latched=True
        if not on: latched=False
    return found


def any_alert_in_fault_interval(alerts: list[float], intervals: list[dict]):
    return any(a>=i['start_s'] and a<i['end_s'] for a in alerts for i in intervals)


def warning_summary(flags: list[bool], telemetry: list[dict], truth: dict) -> dict:
    times=[x['time_s'] for x in telemetry]
    onset=truth['episodes'][0]['start_s'] if truth['episodes'] else None
    alerts=alerts_to_episodes(flags,times)
    valid=[a for a in alerts if any(e['start_s']<=a<e['end_s'] for e in truth['episodes'])]
    return {'warning_episodes':len(alerts), 'first_warning_s':alerts[0] if alerts else None,
            'first_fault_warning_s':valid[0] if valid else None,
            'detection_delay_s':valid[0]-onset if valid and onset is not None else None,
            'detected_during_fault':bool(valid),
            'false_alert_episodes':len([a for a in alerts if not any(
                e['start_s']<=a<e['end_s'] for e in truth['episodes'])])}


def feature_matrix(rows: list[dict]):
    return [[float(r[k]) for k in FEATURE_NAMES] for r in rows]


def predict_methods(telemetry: list[dict], ml_models: dict | None = None) -> dict:
    rows=engineer_features(telemetry)
    times=[r['time_s'] for r in rows]
    output={}
    for method in ('limit','trend','cusum','physics_residual'):
        flags=classical_detector(rows,method)
        output[method]={'flags':flags,'warning_times_s':alerts_to_episodes(flags,times)}
    if ml_models:
        import numpy as np
        x=np.asarray(feature_matrix(rows))
        anomaly = -ml_models['isolation_forest'].score_samples(x)
        flags=(anomaly>ml_models['iforest_threshold']).tolist()
        output['isolation_forest']={'flags':flags,
                     'warning_times_s':alerts_to_episodes(flags,times)}
        prob=ml_models['gradient_boosting'].predict_proba(x)[:,1]
        flags=(prob>ml_models['gb_threshold']).tolist()
        output['gradient_boosting']={'flags':flags,
                     'warning_times_s':alerts_to_episodes(flags,times)}
    return output
