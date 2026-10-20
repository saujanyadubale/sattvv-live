"""Deterministic, hidden-oracle synthetic fault challenges for SAT-V&V.

Uses distinct seeds and base+injected episode mechanisms. Not a claim of
realistic spaceflight failure occurrence probabilities. A run's truth is revealed
only in the external *evaluator response*, never to policy/diagnostic features.
"""
from __future__ import annotations
from dataclasses import dataclass
from random import Random
from .coupled import Episode
from .adcs_v08 import SpacecraftWithADCS

DIFFICULTIES=('control','single','mixed','stress')
INTENSITIES=('exploratory','high_impact')
FAULTS=('battery_resistance','sensor_drift','heater_fault','radio_burst','adcs_gyro_bias','adcs_wheel_weak','adcs_star_dropout')

@dataclass(frozen=True)
class Challenge:
    difficulty:str
    seed:int
    budget_min:int
    initial_soc:float
    eclipse:bool
    episodes:tuple[Episode,...]
    adcs_fault:str|None
    adcs_onset_s:int|None
    base:str='healthy'
    intensity:str='exploratory'

    def oracle(self):
        faults=[{'mechanism':e.mechanism,'onset_s':int(e.start_s),'end_s':int(e.end_s),
                 'severity':round(e.severity,3),'ramp_s':int(e.ramp_s)} for e in self.episodes if e.mechanism!='extra_load']
        if self.adcs_fault:faults.append({'mechanism':self.adcs_fault,'onset_s':self.adcs_onset_s,
                                          'end_s':self.budget_min*60,'severity':'synthetic constant'})
        return {'faults':faults,'fault_count':len(faults),'healthy':not bool(faults),
                'generator':'seeded, model-dependent stress generator; held-out combinations, not independent flight physics'}


