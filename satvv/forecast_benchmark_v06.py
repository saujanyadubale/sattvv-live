"""Campaign-held-out forecast benchmark. Evaluator may see futures; predictors may not."""
from __future__ import annotations
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, median
from .forecast_v06 import (METHODS, SIGNALS, _campaigns, _violates,
                            evaluate_trajectory, train_forecasters)


def benchmark_forecasting(*, train_seeds: int=4, calibration_seeds: int=4,
                           eval_seeds: int=3, horizon_s: int=300,
                           out: str='results/v0.6') -> dict:
    if type(eval_seeds) is not int or not 1<=eval_seeds<=20:
        raise ValueError('eval_seeds must be in 1..20')
    models=train_forecasters(train_seeds=train_seeds,
        calibration_seeds=calibration_seeds,horizon_s=horizon_s)
    records=[]
    for cid, sim in _campaigns(900,eval_seeds,horizon_s, extra_shift=True):
        scenario=sim['meta']['scenario']
        for signal in SIGNALS:
            data=evaluate_trajectory(sim['telemetry'],models,signal)
            for method in METHODS:
                err=[abs(r['predictions'][method]-r['actual_future']) for r in data]
                # A *future point* threshold prediction is not a confirmed fault.
                opportunities=[r for r in data if not r['current_violation']]
                positives=[r for r in opportunities if r['future_violation']]
                negatives=[r for r in opportunities if not r['future_violation']]
                flags=[_violates(signal,r['predictions'][method]) for r in opportunities]
                tp=sum(f and r['future_violation'] for f,r in zip(flags,opportunities))
                fp=sum(f and not r['future_violation'] for f,r in zip(flags,opportunities))
                fn=len(positives)-tp
                first_actual=next((p['time_s'] for p in sim['telemetry'] if _violates(signal,p[signal])),None)
                qualifying=[r['issue_time_s'] for r in opportunities
                            if first_actual is not None and r['issue_time_s']<first_actual
                            and r['future_violation'] and _violates(signal,r['predictions'][method])]
                lead_s=first_actual-min(qualifying) if qualifying else None
                records.append({'campaign':cid,'scenario':scenario,'signal':signal,'method':method,
                    'n_points':len(data),'mae':round(mean(err),6),
                    'point_interval_coverage':round(mean(r['interval_covered'] for r in data),4)
                        if method=='gradient_boosting' else None,
                    'whole_campaign_covered':all(r['interval_covered'] for r in data)
                        if method=='gradient_boosting' else None,
                    'actual_violation_observed':first_actual is not None,
                    'future_positive_points':len(positives),
                    'future_negative_points':len(negatives),
                    'true_positive_forecasts':tp,'false_positive_forecasts':fp,
                    'false_negative_forecasts':fn,
                    'first_warning_lead_s':lead_s})
    aggregate=[]
    for signal in SIGNALS:
        for method in METHODS:
            selected=[r for r in records if r['signal']==signal and r['method']==method]
            tp=sum(r['true_positive_forecasts'] for r in selected)
            fp=sum(r['false_positive_forecasts'] for r in selected)
            fn=sum(r['false_negative_forecasts'] for r in selected)
            full=mean(r['whole_campaign_covered'] for r in selected) if method=='gradient_boosting' else None
            point=mean(r['point_interval_coverage'] for r in selected) if method=='gradient_boosting' else None
            lead=[r['first_warning_lead_s'] for r in selected if r['first_warning_lead_s'] is not None]
            aggregate.append({'signal':signal,'method':method,'campaigns':len(selected),
                'macro_mae':round(mean(r['mae'] for r in selected),4),
                'forecast_precision':round(tp/(tp+fp),3) if tp+fp else None,
                'forecast_recall':round(tp/(tp+fn),3) if tp+fn else None,
                'false_forecast_points':fp,
                'true_future_violation_points':tp+fn,
                'interval_point_coverage':round(point,3) if point is not None else None,
                'simultaneous_campaign_coverage':round(full,3) if full is not None else None,
                'median_early_warning_s':median(lead) if lead else None})
    result={'meta':{'version':'0.6','train_campaigns':models.train_campaigns,
                   'calibration_campaigns':models.calibration_campaigns,
                   'evaluation_campaigns':eval_seeds*7,
                   'horizon_s':horizon_s,
                   'interval_target_campaign_coverage':.9,
                   'disjoint_seeds':'Fit seeds 100+, calibration 500+, evaluation 900+ with changed onset/severity',
                   'limitations':'No external spacecraft validation; all splits share handcrafted simulation families. Forecast warnings are not verification test failures.'},
            'interval_half_widths':models.interval_half_width,
            'summary':aggregate,'campaigns':records}
    folder=Path(out);folder.mkdir(parents=True,exist_ok=True)
    (folder/'forecast_benchmark.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    for filename,data in (('forecast_summary.csv',aggregate),('forecast_campaigns.csv',records)):
        with (folder/filename).open('w',newline='') as f:
            wr=csv.DictWriter(f,fieldnames=data[0].keys());wr.writeheader();wr.writerows(data)
    return result
