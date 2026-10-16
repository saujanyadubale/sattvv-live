"""v0.5 sixteen-test catalog and coupled-simulator verification campaign.

Distinct from monitoring: only executed requirement checks can produce FAIL.
All seven scheduling policies operate on the SAME 16-test coupled test catalog.
Policies are comparable under common simulation time budgets and scenario inputs.
"""
from __future__ import annotations
from dataclasses import asdict
from typing import Any
import random
from .core import TESTS, TestCase, Mode
from .coupled import CoupledSpacecraft, make_episodes, SCENARIOS, predict_nominal_voltage
from .dynamic_campaign import _execute_test, _navigate, _test_score, _focus_from_telemetry
from .temporal_campaign import ALL_POLICIES

EXTRA_REQUIREMENTS = {
    'REQ-ECL-V':'Bus >=6.70 V during scripted 5-min eclipse',
    'REQ-ECL-S':'Battery SOC remains >=10% through eclipse',
    'REQ-EPS-R':'Loaded bus voltage is within 0.26 V of healthy prediction',
    'REQ-EPS-REC':'Bus voltage recovers within 0.18 V of pre-load baseline',
    'REQ-THM-R':'Payload heating rate drops >=0.2 C/min when load is reduced',
    'REQ-THM-DR':'Thermal sensor disagreement stays <=3.0 C in a timed test',
}

ADDITIONAL_TESTS = (
    TestCase('T13','Eclipse EPS endurance','EPS',Mode.NOMINAL,5,
             ('REQ-ECL-V','REQ-ECL-S'),criticality=1.9),
    TestCase('T14','Battery load-step and recovery','EPS',Mode.NOMINAL,5,
             ('REQ-EPS-R','REQ-EPS-REC'),criticality=2.0),
    TestCase('T15','Payload thermal recovery','THERMAL',Mode.PAYLOAD,7,
             ('REQ-THM-T','REQ-THM-R'),criticality=1.6),
    TestCase('T16','Time-series sensor drift consistency','THERMAL',Mode.NOMINAL,4,
             ('REQ-THM-DR',),criticality=1.7),
)
ALL_TESTS = TESTS + ADDITIONAL_TESTS
CATALOG = {x.id:x for x in ALL_TESTS}

def _offline_model_fixed_schedule() -> list[TestCase]:
    """Commit to catalog ordering BEFORE seeing any spacecraft measurements."""
    from .dynamic_campaign import _path
    pool=list(ALL_TESTS)
    planned_coverage=set()
    planned_transitions=set()
    ordered=[]
    while pool:
        next_test=max(pool,key=lambda x:(_test_score(x,planned_coverage,planned_transitions,{}),-int(x.id[1:])))
        pool.remove(next_test)
        ordered.append(next_test)
        planned_coverage.update(next_test.checks)
        path=[Mode.BOOT]+(_path(Mode.BOOT,next_test.target) or [])
        planned_transitions.update(f'{a.value}->{b.value}' for a,b in zip(path,path[1:]))
    return ordered



