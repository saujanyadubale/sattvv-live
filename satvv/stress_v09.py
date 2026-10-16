"""Independent, OOD stress scenarios and stratified paired uncertainty summaries.

Compound fault combinations are held out of learned-model and likelihood fits.
"""
from __future__ import annotations
from dataclasses import dataclass
from random import Random
from math import sqrt
from .coupled import Episode
from .adcs_v08 import SpacecraftWithADCS
from .integrated_v08 import run_integrated

@dataclass(frozen=True)
class StressCase:
    name:str
    base:str
    episode:str|None
    adcs:str|None
    healthy:bool

STRESS_CASES=(
  StressCase('healthy_eclipse_and_load','normal_load_cycle',None,None,True),
  StressCase('dual_resistance_sensor','intermittent_resistance','sensor_drift',None,False),
  StressCase('heater_plus_radio','heater_fault','radio_burst',None,False),
  StressCase('wheel_plus_battery','adcs_wheel_weak','battery_resistance','adcs_wheel_weak',False),
  StressCase('slow_resistance_unseen','healthy','battery_resistance',None,False),
  StressCase('radio_plus_gyro_bias','radio_burst',None,'adcs_gyro_bias',False),
  StressCase('healthy_eclipse','healthy',None,None,True),
)

def make_stress_sim(case:StressCase, seed:int, onset_s=600):
    rng=Random(seed*7001+len(case.name))
    severity=round(rng.uniform(.65,1.35),4)
    eclipse=case.healthy or (rng.random()<.4)
    soc=rng.uniform(.67,.90)
    sim=SpacecraftWithADCS(case.base,severity,onset_s,seed=seed,initial_soc=soc,eclipse=eclipse)
    if case.episode:
        # Novel mixture/ramp shapes deliberately excluded from training scenarios.
        mechanisms={'battery_resistance':(onset_s+90,1400),
                    'sensor_drift':(onset_s+160,650),
                    'radio_burst':(onset_s+110,0)}
        start,ramp=mechanisms[case.episode]
        sim._episodes=sim._episodes+(Episode(case.episode,start,start+1700,severity,ramp),)
    if case.adcs:
        sim.adcs_scenario=case.adcs
        sim.adcs_onset_s=onset_s+80
    return sim

def evaluate_stress(seeds=(801,802,803,804),budget_min=45,onset_s=600):
    rows=[]
    for case in STRESS_CASES:
        for seed in seeds:
            for policy in ('fixed','temporal_adaptive','information_gain','learned_risk'):
                sim=make_stress_sim(case,seed,onset_s)
                result=run_integrated(case.base,policy=policy,budget_min=budget_min,seed=seed,
                                      onset_s=onset_s,_sim=sim)
                rows.append({'case':case.name,'healthy':case.healthy,'seed':seed,'policy':policy,
                             'detected':result['detected'],'spent_s':result['spent_s'],
                             'detection_s':result['detection_s'],
                             'cause':result.get('estimated_cause')})
    return rows

def clustered_summary(rows,bootstraps=500,seed=149):
    """Equal weight for each scenario family; cluster bootstrap on families."""
    rnd=Random(seed)
    policies=sorted({r['policy'] for r in rows})
    families=sorted({r['case'] for r in rows})
    out=[]
    for p in policies:
        present=[r for r in rows if r['policy']==p]
        subset={f:[r for r in present if r['case']==f] for f in families}
        family_scores={f:sum(r['detected'] for r in x)/len(x) for f,x in subset.items()}
        fault=[f for f in families if not subset[f][0]['healthy']]
        healthy=[f for f in families if subset[f][0]['healthy']]
        for label,kind in (('fault_detection',fault),('healthy_false_fail',healthy)):
            if not kind:continue
            point=sum(family_scores[k] for k in kind)/len(kind)
            sampled=[]
            for _ in range(bootstraps):
                draw=[rnd.choice(kind) for _ in kind]
                sampled.append(sum(family_scores[x] for x in draw)/len(draw))
            sampled.sort()
            out.append({'policy':p,'metric':label,'rate':point,
                        'ci95_low':sampled[int(.025*(bootstraps-1))],
                        'ci95_high':sampled[int(.975*(bootstraps-1))],
                        'families':len(kind),'campaigns':sum(len(subset[k]) for k in kind),
                        'uncertainty':'Exploratory 95% cluster-bootstrap CI over a small number of synthetic families'})
    return out
