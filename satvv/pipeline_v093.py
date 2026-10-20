"""v0.9.3: five-stage closed-loop verification research demonstrator.

All selection features are causal observables; hidden fault names are used only
in the simulator construction and evaluation metadata. Warning != verification FAIL.
The Bayesian likelihood, anomaly ML, and forecast ML were fit on separate
synthetic campaigns; none is calibrated as flight-operational probability.
"""
from __future__ import annotations
from functools import lru_cache
from math import isfinite
from .adcs_v08 import SpacecraftWithADCS,ADCS_FAULTS,ALL_SCENARIOS
from .integrated_v08 import CATALOG,CAUSES,execute
from .monitoring import engineer_features,classical_detector,feature_matrix
from .dynamic_campaign import _focus_from_telemetry
from .forecast_v06 import (train_forecasters,features_for_forecasting,
    _feature_vector,_baseline,LIMITS)
from .stress_v09 import STRESS_CASES,make_stress_sim
from .evidence_v094 import POLICY_REASONS,audit_trace
from .diagnosis_v096 import update_requirements,expected_information
from .coverage_v101 import adcs_observable_risk,choose_with_guard
from .planner_v102 import ranked_plan
from .weak_monitor_v103 import WeakSignalMonitor
from .fusion_monitor_local import FusedTelemetryMonitor
from .learning_v11 import pretest_features

METHODS=('fixed','temporal_adaptive','information_gain','learned_risk','predictive_active','predictive_greedy_v101',
         'predictive_ml_feedback','predictive_coverage','predictive_ml_coverage',
         'predictive_learned','predictive_learned_coverage',
         'predictive_soft_coverage','predictive_learned_soft','predictive_learned_retest',
         'predictive_learned_soft_retest','predictive_learned_soft_ml_retest')
LOCAL_ML_POLICIES=('predictive_ml_feedback','predictive_ml_coverage','predictive_learned_coverage',
                   'predictive_learned_soft_ml_retest')
LOCAL_LEARNED_POLICIES=('predictive_learned','predictive_learned_coverage',
                        'predictive_learned_soft','predictive_learned_retest',
                        'predictive_learned_soft_retest','predictive_learned_soft_ml_retest')
LOCAL_COVERAGE_POLICIES=('predictive_coverage','predictive_ml_coverage','predictive_learned_coverage')
LOCAL_SOFT_POLICIES=('predictive_soft_coverage','predictive_learned_soft',
                     'predictive_learned_soft_retest','predictive_learned_soft_ml_retest')
LOCAL_RETEST_POLICIES=('predictive_learned_retest','predictive_learned_soft_retest',
                       'predictive_learned_soft_ml_retest')
LOCAL_PREDICTIVE_POLICIES=('predictive_active','predictive_learned')+LOCAL_ML_POLICIES+(
    'predictive_coverage','predictive_soft_coverage','predictive_learned_soft',
    'predictive_learned_retest','predictive_learned_soft_retest')
DETECTORS=('limit','trend','cusum','physics_residual','isolation_forest','gradient_boosting')

@lru_cache(maxsize=1)
def detector_models():
    from .ml_benchmark import train_models
    return train_models(train_seeds=4)

@lru_cache(maxsize=3)
def future_models(horizon):
    return train_forecasters(horizon_s=horizon,train_seeds=4,calibration_seeds=4)

@lru_cache(maxsize=1)
def ranking_model():
    from .learned_v09 import fit_failure_ranker
    return fit_failure_ranker()

def forecast_now(rows, models):
    """Evaluate only observed rows <= current decision timestamp."""
    if len(rows)<4:return {}
    f=features_for_forecasting(rows)[-1]
    features=[_feature_vector(f)]
    forecasts={}
    for signal in ('bus_voltage_v','temperature_c'):
        ml=float(models.regressors[signal].predict(features)[0])
        physics=float(_baseline(f,signal,'physics_baseline',models.horizon_s))
        trend=float(_baseline(f,signal,'linear_trend',models.horizon_s))
        band=float(models.interval_half_width[signal]);limit=LIMITS[signal]
        low,high=ml-band,ml+band
        possible=low<limit if signal=='bus_voltage_v' else high>limit
        forecasts[signal]={'ml_estimate':round(ml,5),'physics_estimate':round(physics,5),
            'linear_estimate':round(trend,5),'lower':round(low,5),'upper':round(high,5),
            'limit':limit,'possible_crossing':bool(possible),
            'point_crossing':bool(ml<limit if signal=='bus_voltage_v' else ml>limit)}
    return forecasts

