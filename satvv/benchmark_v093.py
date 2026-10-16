"""Paired v0.9.3 pilot benchmark; scenario families, not individual time samples, are units."""
from __future__ import annotations
import csv,json
from collections import defaultdict
from pathlib import Path
from .pipeline_v093 import run_pipeline,METHODS
from .stress_v09 import STRESS_CASES

def benchmark(seeds=(801,802),budgets=(20,25,35),horizon_s=300):
    rows=[]
    for budget in budgets:
        for case in STRESS_CASES:
            for seed in seeds:
                for policy in METHODS:
                    out=run_pipeline(case.name,policy=policy,seed=seed,budget_min=budget,
                                     onset_s=600,horizon_s=horizon_s)
                    if not out['audit']['passed']:
                        raise AssertionError(f'Audit error: {case.name} {policy} {seed}')
                    rows.append({'budget_min':budget,'case':case.name,'healthy':case.healthy,
                        'seed':seed,'policy':policy,'detected':out['detected'],
                        'detection_s':out['detection_s'],'spent_s':out['spent_s'],
                        'tests_run':out['tests_run'],'forecast_risk_seen':out['forecast_risk_seen'],
                        'cause':out['estimated_cause']})
    groups=defaultdict(list)
    for r in rows:groups[(r['budget_min'],r['policy'],r['healthy'])].append(r)
    summary=[]
    for (budget,policy,healthy),values in sorted(groups.items()):
        k=sum(r['detected'] for r in values)
        summary.append({'budget_min':budget,'policy':policy,'population':'healthy' if healthy else 'faulty',
                        'positive':k,'campaigns':len(values),'rate':k/len(values),
                        'meaning':'healthy false-failure rate' if healthy else 'faulty-case verification detection'})
    return {'meta':{'version':'0.9.3','seeds':list(seeds),'budgets':list(budgets),'horizon_s':horizon_s,
            'caution':'small synthetic held-out compound-fault pilot; not flight validation or trained on independent hardware'},
            'rows':rows,'summary':summary}

def save(report,out='results/v0.9.3'):
    root=Path(out);root.mkdir(parents=True,exist_ok=True)
    (root/'benchmark.json').write_text(json.dumps(report,indent=2))
    with (root/'campaigns.csv').open('w',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=report['rows'][0]);wr.writeheader();wr.writerows(report['rows'])
    with (root/'summary.csv').open('w',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=report['summary'][0]);wr.writeheader();wr.writerows(report['summary'])
    return root
