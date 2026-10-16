"""Cross-scenario paired v0.5 test-selection benchmark on coupled simulator."""
from __future__ import annotations
import csv
import json
from pathlib import Path
from .coupled import SCENARIOS
from .temporal_campaign import ALL_POLICIES
from .verification_v05 import run_verification_v05


def benchmark_verification(*,seeds:int=4,out:str='results/v0.5'):
    if type(seeds) is not int or not 1<=seeds<=20: raise ValueError('seeds must be 1..20')
    rows=[]
    for seed in range(seeds):
        for scenario in SCENARIOS:
            for onset in (180,600):
                for budget in (20,35):
                    for policy in ALL_POLICIES:
                        c=run_verification_v05(policy,scenario,budget_min=budget,
                            onset_s=onset,seed=1000+seed,eclipse=bool(seed%2))
                        rows.append({'policy':policy,'scenario':scenario,'seed':1000+seed,
                           'onset_s':onset,'budget_min':budget,'detected':c['detected'],
                           'spent_s':c['spent_s'],'tests_run':c['tests_run'],
                           'repeats':c['repeats']})
    summary=[]
    for onset in (180,600):
        for budget in (20,35):
            for policy in ALL_POLICIES:
                selected=[r for r in rows if r['onset_s']==onset and r['budget_min']==budget and r['policy']==policy]
                fault=[r for r in selected if r['scenario'] not in ('healthy','normal_load_cycle')]
                control=[r for r in selected if r['scenario'] in ('healthy','normal_load_cycle')]
                summary.append({'policy':policy,'onset_s':onset,'budget_min':budget,
                    'fault_detection_fraction':round(sum(r['detected'] for r in fault)/len(fault),3),
                    'healthy_false_failure_fraction':round(sum(r['detected'] for r in control)/len(control),3),
                    'n_fault_campaigns':len(fault),'n_healthy_campaigns':len(control)})
    output={'meta':{'version':'0.5','seeds':seeds,'total_campaigns':len(rows),
                    'warning':'Synthetic study, 5 fault families + 2 controls, not spacecraft-qualified'},
            'summary':summary,'rows':rows}
    dest=Path(out);dest.mkdir(parents=True,exist_ok=True)
    (dest/'verification_benchmark.json').write_text(json.dumps(output,indent=2)+'\n')
    for name,data in [('verification_summary.csv',summary),('verification_campaigns.csv',rows)]:
        with (dest/name).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=data[0].keys());writer.writeheader();writer.writerows(data)
    return output