def generate(difficulty='mixed',seed=7,budget_min=35,intensity='exploratory'):
    if difficulty not in DIFFICULTIES:raise ValueError('Unknown challenge difficulty')
    if intensity not in INTENSITIES:raise ValueError('Unknown intensity profile')
    if type(seed) is not int or not 0<=seed<=1000000:raise ValueError('Invalid challenge seed')
    if type(budget_min) is not int or not 15<=budget_min<=90:raise ValueError('Challenge budget must be 15–90 min')
    rng=Random(9620003+seed*8111+DIFFICULTIES.index(difficulty)*1061)
    n={'control':0,'single':1,'mixed':rng.choice((1,2)) if intensity=='exploratory' else 2,'stress':rng.choice((2,3)) if intensity=='exploratory' else 3}[difficulty]
    # Duplicate mechanism never sampled in the same multi-fault event.
    types=rng.sample(FAULTS,n)
    if sum(f.startswith('adcs_') for f in types)>1:
        adcs=[f for f in types if f.startswith('adcs_')]
        remaining=[f for f in FAULTS if f not in types and not f.startswith('adcs_')]
        types=[f for f in types if f==adcs[0] or not f.startswith('adcs_')]
        types+=rng.sample(remaining,n-len(types))
    start_max=max(90,(budget_min-9)*60)
    episodes=[];adcs_fault=None;adcs_time=None
    for kind in types:
        start=(rng.randrange(6,max(7,start_max//10))*10)
        duration=rng.randrange(25,110)*10
        severity=round(rng.uniform(.45,1.30 if difficulty=='single' else 1.75),3)
        ramp=round(rng.uniform(120,650)/10)*10 if kind in ('battery_resistance','sensor_drift') and rng.random()<.7 else 0
        if intensity=='high_impact':
            # Earlier sustained severe fault(s); no guarantee of detection.
            start=min(start,rng.randrange(3,max(4,budget_min*3))*10)
            duration=max(duration,budget_min*60-start+120)
            severity=round(rng.uniform(1.45,2.35),3)
            if kind in ('sensor_drift','battery_resistance'):ramp=0
        if kind.startswith('adcs_'):
            adcs_fault,adcs_time=kind,start
        else:
            episodes.append(Episode(kind,start,start+duration,severity,ramp))
            # Recurrence for stress case, using same mechanism but non-overlapping periods.
            if difficulty=='stress' and rng.random()<.45:
                next_start=start+duration+rng.randrange(4,14)*10
                episodes.append(Episode(kind,next_start,next_start+rng.randrange(20,70)*10,severity,0))
    if difficulty in ('control','stress'):
        start=rng.randrange(3,11)*60
        episodes.append(Episode('extra_load',start,start+180,round(rng.uniform(.15,.9),3)))
    return Challenge(difficulty,seed,budget_min,round(rng.uniform(.5,1),3),rng.random()<.40,
                     tuple(sorted(episodes,key=lambda e:e.start_s)),adcs_fault,adcs_time,intensity=intensity)

def make_sim(spec:Challenge):
    sim=SpacecraftWithADCS('healthy',seed=spec.seed,initial_soc=spec.initial_soc,eclipse=spec.eclipse)
    sim._episodes=spec.episodes
    if spec.adcs_fault:
        sim.adcs_scenario=spec.adcs_fault
        sim.adcs_onset_s=spec.adcs_onset_s
        sim.adcs_severity=1.0
    return sim

# Which diagnostic checks could theoretically examine each injected mechanism?
# Mapping is used ONLY by post-run evaluation, never by decision policies.
RELEVANT_TESTS={
 'battery_resistance': ('T03','T07','T13','T14'),
 'sensor_drift': ('T11','T16'),
 'heater_fault': ('T06','T15'),
 'radio_burst': ('T05','T08'),
 'adcs_gyro_bias': ('T19',),
 'adcs_wheel_weak': ('T17','T18','T20'),
 'adcs_star_dropout': ('T19',),
}

def assess_exposure(result, oracle):
    """Post-hoc exposure explanation; does not assert that a fault is detectable.

    An overlap indicates a test was performed while the fault episode was
    active, NOT that a requirement violation should necessarily occur.
    """
    assessments=[]
    for f in oracle['faults']:
        candidates=RELEVANT_TESTS.get(f['mechanism'],())
        overlapping=[]; performed=[]
        for e in result.get('evidence',[]):
            if e['test_id'] not in candidates:continue
            performed.append(e['test_id'])
            if e['start_s']<f['end_s'] and e['end_s']>f['onset_s']:
                overlapping.append({'test_id':e['test_id'],'start_s':e['start_s'],
                    'end_s':e['end_s'],'result':e['status'],
                    'check_details':e.get('check_details',{})})
        assessments.append({'fault':f['mechanism'],'onset_s':f['onset_s'],
            'end_s':f['end_s'],'duration_s':f['end_s']-f['onset_s'],
            'severity':f['severity'],'relevant_tests':list(candidates),
            'relevant_tests_performed':performed,'overlapping_checks':overlapping,
            'explanation':('Relevant test(s) overlapped this fault, but a passing check can still occur when the disturbance is too small or too brief.' if overlapping
                           else 'No relevant diagnostic procedure overlapped this fault episode. This does not prove that it was undetectable.')})
    return {'fault_exposures':assessments,
        'interpretation':('Healthy control: no fault episodes were injected.' if oracle['healthy'] else
         'A missed detection requires exposure analysis. Random faults are not guaranteed to violate any requirement.'),
        'not_a_detectability_proof':True}

def run_challenge(difficulty='mixed',seed=7,budget_min=35,policy='predictive_active',intensity='exploratory', _weak_monitor_priority=True,_continue_after_fail=False,
                  _learning_model=None,_learning_version=None):
    from .pipeline_v093 import run_pipeline
    spec=generate(difficulty,seed,budget_min,intensity)
    # Use the same deterministic scenario for all policies, but independent sim copies.
    result=run_pipeline('healthy',policy=policy,budget_min=budget_min,seed=seed,
                        onset_s=0,initial_soc=spec.initial_soc,eclipse=spec.eclipse,
                        _sim=make_sim(spec),_weak_monitor_priority=_weak_monitor_priority,
                        _continue_after_fail=_continue_after_fail,
                        _learning_model=_learning_model,_learning_version=_learning_version)
    result['meta'].update({'version':'0.9.8','scenario':'random_challenge','challenge_level':difficulty,
                           'challenge_seed':seed,'challenge_intensity':intensity,'generated_environment':{'soc':spec.initial_soc,'eclipse':spec.eclipse}})
    result['oracle_after_run']=spec.oracle()
    result['challenge_assessment']=assess_exposure(result,result['oracle_after_run'])
    result['generator_note']='Ground truth revealed only after completed experiment, never to the decision algorithm.'
    # Reproducible truth-based metrics, separate from the posterior diagnosis.
    truth=[f['mechanism'] for f in spec.oracle()['faults']]
    convert={'battery_resistance':('resistance_ramp','intermittent_resistance'),
             'sensor_drift':('sensor_drift',),'heater_fault':('heater_fault',),
             'radio_burst':('radio_burst',),'adcs_gyro_bias':('adcs_gyro_bias',),
             'adcs_wheel_weak':('adcs_wheel_weak',),'adcs_star_dropout':('adcs_star_dropout',)}
    result['diagnosis_match']=(result['estimated_cause']=='healthy') if not truth else (result['estimated_cause'] in {h for f in truth for h in convert.get(f,())})
    result['diagnosis_match_note']='Top single-cause hypothesis matches the healthy condition or at least one injected fault; not complete multi-fault diagnosis.'
    return result