def audit_evidence(evidence,budget_min):
    """Independent structural verifier. Cannot establish correctness of the physics."""
    problems=[];end=0
    by_id={t.id:t for t in CATALOG}
    for n,rec in enumerate(evidence,1):
        if rec.get('start_s')!=end:problems.append(f'Step {n}: discontinuous clock')
        tid=rec.get('test_id');test=by_id.get(tid)
        if test is None:problems.append(f'Step {n}: unknown test');continue
        if rec.get('end_s')-rec.get('start_s') != test.cost*60:
            problems.append(f'Step {n}: incorrect test duration')
        checks=rec.get('checks',{})
        if set(checks)!=set(test.checks):problems.append(f'Step {n}: wrong requirements')
        if any(type(x) not in (bool,type(None)) for x in checks.values()):
            problems.append(f'Step {n}: invalid check value')
        expected='FAIL' if any(v is False for v in checks.values()) else (
            'PASS' if checks and all(v is True for v in checks.values()) else 'INCONCLUSIVE')
        if rec.get('status')!=expected:problems.append(f'Step {n}: status/check inconsistency')
        if rec.get('detected')!=(expected=='FAIL'):
            problems.append(f'Step {n}: detected flag inconsistent')
        end=rec.get('end_s')
    if end>budget_min*60:problems.append('Campaign exceeds budget')
    return {'passed':not problems,'problems':problems,'checked_steps':len(evidence),
            'meaning':'Structural evidence consistency, not physics validation'}

