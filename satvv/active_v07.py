"""v0.7: interpretable Bayesian active diagnosis (experimental, synthetic).

Calibration estimates test-outcome likelihoods using training campaigns only.
The policy never receives the hidden scenario. A test failure is not repair.
"""
from __future__ import annotations
from functools import lru_cache
from math import log2
from .coupled import CoupledSpacecraft, make_episodes, SCENARIOS
from .verification_v05 import ALL_TESTS, ADDITIONAL_TESTS, _extended_test, run_verification_v05
from .dynamic_campaign import _execute_test, _focus_from_telemetry

HYPOTHESES = ('healthy','resistance_ramp','intermittent_resistance','sensor_drift','heater_fault','radio_burst')

def entropy(values):
    return -sum(p*log2(p) for p in values if p>0)

def information_gain(belief, likelihood):
    """Expected information (bits) from binary PASS/FAIL, excluding INCONCLUSIVE."""
    p_fail=sum(belief[h]*likelihood[h] for h in HYPOTHESES)
    if p_fail<=0 or p_fail>=1: return 0.
    prior=entropy(belief.values())
    after_fail={h:belief[h]*likelihood[h]/p_fail for h in HYPOTHESES}
    after_pass={h:belief[h]*(1-likelihood[h])/(1-p_fail) for h in HYPOTHESES}
    return max(0.,prior-p_fail*entropy(after_fail.values())-(1-p_fail)*entropy(after_pass.values()))

def update_belief(belief, likelihood, failed):
    unnormalized={h:belief[h]*(likelihood[h] if failed else 1-likelihood[h]) for h in HYPOTHESES}
    denominator=sum(unnormalized.values())
    if not denominator: return dict(belief)
    return {h:unnormalized[h]/denominator for h in HYPOTHESES}

@lru_cache(maxsize=1)
def calibrated_likelihoods():
    """Fit smoothed Bernoulli response model on fixed, separate scenario seeds.

    Conditioning on a standardized diagnostic phase (fault present 5 min), not
    estimating full likelihoods conditional on operational mode and fault age.
    """
    rows={}
    for h in HYPOTHESES:
        responses={t.id:[] for t in ALL_TESTS}
        for seed in (301,302,303):
            for t in ALL_TESTS:
                sim=CoupledSpacecraft(make_episodes(h,1.0,0),seed=seed)
                for _ in range(30): sim.step(10)  # fixed diagnostic reference epoch
                rec=(_extended_test(sim,t) if t in ADDITIONAL_TESTS else _execute_test(sim,t,sunlit=True))
                if rec['status']!='INCONCLUSIVE':responses[t.id].append(int(rec['detected']))
        for tid,observed in responses.items():
            # Laplace smoothing and modest shrinkage to avoid certain likelihoods.
            rows[(h,tid)]=(sum(observed)+1)/(len(observed)+2) if observed else .5
    return rows

