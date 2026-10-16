"""Paired seeded, synthetic v1.0.2 benchmark (not flight validation).

Identical generated initial conditions across strategies at each seed/budget. Each
strategy has its own simulator because tests change future state. All failures
are verified by actual executed requirement checks.
"""
from __future__ import annotations
import argparse,csv,json
from collections import defaultdict
from pathlib import Path
from .challenge_v096 import run_challenge

POLICIES=('fixed','predictive_greedy_v101','predictive_active','information_gain','learned_risk')

def benchmark(seeds=range(5,17),budgets=(35,60,90),intensities=('exploratory',),
              policies=POLICIES,difficulty='mixed'):
    rows=[]
    for intensity in intensities:
        for budget in budgets:
            for seed in seeds:
                for policy in policies:
                    r=run_challenge(difficulty,seed,budget,policy,intensity)
                    relevant=r.get('challenge_assessment',{}).get('fault_exposures',[])
                    row={'difficulty':difficulty,'intensity':intensity,'seed':seed,'budget_min':budget,
                        'policy':policy,'fault_count':r['oracle_after_run']['fault_count'],
                        'detected':int(r['detected']),'detection_min':r['detection_s']/60 if r['detected'] else '',
                        'time_censored_min':r['detection_s']/60 if r['detected'] else budget,
                        'tests_run':r['tests_run'],'distinct_tests':len({e['test_id'] for e in r['evidence']}),
                        'req_coverage':len(r['requirements_checked']),
                        'relevant_test_exposure':int(any(f['overlapping_checks'] for f in relevant)),
                        'oracle_diagnosis_top_match':int(bool(r['diagnosis_match'])),
                        'audit_pass':int(r['audit']['passed']),
                        'planning_steps':sum(int('planned_sequence' in e['decision']) for e in r['evidence'])}
                    rows.append(row)
                print(f'{difficulty}/{intensity} budget={budget} seed={seed}: completed {len(policies)}',flush=True)
    return rows

def summarize(rows):
    groups=defaultdict(list)
    for row in rows:groups[(row['difficulty'],row['intensity'],row['budget_min'],row['policy'])].append(row)
    ret=[]
    for (difficulty,intensity,budget,policy),group in sorted(groups.items()):
        n=len(group)
        ret.append({'difficulty':difficulty,'intensity':intensity,'budget':budget,'policy':policy,'n':n,
          'detected':sum(x['detected'] for x in group),
          'detection_pct':round(100*sum(x['detected'] for x in group)/n,1),
          'mean_time_censored':round(sum(x['time_censored_min'] for x in group)/n,2),
          'mean_distinct_tests':round(sum(x['distinct_tests'] for x in group)/n,2),
          'mean_req_coverage':round(sum(x['req_coverage'] for x in group)/n,2),
          'audits_passed':sum(x['audit_pass'] for x in group),
          'mean_relevant_exposure':round(sum(x['relevant_test_exposure'] for x in group)/n,2)})
    return ret

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seeds',nargs='+',type=int,default=list(range(5,17)))
    p.add_argument('--budgets',nargs='+',type=int,default=[35,60,90])
    p.add_argument('--intensities',nargs='+',default=['exploratory'])
    p.add_argument('--difficulty',default='mixed')
    p.add_argument('--policies',nargs='+',default=list(POLICIES))
    p.add_argument('--outdir',default='results/v1.0.2')
    a=p.parse_args()
    records=benchmark(a.seeds,a.budgets,a.intensities,a.policies,a.difficulty)
    dest=Path(a.outdir);dest.mkdir(parents=True,exist_ok=True)
    with (dest/'paired_campaigns.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    summ=summarize(records)
    (dest/'summary.json').write_text(json.dumps(summ,indent=2)+'\n')
    for x in summ:print(x)
    print('Saved',dest.resolve())
if __name__=='__main__':main()
