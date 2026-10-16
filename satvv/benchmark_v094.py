"""v0.9.4 paired diagnostic study. Synthetic campaigns, not flight validation.

Fault family is the natural unit of generalization; seeds vary within family.
Model probabilities remain uncalibrated. Root-cause accuracy is only assessed
on known single-fault scenarios, never on held-out compound fault labels.
"""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
import csv,json
from .pipeline_v093 import run_pipeline,METHODS

CASES=(
 ('healthy',True,False),('normal_load_cycle',True,False),
 ('resistance_ramp',False,True),('intermittent_resistance',False,True),
 ('sensor_drift',False,True),('heater_fault',False,True),
 ('dual_resistance_sensor',False,False),('wheel_plus_battery',False,False),
)

def benchmark(seeds=(901,902,903),budgets=(20,26),onset_s=300,severity=1.35):
    rows=[]
    for budget in budgets:
        for scenario,healthy,single in CASES:
            for seed in seeds:
                for policy in METHODS:
                    result=run_pipeline(scenario,policy=policy,budget_min=budget,
                                        onset_s=onset_s,seed=seed,severity=severity)
                    if not result['audit']['passed']:
                        raise AssertionError(f'Audit failed: {scenario}/{policy}/{seed}')
                    rows.append({'budget_min':budget,'scenario':scenario,
                        'population':'healthy' if healthy else 'faulty',
                        'single_fault':single,'seed':seed,'policy':policy,
                        'detected':result['detected'],
                        'detection_delay_s':None if result['detection_s'] is None else result['detection_s']-onset_s,
                        'spent_s':result['spent_s'],'tests_run':result['tests_run'],
                        'first_test':result['evidence'][0]['test_id'] if result['evidence'] else '',
                        'failure_test':next((e['test_id'] for e in result['evidence'] if e['status']=='FAIL'),''),
                        'estimated_cause':result['estimated_cause'],
                        'top_hypothesis_correct':result['estimated_cause']==scenario if single else None,
                        'audit_passed':result['audit']['passed']})
    grouped=defaultdict(list)
    for row in rows:grouped[(row['budget_min'],row['policy'],row['population'])].append(row)
    summary=[]
    for (budget,policy,pop),group in sorted(grouped.items()):
        k=sum(x['detected'] for x in group)
        latencies=[x['detection_delay_s'] for x in group if x['detection_delay_s'] is not None]
        solo=[x['top_hypothesis_correct'] for x in group if x['top_hypothesis_correct'] is not None]
        summary.append({'budget_min':budget,'policy':policy,'population':pop,
            'positives':k,'campaigns':len(group),'fraction':k/len(group),
            'meaning':'False requirement-failure frequency' if pop=='healthy' else 'Requirement-failure detection frequency',
            'mean_detection_delay_min_when_detected':round(sum(latencies)/len(latencies)/60,3) if latencies else None,
            'single_fault_top1_rate':round(sum(solo)/len(solo),4) if solo else None})
    return {'meta':{'version':'0.9.4','budgets':list(budgets),'seeds':list(seeds),
           'onset_s':onset_s,'severity_nonstress':severity,'families':[c[0] for c in CASES],
           'note':'Paired controlled synthetic benchmark. Held-out stress mixes are not independent physical validation. Single-fault diagnosis percentages are uncalibrated.'},
           'campaigns':rows,'summary':summary}

def save(report,path='results/v0.9.4'):
    p=Path(path);p.mkdir(parents=True,exist_ok=True)
    (p/'benchmark.json').write_text(json.dumps(report,indent=2)+'\n')
    for file,items in (('campaigns.csv',report['campaigns']),('summary.csv',report['summary'])):
        with (p/file).open('w',newline='') as f:
            wr=csv.DictWriter(f,fieldnames=list(items[0]));wr.writeheader();wr.writerows(items)
    return p