def run_active(scenario='resistance_ramp',*,seed=7,budget_min=35,onset_s=600,
               severity=1.0,eclipse=False,initial_soc=.8,policy='information_gain'):
    """Shared test catalog and simulator. Available policies: information_gain, coverage.

    Evaluate only executed test outcomes; posterior diagnoses are exploratory.
    """
    if policy not in ('information_gain','coverage'):raise ValueError('Unknown active policy')
    if scenario not in SCENARIOS:raise ValueError('Unknown scenario')
    if type(budget_min) is not int or not 5<=budget_min<=90:raise ValueError('Invalid budget')
    if type(seed) is not int or not 0<=seed<=1000000:raise ValueError('Invalid seed')
    if type(onset_s) is not int or onset_s<0 or onset_s%10:raise ValueError('Invalid onset')
    if not 0<=severity<=3 or not 0<=initial_soc<=1 or type(eclipse) is not bool:raise ValueError('Invalid conditions')
    sim=CoupledSpacecraft(make_episodes(scenario,severity,onset_s),seed=seed,initial_soc=initial_soc,eclipse=eclipse)
    belief={h:1/len(HYPOTHESES) for h in HYPOTHESES}
    calibrated=calibrated_likelihoods()
    evidence=[]; checked=set(); ages={}; repeated={};warnings={};total=0
    while total<budget_min:
        tests=[t for t in ALL_TESTS if t.cost<=budget_min-total]
        if not tests: break
        def valuation(test):
            chance={h:calibrated[(h,test.id)] for h in HYPOTHESES}
            gain=information_gain(belief,chance) if policy=='information_gain' else 0.
            coverage=len(set(test.checks)-checked)
            freshness=sum(min(3.,(sim.state.time_s-ages[r])/360.) for r in test.checks if r in ages)
            risk=warnings.get(test.subsystem,0.)
            # Score includes both information and requirement novelty; no oracle label.
            return (7*gain +3.3*coverage+2.6*freshness+2.1*test.criticality+1.35*risk - 1.15*repeated.get(test.id,0))/test.cost**.68
        pick=max(tests,key=lambda t:(valuation(t),-int(t.id[1:])))
        chance={h:calibrated[(h,pick.id)] for h in HYPOTHESES}
        prior=dict(belief); estimated_ig=information_gain(belief,chance)
        rec=(_extended_test(sim,pick) if pick in ADDITIONAL_TESTS else _execute_test(sim,pick,sunlit=True))
        total+=pick.cost
        if total*60!=sim.state.time_s:raise AssertionError('Clock mismatch')
        rec['decision']={'score':round(valuation(pick),4),'estimated_information_bits':round(estimated_ig,5),
                        'prior_top':max(prior,key=prior.get),'prior_probabilities':{k:round(v,4) for k,v in prior.items()}}
        if rec['status'] in ('PASS','FAIL'):
            belief=update_belief(belief,chance,rec['status']=='FAIL')
        rec['posterior']={h:round(belief[h],5) for h in HYPOTHESES}
        rec['repeat_index']=repeated.get(pick.id,0)
        repeated[pick.id]=rec['repeat_index']+1
        for r,v in rec['checks'].items():
            if v is not None:
                checked.add(r)
                ages[r]=sim.state.time_s
        warnings=_focus_from_telemetry(rec['telemetry_end'])
        evidence.append(rec)
        if rec['status']=='FAIL':break
    diagnosed=max(belief,key=belief.get)
    return {'meta':{'version':'0.7','policy':policy,'budget_min':budget_min,'onset_s':onset_s,
                    'scenario':scenario,'seed':seed,'limitations':'Calibration on small synthetic test outcomes. Diagnosis is not ground-truth certainty.'},
            'detected':bool(evidence and evidence[-1]['status']=='FAIL'),
            'detection_s':int(sim.state.time_s) if evidence and evidence[-1]['status']=='FAIL' else None,
            'spent_s':int(sim.state.time_s),'tests_run':len(evidence),'requirements_checked':sorted(checked),
            'estimated_cause':diagnosed,'cause_confidence':round(belief[diagnosed],5),
            'posterior':{h:round(v,5) for h,v in belief.items()},'evidence':evidence}

def pilot_benchmark(seeds=(51,52,53), budget=35, onset=600):
    summaries=[]
    for scenario in SCENARIOS:
        for seed in seeds:
            for policy in ('information_gain','coverage','temporal_adaptive'):
                c=(run_verification_v05('temporal_adaptive',scenario,budget_min=budget,onset_s=onset,seed=seed)
                   if policy=='temporal_adaptive' else run_active(scenario,seed=seed,budget_min=budget,onset_s=onset,policy=policy))
                summaries.append({'scenario':scenario,'seed':seed,'policy':policy,'detected':c['detected'],
                                  'time_min':c['spent_s']/60,
                                  'estimated_cause':c.get('estimated_cause')})
    return summaries