def run_pipeline(scenario='resistance_ramp', *,policy='predictive_active',budget_min=30,
                 seed=7,onset_s=600,severity=1.,eclipse=False,initial_soc=.8,
                 horizon_s=300,detector='physics_residual',_sim=None, _weak_monitor_priority=True,
                 _continue_after_fail=False,_learning_model=None,_learning_version=None):
    if scenario not in ALL_SCENARIOS and scenario not in {c.name for c in STRESS_CASES}:
        raise ValueError('Unknown spacecraft condition')
    if policy not in METHODS:raise ValueError('Unknown verification strategy')
    if policy in LOCAL_LEARNED_POLICIES and _learning_model is None:
        raise ValueError('No active learning model. Collect >=12 seeds and train a validated model first.')
    if detector not in DETECTORS:raise ValueError('Unsupported monitoring method')
    if type(budget_min) is not int or not 5<=budget_min<=90:raise ValueError('Budget must be 5–90 min')
    if type(seed) is not int or not 0<=seed<=1000000:raise ValueError('Invalid seed')
    if type(onset_s) is not int or not 0<=onset_s<=5400 or onset_s%10:raise ValueError('Invalid fault onset')
    if horizon_s not in (120,300,600) or type(horizon_s) is not int:raise ValueError('Invalid horizon')
    if type(eclipse) is not bool or not 0<=initial_soc<=1 or not 0<=severity<=3:
        raise ValueError('Invalid spacecraft settings')
    if any(not isfinite(float(v)) for v in (initial_soc,severity)):raise ValueError('Nonfinite setting')
    case=next((c for c in STRESS_CASES if c.name==scenario),None)
    sim=_sim if _sim is not None else (make_stress_sim(case,seed,onset_s) if case else SpacecraftWithADCS(
        scenario,severity,onset_s,seed,initial_soc,eclipse))
    history=[sim.telemetry()]
    weak_monitor=WeakSignalMonitor()
    weak_monitor.update(history[0])
    fused_monitor=None
    original_step=sim.step
    def recording_step(duration,*,sunlit=True):
        original_step(duration,sunlit=sunlit)
        history.append(sim.telemetry())
        weak_monitor.update(history[-1])
        if fused_monitor is not None:
            fused_monitor.update(history[-1],weak_monitor.risks(history[-1]['time_s']))
    sim.step=recording_step
    forecasters=future_models(horizon_s)
    monitors=detector_models();ranker=ranking_model() if policy=='learned_risk' else None
    if policy in LOCAL_ML_POLICIES:
        fused_monitor=FusedTelemetryMonitor(monitors)
        fused_monitor.update(history[0],weak_monitor.risks(history[0]['time_s']))
    belief={h:1/len(CAUSES) for h in CAUSES}
    coverage=set();ages={};repeats={};evidence=[];warnings_count=0;forecasts_risk_count=0
    catalog_index=0;last_test_end_s={};last_test_outcome={};steps=[];guard_skips=0;repeat_streak=0;coverage_overrides=0;warnings_latest=[];forecast_latest={};window_warnings=[];monitor_events=[]
    while sim.state.time_s<budget_min*60:
        remaining=(budget_min*60-sim.state.time_s)//60
        candidates=[t for t in CATALOG if t.cost<=remaining]
        if not candidates:break
        # 1 DETECT: historical measurement-based methods; all policies get the same interface.
        obs=sim.telemetry();history.append(obs)
        weak_monitor.update(obs)
        weak_risks=weak_monitor.risks(sim.state.time_s)
        if fused_monitor is not None:
            fused_monitor.update(obs,weak_risks)
        features=engineer_features(history)
        warnings_latest=[m for m in ('limit','trend','cusum','physics_residual')
                         if classical_detector(features,m)[-1]]
        if detector=='isolation_forest':
            flags=bool(-monitors['isolation_forest'].score_samples(feature_matrix(features[-1:]))[0]
                       >monitors['iforest_threshold'])
        elif detector=='gradient_boosting':
            flags=bool(monitors['gradient_boosting'].predict_proba(feature_matrix(features[-1:]))[0,1]
                       >monitors['gb_threshold'])
        else:
            flags=detector in warnings_latest
        if flags and detector not in warnings_latest:warnings_latest.append(detector)
        warnings_count+=int(flags)
        # 2 PREDICT: all methods see the same causal model outputs; only predictive_active uses it to rank tests.
        forecast_latest=forecast_now(history,forecasters)
        voltage_risk=forecast_latest.get('bus_voltage_v',{}).get('possible_crossing',False)
        thermal_risk=forecast_latest.get('temperature_c',{}).get('possible_crossing',False)
        forecasts_risk_count+=int(voltage_risk or thermal_risk)
        # Safety guard: avoid stressing already endangered equipment.
        unsafe=[]
        forecast_brownout=forecast_latest.get('bus_voltage_v',{}).get('point_crossing',False)
        if obs['bus_voltage_v']<6.85 or obs['battery_soc_pct']<18 or forecast_brownout:
            unsafe+=['T07','T13','T14']
        if obs['temperature_c']>67:unsafe+=['T06','T15']
        safe=[t for t in candidates if t.id not in unsafe]
        guard_skips+=len(candidates)-len(safe)
        if not safe:break
        warning_weights=_focus_from_telemetry(obs)
        if policy=='predictive_active' and _weak_monitor_priority:
            for subsystem,weight in weak_risks.items():
                warning_weights[subsystem]=max(warning_weights.get(subsystem,0.),weight)
        if fused_monitor is not None:
            for subsystem, weight in fused_monitor.risks().items():
                warning_weights[subsystem]=max(warning_weights.get(subsystem,0.),weight)
        adcs=sim.adcs_telemetry()
        adcs_risk=adcs_observable_risk(adcs)
        if adcs_risk and policy in LOCAL_PREDICTIVE_POLICIES+('predictive_greedy_v101',):
            warning_weights['ADCS']=max(warning_weights.get('ADCS',0),adcs_risk)
        risk={'EPS':int(voltage_risk)*6.,'THERMAL':int(thermal_risk)*6.}
        if flags:
            focus=max(warning_weights,key=warning_weights.get) if warning_weights else 'EPS'
            risk[focus]=risk.get(focus,0.)+3.
        # 3 DIAGNOSE: prior updated only after completed tests; no injected label in belief update.
        def gain_for(t):
            return expected_information(belief,t.checks)
        def novelty(t):return len(set(t.checks)-coverage)
        def freshness(t):return sum(min(3.,(sim.state.time_s-ages[r])/360) for r in t.checks if r in ages)
        def selection_score(t):
            base=(3.3*novelty(t)+2.6*freshness(t)+2.1*t.criticality
                  +warning_weights.get(t.subsystem,0.)-1.15*repeats.get(t.id,0))
            # Only applies to short-budget greedy fallback in v1.1.1; the
            # bounded planner applies these bonuses to every sequence candidate.
            if policy in LOCAL_SOFT_POLICIES and not repeats.get(t.id,0):
                base+=2.6
            if policy in LOCAL_RETEST_POLICIES and repeats.get(t.id,0):
                base+=retest_bonus.get(t.id,0.)
            if policy=='information_gain':base+=7*gain_for(t)
            if policy in LOCAL_PREDICTIVE_POLICIES+('predictive_greedy_v101',):base+=7*gain_for(t)+risk.get(t.subsystem,0.)
            if policy in LOCAL_LEARNED_POLICIES:
                base+=5.0*learned_scores.get(t.id,0.)
            if policy=='learned_risk':
                from .learned_v09 import feature_row
                age=freshness(t)/max(1,len(t.checks))
                probability=float(ranker.predict_proba([feature_row(obs,t,age,repeats.get(t.id,0))])[0,1])
                base+=15*probability
            return base/t.cost**.68
        learned_scores={}
        if policy in LOCAL_LEARNED_POLICIES:
            model=_learning_model
            # Causal pre-decision state only; no hidden oracle labels.
            xs=[pretest_features(obs,c,ages,repeats) for c in safe]
            if len(model.classes_)!=2 or 1 not in model.classes_:raise ValueError('Invalid learned model classes')
            scores=model.predict_proba(xs)[:,list(model.classes_).index(1)]
            learned_scores={c.id:float(p) for c,p in zip(safe,scores)}
        # v1.1.1: causal, finite bonuses based only on past executed tests and telemetry.
        # Hard constraints remain in safe[]; fault injections are NEVER examined here.
        is_soft = policy in LOCAL_SOFT_POLICIES
        is_retest = policy in LOCAL_RETEST_POLICIES
        safe_ids = [candidate.id for candidate in safe]
        untried_ids = [candidate.id for candidate in safe if repeats.get(candidate.id,0)==0]
        time_since_pass = {c.id: max(0.,(sim.state.time_s-last_test_end_s[c.id])/60.)
                           for c in safe if last_test_outcome.get(c.id)=='PASS'}
        retest_bonus={}
        if is_retest:
            for c in safe:
                if c.id in time_since_pass:
                    age_min=time_since_pass[c.id]
                    # Predictable renewal clock; no hidden fault onset or hindsight.
                    aging=min(1.5,max(0.,(age_min-18.)/20.))
                    critical=min(1.,max(0.,float(c.criticality)/5.))
                    local_cue=min(2.0,max(0.,float(warning_weights.get(c.subsystem,0.)))/3.)
                    retest_bonus[c.id]=round((3.8*aging*(0.70+0.30*critical)+
                        0.8*local_cue*min(1.,age_min/12.)),5)
        selection_guard='not_applicable'
        planned=None
        scheduler_mode='baseline'
        if policy=='fixed':
            eligible=[t for t in safe if CATALOG.index(t)>=catalog_index]
            if not eligible:break
            t=eligible[0];catalog_index=CATALOG.index(t)+1
        elif policy in LOCAL_PREDICTIVE_POLICIES:
            search_pool=safe
            if policy in LOCAL_COVERAGE_POLICIES:
                # Coverage-first: the planner still determines the ORDER. No test
                # is repeated while a new safe affordable procedure is available.
                # Unsafe tests are never forced; short budgets may not fit all 20.
                untried=[candidate for candidate in safe if repeats.get(candidate.id,0)==0]
                if untried:
                    search_pool=untried
                    selection_guard='coverage_first_untried_only'
                    coverage_overrides+=1
            else:
                search_pool=safe
            if budget_min<=35:
                # With very short campaigns, exploring sequences sacrifices urgent checks.
                # A documented short-budget fallback retains the verified greedy baseline.
                t,selection_guard=choose_with_guard(
                    search_pool,selection_score,repeats,repeat_streak=repeat_streak,remaining_min=remaining)
                if policy in LOCAL_COVERAGE_POLICIES and any(repeats.get(x.id,0)==0 for x in search_pool):
                    selection_guard='coverage_first_untried_only'
                scheduler_mode='short_budget_greedy_fallback'
                coverage_overrides+=int(selection_guard not in ('adaptive_score','coverage_first_untried_only'))
            else:
                planned=ranked_plan(search_pool,belief,coverage,ages,repeats,time_s=sim.state.time_s,
                    remaining_min=remaining,warning_weights=warning_weights,risk=risk,adcs_risk=adcs_risk,
                    learned_priorities=learned_scores,
                    soft_coverage_bonus=2.6 if is_soft else 0.,retest_bonuses=retest_bonus)
                t=planned.test
                if selection_guard!='coverage_first_untried_only':
                    selection_guard=('soft_coverage_retest' if is_soft and is_retest else
                                     'soft_coverage' if is_soft else
                                     'time_aware_retest' if is_retest else
                                     'bounded_sequence_lookahead')
                scheduler_mode='bounded_receding_horizon'
        elif policy=='predictive_greedy_v101':
            t,selection_guard=choose_with_guard(
                safe,selection_score,repeats,repeat_streak=repeat_streak,remaining_min=remaining)
            coverage_overrides+=int(selection_guard!='adaptive_score')
        else:
            t=max(safe,key=lambda item:(selection_score(item),-int(item.id[1:])))
        prior=dict(belief)
        score=(planned.objective if planned is not None else selection_score(t) if policy!='fixed' else None)
        ig=gain_for(t)
        # 4 VERIFY: executing the test changes the spacecraft state and provides measured checks.
        chosen_pretest=pretest_features(obs,t,ages,repeats)
        rec=execute(sim,t)
        rec['learning_pretest']=chosen_pretest
        # Keep the full evidence for requirement checks where the simulator
        # already exposes relevant extrema. Never substitute final telemetry
        # for an unrecorded within-test maximum/minimum.
        rec.setdefault('check_details',{})
        extrema=rec.get('window_extrema') or {}
        bound_metrics={
            'REQ-EPS-V':('minimum_bus_voltage_v','Minimum measured bus voltage','>=',6.70,'V'),
            'REQ-EPS-I':('maximum_bus_current_a','Maximum measured bus current','<=',1.30,'A'),
            'REQ-THM-T':('maximum_temperature_c','Maximum measured temperature','<=',70.,'°C'),
            'REQ-THM-D':('maximum_sensor_disagreement_c','Maximum sensor disagreement','<=',3.,'°C'),
        }
        for requirement,(field,metric,operator,threshold,unit) in bound_metrics.items():
            if requirement in rec['checks'] and rec['checks'][requirement] is not None and field in extrema:
                rec['check_details'].setdefault(requirement,{
                    'metric':metric,'measured':extrema[field],
                    'operator':operator,'threshold':threshold,'unit':unit,
                    'context':'Worst sampled value during the executed procedure'})
        # Distinguish warnings seen *during* a procedure from pre-decision
        # telemetry. Radio bursts can be observable only in DOWNLINK mode.
        window=rec.get('communication_window') or {}
        comm_on=(window.get('maximum_packet_loss_fraction',0)>.10)
        if comm_on:
            window_warnings.append('COMMS packet loss during '+t.id)
            monitor_events.append({'time_s':window['first_abnormal_time_s'],
                'kind':'COMMS_PACKET_LOSS','test_id':t.id,
                'peak_loss':window['maximum_packet_loss_fraction'],
                'source':'test-window telemetry'})
        rec['test_window_monitor']={'comms_warning':bool(comm_on),
            'observed_comms_samples':window.get('sample_count',0)}
        rec['repeat_index']=repeats.get(t.id,0)
        repeat_streak=repeat_streak+1 if rec['repeat_index'] else 0
        repeats[t.id]=rec['repeat_index']+1
        last_test_end_s[t.id]=int(rec['end_s'])
        last_test_outcome[t.id]=rec['status']
        rec['decision']={'reason':POLICY_REASONS[policy],
             'observation_time_s':int(obs['time_s']),
             'selected_policy':policy,'score':round(score,4) if score is not None else None,
             'expected_information_bits':round(ig,5),'warning':bool(flags),'test_window_comms_warning':bool(comm_on),
             'forecast_voltage_risk':bool(voltage_risk),'forecast_temperature_risk':bool(thermal_risk),
             'safety_excluded':list(unsafe),'coverage_guard':selection_guard,'scheduler_mode':scheduler_mode,
             'adcs_observable_risk':round(adcs_risk,3),
             'weak_signal_risks_before':{k:round(v,3) for k,v in weak_risks.items()} if _weak_monitor_priority else {},
             'ml_monitor_before':dict(fused_monitor.latest) if fused_monitor else None,
             'ml_cues_before':fused_monitor.risks() if fused_monitor else {},
             'posterior_before':prior,
             'learned_model_id':_learning_version if policy in LOCAL_LEARNED_POLICIES else None,
             'learned_test_scores':{k:round(v,5) for k,v in learned_scores.items()} if learned_scores else {},
             'v111_decision_trace':{
                  'candidate_safe_ids':safe_ids,'safety_excluded_ids':list(unsafe),
                  'untried_safe_ids':untried_ids,
                  'selected_was_repeat':bool(rec['repeat_index']),
                  'selected_since_prior_pass_min':time_since_pass.get(t.id),
                  'soft_coverage_bonus':2.6 if is_soft else 0.,
                  'retest_bonuses':retest_bonus,
                  'localized_observable_risks':{k:round(float(v),4) for k,v in warning_weights.items()},
                  'strategy_note':'Only causal measurements and prior executions; no oracle fault timing.'}}

        if planned is not None:
            rec['decision']['planned_sequence']=list(planned.sequence)
            rec['decision']['plan_objective']=planned.objective
            rec['decision']['candidate_sequences_evaluated']=planned.candidate_count
            rec['decision']['plan_assumptions']='Frozen observable heuristic risk; no future physics rollout or injected fault oracle'
        if rec['status'] in ('PASS','FAIL'):
            belief=update_requirements(belief,rec['checks'])
        rec['posterior']={k:round(v,6) for k,v in belief.items()}
        for requirement,passed in rec['checks'].items():
            if passed is not None:coverage.add(requirement);ages[requirement]=sim.state.time_s
        evidence.append(rec)
        steps.append({'time_s':int(rec['start_s']),'warning':bool(flags or comm_on),
                      'forecast_risk':bool(voltage_risk or thermal_risk),'test':t.id})
        if rec['status']=='FAIL' and not _continue_after_fail:break
    audit=audit_evidence(evidence,budget_min)
    provenance=audit_trace(evidence,policy,budget_min)
    audit['provenance']=provenance
    audit['passed']=audit['passed'] and provenance['passed']
    audit['problems']+=provenance['problems']
    predicted=any(x['forecast_risk'] for x in steps)
    first_failure=next((e for e in evidence if e['status']=='FAIL'),None)
    top=max(belief,key=belief.get)
    return {'meta':{'version':'0.9.4','software_release':'1.1.1-local','scenario':scenario,'policy':policy,'budget_min':budget_min,
         'seed':seed,'onset_s':onset_s,'learning_model_id':_learning_version or 'frozen','severity':severity,'initial_soc':initial_soc,
         'eclipse':eclipse,'horizon_s':horizon_s,'detector':detector,'stop_on_first_failure':not _continue_after_fail,
         'calibration':'Expert-specified requirement signatures; posterior weights not calibrated or validated',
         'randomized_stress_environment':case is not None},
        'display_policy':policy,
        'detected':first_failure is not None,
        'detection_s':first_failure['end_s'] if first_failure else None,
        'spent_s':int(sim.state.time_s),'tests_run':len(evidence),
        'estimated_cause':top,'cause_confidence':round(belief[top],6),
        'posterior':{h:round(v,6) for h,v in belief.items()},
        'requirements_checked':sorted(coverage),'evidence':evidence,
        'observations':history[::max(1,len(history)//200)],
        'monitoring_warning_times':sum(1 for x in steps if x['warning']),
        'monitor_events':monitor_events,
        'ml_monitor_analysis':fused_monitor.summary() if fused_monitor else None,
        'distinct_procedures':len(set(e['test_id'] for e in evidence)),
        'untested_procedures':[t.id for t in CATALOG if t.id not in set(e['test_id'] for e in evidence)],
        'continued_after_first_failure':bool(_continue_after_fail and first_failure and evidence[-1] is not first_failure),
        'weak_fault_analysis':weak_monitor.summary(),
        'forecast_risk_seen':predicted,'last_forecast':forecast_latest,
        'stages':{'detection':{'summary':f'{warnings_count} pre-test warning decisions; {len(monitor_events)} in-test communication warnings','methods':warnings_latest,'test_window_events':monitor_events},
                  'forecasting':{'summary':f'{horizon_s//60}-minute prediction: '+('possible limit crossing' if predicted else 'no predicted crossing at sampled decisions'),
                                 'latest':forecast_latest,'forecast_is_not_verification':True},
                  'diagnosis':{'summary':f'Top test-outcome hypothesis: {top} ({belief[top]*100:.1f}%, uncalibrated)','posterior':belief},
                  'verification':{'summary':f'{len(evidence)} tests run; '+('a requirement failed' if first_failure else 'no failed check'),
                                  'method':policy,'safety_guard_exclusions':guard_skips,
                                  'coverage_guard_overrides':coverage_overrides,
                                  'distinct_procedures':len(set(x['test_id'] for x in evidence))},
                  'audit':{'summary':'Evidence consistent' if audit['passed'] else 'Evidence inconsistencies found',**audit}},
        'audit':audit,'decision_history':steps,
        'notes':'Research model: simulated failures; forecasts and warnings are not formal verification.'}
