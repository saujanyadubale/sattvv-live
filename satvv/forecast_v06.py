"""v0.6: causal, campaign-separated voltage/thermal point forecasts.

The forecast is a *prediction*, never an executed verification test. Explicit
simulation futures exist only in the trainer/evaluator, not in model features.
This is a synthetic research module, not operational spacecraft prognostics.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil, isfinite
from statistics import mean
from typing import Any

from .coupled import SCENARIOS, predict_nominal_voltage, simulate_health
from .monitoring import engineer_features, _ols_slope

SIGNALS = ('bus_voltage_v', 'temperature_c')
LIMITS = {'bus_voltage_v': 6.70, 'temperature_c': 70.0}
METHODS = ('persistence', 'physics_baseline', 'linear_trend', 'gradient_boosting')
FEATURES = (
    'bus_voltage_v', 'temperature_c', 'battery_soc_pct', 'bus_current_a',
    'load_w', 'solar_w', 'redundant_temperature_c', 'residual_v',
    'residual_slope_v_min', 'voltage_slope_v_min', 'temperature_slope_c_min',
    'soc_slope_pct_min', 'sensor_disagreement_c', 'packet_loss',
    'mode_safe', 'mode_payload', 'mode_downlink',
)


def _require_horizon(horizon_s: int) -> None:
    if type(horizon_s) is not int or horizon_s not in (120, 300, 600):
        raise ValueError('horizon_s must be exactly 120, 300 or 600 seconds')


def features_for_forecasting(telemetry: list[dict]) -> list[dict]:
    """Input rows have *only* measurements available up to that timestamp."""
    if len(telemetry) < 4:
        raise ValueError('Need at least four telemetry samples')
    engineered = engineer_features(telemetry)
    out = []
    for i, p in enumerate(telemetry):
        # Restrict to previous 180 s, never include later rows.
        ids = [j for j in range(i + 1) if p['time_s'] - telemetry[j]['time_s'] <= 180]
        times = [telemetry[j]['time_s'] / 60. for j in ids]
        def trend(key):
            return _ols_slope(times, [telemetry[j][key] for j in ids])
        row = {
            'time_s': float(p['time_s']),
            'bus_voltage_v': float(p['bus_voltage_v']),
            'temperature_c': float(p['temperature_c']),
            'battery_soc_pct': float(p['battery_soc_pct']),
            'bus_current_a': float(p['bus_current_a']),
            'load_w': float(p['load_w']),
            'solar_w': float(p['solar_w']),
            'redundant_temperature_c': float(p['redundant_temperature_c']),
            'residual_v': engineered[i]['residual_v'],
            'residual_slope_v_min': engineered[i]['residual_slope_v_min'],
            'voltage_slope_v_min': trend('bus_voltage_v'),
            'temperature_slope_c_min': trend('temperature_c'),
            'soc_slope_pct_min': trend('battery_soc_pct'),
            'sensor_disagreement_c': engineered[i]['sensor_disagreement_c'],
            'packet_loss': engineered[i]['packet_loss'],
            'mode_safe': int(p['mode']=='SAFE'),
            'mode_payload': int(p['mode']=='PAYLOAD'),
            'mode_downlink': int(p['mode']=='DOWNLINK'),
        }
        out.append(row)
    return out


def _feature_vector(row: dict) -> list[float]:
    return [float(row[k]) for k in FEATURES]


def _baseline(row: dict, signal: str, method: str, horizon_s: int) -> float:
    current = float(row[signal])
    if method == 'persistence':
        return current
    if method == 'linear_trend':
        slope = row['voltage_slope_v_min'] if signal == 'bus_voltage_v' else row['temperature_slope_c_min']
        bound = 0.15 if signal == 'bus_voltage_v' else 2.0
        slope = max(-bound, min(bound, slope))
        return current + slope * horizon_s / 60
    if method == 'physics_baseline':
        if signal == 'bus_voltage_v':
            charge = row['battery_soc_pct']/100
            charge += (row['solar_w']-row['load_w'])*horizon_s/(24*3600)
            charge = min(1.,max(0.,charge))
            # Hold the presently observed residual constant; not an oracle of the future.
            expected = predict_nominal_voltage(charge, row['load_w'])
            return expected-row['residual_v']
        # Heat equilibrium for constant currently measured load; true thermal dynamics
        # are not exposed to the estimator beyond the published nominal proxy.
        k, c, ambient = 0.075, 260., 18.
        from math import exp
        heat = .58*row['load_w'] + row['bus_current_a']**2 * .12
        decay = exp(-k*horizon_s/c)
        return ambient + (current-ambient)*decay + heat/k*(1-decay)
    raise ValueError('Unknown forecast baseline')


def _campaigns(seed_offset: int, count: int, horizon_s: int, *, extra_shift: bool = False):
    _require_horizon(horizon_s)
    for i in range(count):
        for scenario in SCENARIOS:
            mode = ('PAYLOAD' if i%3==0 else 'DOWNLINK' if i%3==1 else 'NOMINAL')
            if scenario == 'radio_burst': mode = 'DOWNLINK'
            severity = (0.75, 1.0, 1.25, 1.65)[i%4]
            if extra_shift: severity = (0.45, 1.45, 2.1)[i%3]
            onset = (180,480,720,990)[i%4] if not extra_shift else (300,630,900)[i%3]
            sim=simulate_health(scenario, seed=seed_offset+i, onset_s=onset,
                severity=severity, duration_s=2400, step_s=30,
                eclipse=bool(i%2), initial_soc=0.65+0.06*(i%4), mode=mode)
            yield f'{seed_offset+i}:{scenario}', sim


def future_pairs(telemetry: list[dict], horizon_s: int):
    """Training/evaluation only; future samples must NEVER enter input features."""
    _require_horizon(horizon_s)
    step = telemetry[1]['time_s']-telemetry[0]['time_s']
    if step <= 0 or horizon_s%step:
        raise ValueError('Telemetry sampling step must divide forecast horizon')
    jump = int(horizon_s/step)
    rows=features_for_forecasting(telemetry)
    for i in range(3, len(rows)-jump):
        yield rows[i], telemetry[i+jump]


@dataclass
class ForecastModels:
    horizon_s: int
    regressors: dict[str, Any]
    interval_half_width: dict[str,float]
    train_campaigns: int
    calibration_campaigns: int
    target_coverage: float = 0.90


def train_forecasters(*,train_seeds: int = 4, calibration_seeds: int = 4,
                      horizon_s: int = 300) -> ForecastModels:
    """No shared random seed/campaign between fit, calibration and evaluation.

    Interval width: split-conformal rank of each calibration campaign's MAX
    absolute error. Exchangeable calibration *campaigns* would give simultaneous
    coverage for a future campaign; our synthetic simulator does NOT establish
    validity under real-world shift. A finite width requires enough campaigns.
    """
    _require_horizon(horizon_s)
    if type(train_seeds) is not int or not 2<=train_seeds<=30:
        raise ValueError('train_seeds must be in 2..30')
    if type(calibration_seeds) is not int or not 3<=calibration_seeds<=30:
        raise ValueError('calibration_seeds must be in 3..30')
    try:
        import numpy as np
        from sklearn.ensemble import HistGradientBoostingRegressor
    except ImportError as exc:
        raise RuntimeError('Install numpy and scikit-learn in the satvv environment') from exc
    x=[]; y={s:[] for s in SIGNALS}
    n_train=0
    for _,sim in _campaigns(100,train_seeds,horizon_s):
        n_train+=1
        for row,future in future_pairs(sim['telemetry'],horizon_s):
            x.append(_feature_vector(row))
            for s in SIGNALS: y[s].append(float(future[s]))
    x=np.asarray(x,dtype=float)
    regressors={}
    for signal in SIGNALS:
        model=HistGradientBoostingRegressor(max_iter=75, max_leaf_nodes=13,
                    min_samples_leaf=28,learning_rate=.055,l2_regularization=.10,random_state=47)
        model.fit(x,np.asarray(y[signal],dtype=float))
        regressors[signal]=model
    errors={s:[] for s in SIGNALS};n_cal=0
    for _,sim in _campaigns(500,calibration_seeds,horizon_s):
        pairs=list(future_pairs(sim['telemetry'],horizon_s))
        if not pairs: continue
        xs=np.asarray([_feature_vector(row) for row,_ in pairs])
        n_cal+=1
        for s in SIGNALS:
            pred=regressors[s].predict(xs)
            errors[s].append(max(abs(float(p)-float(future[s])) for p,(_,future) in zip(pred,pairs)))
    widths={}
    for s in SIGNALS:
        vals=sorted(errors[s]);rank=ceil((len(vals)+1)*.90)
        if rank>len(vals): raise ValueError('Not enough independent calibration campaigns for 90% bound')
        widths[s]=float(vals[rank-1])
    return ForecastModels(horizon_s,regressors,widths,n_train,n_cal)


def forecast_trajectory(telemetry: list[dict], models: ForecastModels,
                        signal: str='bus_voltage_v') -> dict:
    """Causal forecasts at all timestamps; realized future is used by evaluator only."""
    if signal not in SIGNALS: raise ValueError('Unsupported signal')
    if not telemetry or len(telemetry)<4: raise ValueError('Not enough telemetry')
    h=models.horizon_s
    rows=features_for_forecasting(telemetry)
    import numpy as np
    x=np.asarray([_feature_vector(r) for r in rows],dtype=float)
    pred=models.regressors[signal].predict(x)
    width=models.interval_half_width[signal]
    forecasts=[]
    for i in range(3,len(rows)):
        r=rows[i]
        estimates={m:float(pred[i]) if m=='gradient_boosting' else
                     float(_baseline(r,signal,m,h)) for m in METHODS}
        low=estimates['gradient_boosting']-width
        high=estimates['gradient_boosting']+width
        # Predicted horizon violation is a forecast, never a verified failure.
        forecast_risk = (estimates['gradient_boosting']<LIMITS[signal] if signal=='bus_voltage_v' else
                         estimates['gradient_boosting']>LIMITS[signal])
        forecasts.append({'issue_time_s':r['time_s'],'target_time_s':r['time_s']+h,
            'observed':r[signal],'predictions':{m:round(v,5) for m,v in estimates.items()},
            'ml_lower':round(low,5),'ml_upper':round(high,5),
            'forecast_warning':bool(forecast_risk)})
    return {'meta':{'version':'0.6','signal':signal,'horizon_s':h,
        'forecast_warning_not_verification':True,
        'band':'campaign-max split-conformal on independent synthetic calibration campaigns; assumes exchangeability',
        'limits':'Forecast is conditional on patterns learned in a synthetic simulator, NOT flight-validated'},
        'limit':LIMITS[signal],'interval_half_width':width,'forecasts':forecasts}


def _violates(signal: str, value: float) -> bool:
    return value < LIMITS[signal] if signal=='bus_voltage_v' else value>LIMITS[signal]


def evaluate_trajectory(telemetry: list[dict], models: ForecastModels,signal:str) -> list[dict]:
    _require_horizon(models.horizon_s)
    pairs=list(future_pairs(telemetry,models.horizon_s))
    if not pairs:return []
    import numpy as np
    x=np.asarray([_feature_vector(r) for r,_ in pairs])
    ml=models.regressors[signal].predict(x)
    out=[];w=models.interval_half_width[signal]
    for (r,future),ml_pred in zip(pairs,ml):
        truth=float(future[signal])
        methods={m:float(ml_pred) if m=='gradient_boosting' else _baseline(r,signal,m,models.horizon_s)
            for m in METHODS}
        out.append({'issue_time_s':r['time_s'],'observed':float(r[signal]),
             'actual_future':truth,'predictions':methods,
             'interval_covered':abs(truth-float(ml_pred))<=w,
             'future_violation':_violates(signal,truth),
             'current_violation':_violates(signal,float(r[signal]))})
    return out
