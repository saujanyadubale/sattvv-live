"""Repeatable v1.0.1 anti-starvation benchmark (runs fixed and updated policy).

Older v1.0 performance must be generated from its archived source separately;
this executable deliberately cannot misrepresent it as the new policy.
"""
from __future__ import annotations
from argparse import ArgumentParser
from csv import DictWriter
from pathlib import Path
from .challenge_v096 import run_challenge

def benchmark(seeds=(5,6,7,8,9,10,11,12),budget_min=90,difficulty='mixed',intensity='exploratory'):
    records=[]
    for seed in seeds:
        for policy in ('fixed','predictive_active'):
            r=run_challenge(difficulty,seed,budget_min,policy,intensity)
            records.append({'seed':seed,'difficulty':difficulty,'intensity':intensity,
                'budget_min':budget_min,'policy':policy,'detected':r['detected'],
                'detection_min':r['detection_s']/60 if r['detection_s'] is not None else '',
                'tests_run':r['tests_run'],'distinct_procedures':len(set(e['test_id'] for e in r['evidence'])),
                'coverage_guard_overrides':r['stages']['verification']['coverage_guard_overrides'],
                'audit_passed':r['audit']['passed']})
    return records

def main():
    p=ArgumentParser(description=__doc__)
    p.add_argument('--seeds',type=int,nargs='+',default=[5,6,7,8,9,10,11,12]);p.add_argument('--budget',type=int,default=90)
    p.add_argument('--difficulty',choices=['single','mixed','stress','control'],default='mixed')
    p.add_argument('--intensity',choices=['exploratory','high_impact'],default='exploratory')
    p.add_argument('--output',default='results/v1.0.1/reproduction.csv')
    a=p.parse_args()
    rows=benchmark(a.seeds,a.budget,a.difficulty,a.intensity)
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('w',newline='') as f:
        w=DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    for policy in ('fixed','predictive_active'):
        rec=[r for r in rows if r['policy']==policy]
        print(policy, f'{sum(x["detected"] for x in rec)}/{len(rec)} detected')
    print('Saved',out)
if __name__=='__main__':main()
