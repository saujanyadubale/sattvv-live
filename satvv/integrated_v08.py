"""v0.8 single 20-test campaign with ADCS/EPS/thermal coupling.

The information-gain hypothesis library is estimated on separate training seeds.
Outputs quantify synthetic requirement failures, not certifiable flight diagnosis.
"""
from __future__ import annotations
from functools import lru_cache
from .active_v07 import information_gain, update_belief, calibrated_likelihoods
from .adcs_v08 import SpacecraftWithADCS, ADCS_TESTS, ADCS_FAULTS, ALL_SCENARIOS, execute_adcs_test
from .verification_v05 import ALL_TESTS, ADDITIONAL_TESTS, _extended_test
from .dynamic_campaign import _execute_test,_focus_from_telemetry

CATALOG=ALL_TESTS+ADCS_TESTS
CAUSES=('healthy','resistance_ramp','intermittent_resistance','sensor_drift','heater_fault','radio_burst')+ADCS_FAULTS

def execute(sim,t):
    if t in ADCS_TESTS:return execute_adcs_test(sim,t)
    if t in ADDITIONAL_TESTS:return _extended_test(sim,t)
    return _execute_test(sim,t,sunlit=True)

@lru_cache(maxsize=1)
def fit_response_table():
    base=calibrated_likelihoods(); model={}
    for h in CAUSES:
        for t in CATALOG:
            if h in CAUSES[:6] and t.id not in {x.id for x in ADCS_TESTS}:
                model[h,t.id]=base[h,t.id]
                continue
            results=[]
            for seed in (451,452,453):
                sim=SpacecraftWithADCS(h,onset_s=0,seed=seed)
                for _ in range(30):sim.step(10)
                rec=execute(sim,t)
                if rec['status']!='INCONCLUSIVE':results.append(int(rec['detected']))
            model[h,t.id]=(sum(results)+1)/(len(results)+2) if results else .5
    return model

def run_integrated(scenario='adcs_wheel_weak', *,policy='information_gain',
                   budget_min=45,seed=7,onset_s=600,severity=1.,eclipse=False,initial_soc=.8,_sim=None):
    if scenario not in ALL_SCENARIOS:raise ValueError('Unknown scenario')
    if policy not in ('information_gain','temporal_adaptive','fixed','learned_risk'):raise ValueError('Unknown policy')
    if type(seed) is not int or not 0<=seed<=1000000:raise ValueError('Invalid seed')
    if type(budget_min) is not int or not 5<=budget_min<=90:raise ValueError('Invalid budget')
    if type(onset_s) is not int or onset_s<0 or onset_s%10:raise ValueError('Invalid onset')
    if type(eclipse) is not bool or not 0<=severity<=3 or not 0<=initial_soc<=1:raise ValueError('Invalid conditions')
    sim=_sim if _sim is not None else SpacecraftWithADCS(scenario,severity,onset_s,seed,initial_soc,eclipse)
    likelihood=fit_response_table() if policy=='information_gain' else None
    if policy=='learned_risk':
        from .learned_v09 import fit_failure_ranker, feature_row
        learned=fit_failure_ranker()
    else:learned=None
    belief={h:1/len(CAUSES) for h in CAUSES}
    ages={};checked=set();runs={};evidence=[];warnings={};spent=0;next_fixed=0
    while True:
        eligible=[t for t in CATALOG if t.cost<=budget_min-spent]
        if policy=='fixed':
            eligible=[t for t in CATALOG[next_fixed:] if t.cost<=budget_min-spent]
        if not eligible:break
        # Fair observation interface: every policy receives one identical-format
        # pre-decision measurement before scoring, whether or not it uses ML.
        obs=sim.telemetry()
        warnings.update(_focus_from_telemetry(obs))
        if learned is not None:
            batch=[feature_row(obs,t,
                sum(min(3.,(sim.state.time_s-ages[r])/360.) for r in t.checks if r in ages)/len(t.checks),
                runs.get(t.id,0)) for t in eligible]
            risk_scores={t.id:float(pr) for t,pr in zip(eligible,learned.predict_proba(batch)[:,1])}
        else:risk_scores={}
        def score(t):
            coverage=len(set(t.checks)-checked)
            age=sum(min(3.,(sim.state.time_s-ages[r])/360.) for r in t.checks if r in ages)
            risk=warnings.get(t.subsystem,0.)
            gain=(information_gain(belief,{h:likelihood[h,t.id] for h in CAUSES})
                  if likelihood is not None else 0.)
            if learned is not None:
                riskprob=risk_scores[t.id]
                return (15*riskprob+2.0*coverage+1.0*age+.7*t.criticality+.2*risk-1.0*runs.get(t.id,0))/t.cost**.68
            return (7*gain+3.3*coverage+2.6*age+2.1*t.criticality+1.35*risk-1.15*runs.get(t.id,0))/t.cost**.68
        t=(eligible[0] if policy=='fixed' else max(eligible,key=lambda x:(score(x),-int(x.id[1:]))))
        if policy=='fixed':next_fixed=CATALOG.index(t)+1
        rec=execute(sim,t)
        spent+=t.cost
        if sim.state.time_s != spent*60:raise AssertionError('Clock mismatch')
        rec['decision']={'selection_score':round(score(t),4),'selected_policy':policy,
                         'expected_information_bits':round(information_gain(belief,{h:likelihood[h,t.id] for h in CAUSES}),5) if likelihood else None}
        rec['repeat_index']=runs.get(t.id,0);runs[t.id]=rec['repeat_index']+1
        if likelihood and rec['status'] in ('PASS','FAIL'):
            belief=update_belief(belief,{h:likelihood[h,t.id] for h in CAUSES},rec['status']=='FAIL')
        rec['posterior']={k:round(v,6) for k,v in belief.items()} if likelihood else None
        evidence.append(rec)
        for r,status in rec['checks'].items():
            if status is not None:checked.add(r);ages[r]=sim.state.time_s
        warnings=_focus_from_telemetry(rec['telemetry_end'])
        # ADCS observable warnings are designed independently of hidden scenario identity.
        tm=sim.adcs_telemetry()
        if tm['star_available'] is False or abs(tm['gyro_rads']-tm['star_rate_rads'])>.003:
            warnings['ADCS']=5.
        if rec['detected']:break
    estimate=max(belief,key=belief.get) if likelihood else None
    return {'meta':{'version':'0.8','scenario':scenario,'policy':policy,'budget_min':budget_min,'seed':seed,
                    'onset_s':onset_s,'scope':'Uncalibrated 1D ADCS coupled to toy EPS/thermal plant'},
            'detected':bool(evidence and evidence[-1]['detected']),
            'detection_s':int(sim.state.time_s) if evidence and evidence[-1]['detected'] else None,
            'spent_s':spent*60,'tests_run':len(evidence),'requirements_checked':sorted(checked),
            'estimated_cause':estimate,'cause_confidence':round(belief[estimate],6) if estimate else None,
            'posterior':{h:round(p,6) for h,p in belief.items()} if likelihood else {},
            'evidence':evidence,'adcs_terminal':sim.adcs_telemetry()}

def benchmark(seeds=(61,62),onset_s=600,budget_min=45):
    rows=[]
    for s in ALL_SCENARIOS:
        for seed in seeds:
            for p in ('fixed','temporal_adaptive','information_gain'):
                r=run_integrated(s,policy=p,seed=seed,budget_min=budget_min,onset_s=onset_s)
                rows.append({'scenario':s,'seed':seed,'policy':p,'detected':r['detected'],
                             'spent_s':r['spent_s'],'diagnosis':r['estimated_cause']})
    return rows