def _extended_test(sim: CoupledSpacecraft,t:TestCase) -> dict[str,Any]:
    assert t.id in ('T13','T14','T15','T16')
    start=sim.state.time_s
    before=len(sim.events)
    reached, actions=_navigate(sim,t.target)
    observations=[]
    def sample_for(seconds, *, extra_load=0, sunlit_override=None, target=None):
        sim.extra_load_w=extra_load
        sim.sunlit_override=sunlit_override
        if target is not None:
            _, moves=_navigate(sim,target)
            actions.extend(moves)
        for _ in range(int(seconds//10)):
            observations.append(sim.telemetry())
            sim.step(10)
        observations.append(sim.telemetry())
    try:
        if t.id=='T13': sample_for(300,sunlit_override=False)
        elif t.id=='T14':
            sample_for(60)
            initial=observations[-1]['bus_voltage_v']
            sample_for(180,extra_load=3.0)
            sample_for(60)
        elif t.id=='T15':
            sample_for(240)
            hot=observations[-1]['temperature_c']
            sample_for(180,target=Mode.NOMINAL)
        else: sample_for(240)
    finally:
        sim.extra_load_w=0
        sim.sunlit_override=None
    details={}
    if not reached:
        checks={req:None for req in t.checks}
    elif t.id=='T13':
        vmin=min(x['bus_voltage_v'] for x in observations)
        socmin=min(x['battery_soc_pct'] for x in observations)
        checks={'REQ-ECL-V':vmin>=6.7,'REQ-ECL-S':socmin>=10.}
        details={'REQ-ECL-V':{'metric':'Minimum bus voltage during eclipse','measured':vmin,'operator':'>=','threshold':6.7,'unit':'V'},
                 'REQ-ECL-S':{'metric':'Minimum battery charge during eclipse','measured':socmin,'operator':'>=','threshold':10.,'unit':'%'}}
    elif t.id=='T14':
        high=[x for x in observations if x['load_w']>=6]
        max_residual=(max(abs(predict_nominal_voltage(x['battery_soc_pct']/100,x['load_w'])-x['bus_voltage_v'])
                          for x in high) if high else None)
        recovery_error=abs(observations[-1]['bus_voltage_v']-initial)
        checks={'REQ-EPS-R':max_residual<=.26 if max_residual is not None else None,
                'REQ-EPS-REC':recovery_error<=.18}
        details={'REQ-EPS-R':{'metric':'Maximum absolute voltage departure from healthy load-response model',
                  'measured':max_residual,'operator':'<=','threshold':.26,'unit':'V',
                  'context':'Compared during modeled high-load samples (load >= 6 W)'},
                 'REQ-EPS-REC':{'metric':'Absolute difference between recovered and pre-step bus voltage',
                  'measured':recovery_error,'operator':'<=','threshold':.18,'unit':'V',
                  'context':'Measured after the recovery interval; does not alone establish the root cause'}}
    elif t.id=='T15':
        peak=max(x['temperature_c'] for x in observations)
        recovery_metric=((hot-observations[0]['temperature_c'])/4.0 - (observations[-1]['temperature_c']-hot)/3.0)
        checks={'REQ-THM-T':peak<=70,'REQ-THM-R':recovery_metric>=.2}
        details={'REQ-THM-T':{'metric':'Maximum modeled payload temperature','measured':peak,'operator':'<=','threshold':70.,'unit':'°C'},
                 'REQ-THM-R':{'metric':'Heating-rate minus recovery-rate contrast','measured':recovery_metric,'operator':'>=','threshold':.2,'unit':'°C/min'}}
    else:
        disagreement=max(abs(x['temperature_c']-x['redundant_temperature_c']) for x in observations)
        checks={'REQ-THM-DR':disagreement<=3}
        details={'REQ-THM-DR':{'metric':'Maximum temperature-sensor disagreement','measured':disagreement,'operator':'<=','threshold':3.,'unit':'°C'}}
    if sim.state.time_s-start != t.cost*60: raise AssertionError('Duration mismatch')
    failures=[k for k,v in checks.items() if v is False]
    status='FAIL' if failures else ('PASS' if all(x is True for x in checks.values()) else 'INCONCLUSIVE')
    return {'kind':'test','test_id':t.id,'test_name':t.name,'subsystem':t.subsystem,
            'start_s':int(start),'end_s':int(sim.state.time_s),'cost_min':t.cost,
            'status':status,'detected':bool(failures),'checks':checks,'check_details':details,
            'actions':actions,'transitions':[f"{x['from']}->{x['to']}" for x in actions if x['accepted']],
            'telemetry_start':observations[0], 'telemetry_end':observations[-1],
            'window_extrema':{'minimum_bus_voltage_v':min(x['bus_voltage_v'] for x in observations),
              'maximum_temperature_c':max(x['temperature_c'] for x in observations),
              'maximum_bus_current_a':max(x['bus_current_a'] for x in observations)},
            'observed_events':sim.events[before:],
            'warnings':_focus_from_telemetry(observations[-1]),
            'samples':len(observations)}


def run_verification_v05(policy:str='temporal_adaptive', scenario:str='resistance_ramp',*,
                         budget_min:int=30,seed:int=7,severity:float=1.,
                         onset_s:int=480,eclipse:bool=False,initial_soc:float=.8) -> dict[str,Any]:
    if policy not in ALL_POLICIES: raise ValueError('Unknown policy')
    if not type(budget_min) is int or not 5<=budget_min<=90: raise ValueError('Budget must be 5..90 minutes')
    if type(seed) is not int or not 0<=seed<=1000000: raise ValueError('Invalid seed')
    if type(eclipse) is not bool or not 0<=initial_soc<=1: raise ValueError('Invalid environment')
    sim=CoupledSpacecraft(make_episodes(scenario,severity,onset_s), seed, initial_soc,eclipse)
    remaining=list(ALL_TESTS)
    if policy=='random': random.Random(seed).shuffle(remaining)
    if policy=='model_fixed': remaining=_offline_model_fixed_schedule()
    checked=set();visited=set(); ages={};runs={};evidence=[];spent=0
    warnings={}; detection_s=None
    patrol=('T01','T03','T05','T14','T11','T16','T13','T07','T15','T10','T04','T12','T08','T09','T02','T06')
    patrol_i=0
    while budget_min-spent>=1:
        eligible=[x for x in ALL_TESTS if x.cost<=budget_min-spent]
        if not eligible: break
        if policy in ('fixed','random','model_fixed','adaptive'):
            pool=[x for x in remaining if x.cost<=budget_min-spent]
            if not pool: break
            if policy in ('fixed','random'):
                t=pool[0]
            elif policy=='model_fixed':
                t=pool[0]  # Advance the precomputed schedule; no telemetry feedback.
            else:
                t=max(pool,key=lambda x:(_test_score(x,checked,visited,warnings),-int(x.id[1:])))
            remaining.remove(t)
        elif policy=='scheduled_retest':
            choices=[CATALOG[k] for k in patrol[patrol_i:]+patrol[:patrol_i] if CATALOG[k].cost<=budget_min-spent]
            if not choices: break
            t=choices[0];patrol_i=(patrol.index(t.id)+1)%len(patrol)
        else:
            def score(test):
                nov=len(set(test.checks)-checked)
                age=sum(min(3.,(sim.state.time_s-ages[r])/360) for r in test.checks if r in ages)
                risk=warnings.get(test.subsystem,0) if policy=='temporal_adaptive' else 0
                repeat=runs.get(test.id,0)
                return ((3.3*nov+2.1*test.criticality+2.6*age+1.35*risk-1.15*repeat)
                        /test.cost**.68)
            t=max(eligible,key=lambda x:(score(x),-int(x.id[1:])))
            if score(t)<3 and budget_min-spent>=1:
                start=sim.state.time_s
                for _ in range(6):sim.step(10)
                end=sim.telemetry()
                warnings=_focus_from_telemetry(end)
                spent+=1
                evidence.append({'kind':'wait','start_s':start,'end_s':sim.state.time_s,'telemetry_end':end,
                                 'status':'OBSERVED','detected':False})
                continue
        rec = _extended_test(sim,t) if t in ADDITIONAL_TESTS else _execute_test(sim,t,sunlit=True)
        rec['kind']='test';rec['repeat_index']=runs.get(t.id,0)
        evidence.append(rec)
        runs[t.id]=runs.get(t.id,0)+1
        spent+=t.cost
        for r,v in rec['checks'].items():
            if v is not None:checked.add(r);ages[r]=sim.state.time_s
        visited.update(rec['transitions']);warnings=_focus_from_telemetry(rec['telemetry_end'])
        if rec['detected']:
            detection_s=int(sim.state.time_s);break
    if spent*60 != sim.state.time_s: raise AssertionError('Budget clock mismatch')
    return {'meta':{'version':'0.6','policy':policy,'scenario':scenario,'budget_min':budget_min,
                     'seed':seed,'severity':severity,'onset_s':onset_s,'eclipse':eclipse,
                     'limitations':'Synthetic physics; first failed requirement check, not root-cause diagnosis.'},
            'detected':detection_s is not None,'detection_s':detection_s,
            'spent_s':spent*60,'requirements_checked':sorted(checked),
            'tests_run':len([r for r in evidence if r['kind']=='test']),
            'repeats':sum(r.get('repeat_index',0)>0 for r in evidence),
            'evidence':evidence, 'terminal_state':sim.telemetry()}
