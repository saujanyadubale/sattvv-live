"""Paired random-fault challenge pilot: detection, diagnosis and false failures.

Challenge seeds are paired across strategies, and generated faults are not in
training labels for the offline learned ranker. They do share synthetic dynamics;
these results do not establish transfer to physical spacecraft.
"""
from __future__ import annotations
from statistics import mean
from .challenge_v096 import run_challenge,DIFFICULTIES
from .pipeline_v093 import METHODS

def benchmark(seeds=(77,78,79),budget_min=30):
    rows=[]
    for difficulty in DIFFICULTIES:
        for seed in seeds:
            for policy in METHODS:
                r=run_challenge(difficulty,seed,budget_min,policy)
                truth=r['oracle_after_run']
                rows.append({'difficulty':difficulty,'seed':seed,'policy':policy,
                             'fault_episodes':truth['fault_count'],'healthy':truth['healthy'],
                             'detected':r['detected'],'spent_min':r['spent_s']/60,
                             'diagnosis_match':r['diagnosis_match'],'audit_pass':r['audit']['passed']})
    summary=[]
    for difficulty in DIFFICULTIES:
        for policy in METHODS:
            subset=[r for r in rows if r['difficulty']==difficulty and r['policy']==policy]
            summary.append({'difficulty':difficulty,'policy':policy,'campaigns':len(subset),
                            'detection_rate':mean(r['detected'] for r in subset),
                            'diagnosis_partial_match_rate':mean(r['diagnosis_match'] for r in subset),
                            'average_spent_min':round(mean(r['spent_min'] for r in subset),2),
                            'audit_pass_rate':mean(r['audit_pass'] for r in subset)})
    return {'records':rows,'summary':summary,'limits':[
       'Synthetic model-dependent fault generator; not independent spacecraft physics',
       'Small seed counts are exploratory, not statistical superiority evidence',
       'Diagnostic match means top hypothesis agrees with at least one injected fault',
       'False failure on healthy controls is a verification outcome, not an ML anomaly false alert',
       'Strategies may change future spacecraft trajectories through test actions']}
