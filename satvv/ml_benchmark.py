"""Leakage-aware *synthetic* monitoring benchmark for SAT-V&V v0.5.

Separate campaign seeds between training, healthy calibration, and evaluation.
Labels for supervised models come only from training scenario ground truth.
All reported performance is in-distribution-ish synthetic; not flight validation.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path
from .coupled import simulate_health
from .monitoring import engineer_features, feature_matrix, predict_methods, warning_summary

FAULTS = ('resistance_ramp','intermittent_resistance','sensor_drift','heater_fault','radio_burst')
METHODS = ('limit','trend','cusum','physics_residual','isolation_forest','gradient_boosting')


def _training_dataset(seeds: int):
    x=[]; y=[]; healthy=[]
    for seed in range(seeds):
        for name in ('healthy','normal_load_cycle') + FAULTS:
            sim=simulate_health(name,seed=100+seed,onset_s=360, duration_s=1800,
                                step_s=30,severity=.85,eclipse=(seed%2==0),
                                mode='DOWNLINK' if name=='radio_burst' else 'NOMINAL')
            rows=engineer_features(sim['telemetry'])
            x.extend(feature_matrix(rows))
            times=[r['time_s'] for r in rows]
            y.extend([int(any(e['start_s']<=t<e['end_s'] for e in sim['truth']['episodes'])) for t in times])
            if name in ('healthy','normal_load_cycle'):
                healthy.extend(feature_matrix(rows))
    return x,y,healthy


def train_models(train_seeds: int=5):
    try:
        import numpy as np
        from sklearn.ensemble import IsolationForest, HistGradientBoostingClassifier
    except ImportError as e:
        raise RuntimeError('v0.5 ML needs scikit-learn and numpy; conda install -c conda-forge scikit-learn numpy') from e
    x,y,healthy=_training_dataset(train_seeds)
    x=np.asarray(x,float);y=np.asarray(y,int);healthy=np.asarray(healthy,float)
    iforest=IsolationForest(n_estimators=80,contamination='auto',random_state=71,n_jobs=1)
    iforest.fit(healthy)
    gb=HistGradientBoostingClassifier(max_iter=80,max_leaf_nodes=12,learning_rate=.08,
                                       min_samples_leaf=18,random_state=71)
    gb.fit(x,y)
    # Calibration uses separate held-out HEALTHY campaigns, never evaluation faults.
    calibration=[]
    for seed in range(3):
        for name in ('healthy','normal_load_cycle'):
            sim=simulate_health(name,seed=500+seed,onset_s=420, duration_s=1800,step_s=30,
                                eclipse=(seed%2==0),mode='NOMINAL')
            calibration.extend(feature_matrix(engineer_features(sim['telemetry'])))
    cal=np.asarray(calibration,float)
    # Quantile and minimum score thresholds are applied without access to evaluation labels.
    if_threshold=float(np.quantile(-iforest.score_samples(cal), .995))
    gb_threshold=max(.5,float(np.quantile(gb.predict_proba(cal)[:,1],.995)))
    return {'isolation_forest':iforest,'gradient_boosting':gb,
            'iforest_threshold':if_threshold,'gb_threshold':gb_threshold,
            'training_campaigns':7*train_seeds,'calibration_campaigns':6}


def run_benchmark(*, eval_seeds: int = 4, train_seeds: int=5, out: str='results/v0.5') -> dict:
    if not 1<=eval_seeds<=20 or not 2<=train_seeds<=20:
        raise ValueError('eval_seeds and train_seeds must be 1..20 and 2..20')
    models=train_models(train_seeds)
    records=[]
    for seed in range(eval_seeds):
        for name in ('healthy','normal_load_cycle') + FAULTS:
            for eclipse in (False,True):
                sim=simulate_health(name,seed=800+seed,onset_s=420+(seed%3)*60,
                      duration_s=1800,step_s=30,severity=1.0+(seed%3)*.1,
                      eclipse=eclipse,mode='DOWNLINK' if name=='radio_burst' else 'NOMINAL')
                predictions=predict_methods(sim['telemetry'],models)
                for method, pred in predictions.items():
                    summary=warning_summary(pred['flags'],sim['telemetry'],sim['truth'])
                    records.append({'seed':800+seed,'scenario':name,'eclipse':eclipse,
                              'is_fault':sim['truth']['is_fault'],'method':method,
                              **summary})
    summary=[]
    for method in METHODS:
        group=[r for r in records if r['method']==method]
        pos=[r for r in group if r['is_fault']]
        neg=[r for r in group if not r['is_fault']]
        delays=[r['detection_delay_s'] for r in pos if r['detection_delay_s'] is not None]
        summary.append({'method':method,'fault_detection_fraction':round(sum(r['detected_during_fault'] for r in pos)/len(pos),3),
          'healthy_false_alert_episodes_per_hour':round(sum(r['warning_episodes'] for r in neg) / (len(neg)*.5),3),
          'median_detection_delay_s':sorted(delays)[len(delays)//2] if delays else None,
          'fault_campaigns':len(pos), 'healthy_campaigns':len(neg)})
    output={'meta':{'version':'0.5','evaluation_seeds':eval_seeds,'training_seeds':train_seeds,
           'train_campaigns':models['training_campaigns'],'calibration_campaigns':models['calibration_campaigns'],
           'evaluation_campaigns':eval_seeds*14,
           'warning_not_verification':True,
           'limits':'Synthetic uncalibrated coupled simulator. Training and evaluation share fault families, not episodes/seeds.'},
           'summary':summary,'records':records}
    dest=Path(out);dest.mkdir(parents=True,exist_ok=True)
    (dest/'monitor_benchmark.json').write_text(json.dumps(output,indent=2)+'\n')
    with (dest/'monitor_summary.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=summary[0].keys());writer.writeheader();writer.writerows(summary)
    with (dest/'monitor_campaigns.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=records[0].keys());writer.writeheader();writer.writerows(records)
    return output
