"""v0.9.4: reproducible, non-ML verification-evidence quality checks.

The measurements are produced by a synthetic simulator, not external flight
instruments. Audit consistency cannot prove physical validity or causal diagnosis.
"""
from __future__ import annotations
from math import isfinite

POLICY_REASONS={
    'fixed':'Fixed catalog order',
    'temporal_adaptive':'Telemetry warnings + time since verification',
    'information_gain':'Bayesian information gain + coverage',
    'learned_risk':'Offline-trained test failure likelihood',
    'predictive_active':'Risk-aware test planning with short-budget greedy fallback',
    'predictive_greedy_v101':'Expected information gain + forecast risk + coverage',
    'predictive_ml_feedback':'v1.0.2 bounded planner with causal ML monitoring feedback',
    'predictive_coverage':'v1.0.2 bounded planner with untried-test priority',
    'predictive_ml_coverage':'v1.0.2 bounded planner with causal ML feedback and untried-test priority',
    'predictive_learned':'v1.0.2 lookahead with offline learned test-outcome scores',
    'predictive_learned_coverage':'v1.0.2 lookahead with learned test ranking, continuous ML and coverage first',
    'predictive_soft_coverage':'v1.1.1 soft coverage without learned ranking',
    'predictive_learned_soft':'v1.1.1 learned ranker with soft coverage bonus',
    'predictive_learned_retest':'v1.1.1 learned ranker with time-aware retesting',
    'predictive_learned_soft_retest':'v1.1.1 learned ranker with soft coverage and time-aware retesting',
    'predictive_learned_soft_ml_retest':'v1.1.1 learned ranker with soft coverage, retesting and localized ML evidence',
}


def evaluate_bound(detail):
    """Derive boolean status directly from the recorded measurable and limit."""
    value=detail.get('measured')
    if value is None:return None
    if type(value) not in (int,float) or not isfinite(value):raise ValueError('Invalid measured value')
    threshold=detail.get('threshold')
    if type(threshold) not in (int,float) or not isfinite(threshold):raise ValueError('Invalid threshold')
    op=detail.get('operator')
    if op=='<=':return value<=threshold
    if op=='>=':return value>=threshold
    if op=='<':return value<threshold
    if op=='>':return value>threshold
    raise ValueError('Unsupported comparison operator')


def audit_trace(evidence, expected_policy, budget_min):
    """Checks policy provenance, monotonic timeline, numerical limits and checks.

    This augments but does not replace the legacy structural audit.
    """
    problems=[]
    previous_end=0
    for index,rec in enumerate(evidence,1):
        pre=f'Step {index}'
        d=rec.get('decision') or {}
        if d.get('selected_policy')!=expected_policy:
            problems.append(f'{pre}: policy provenance mismatch')
        if d.get('reason')!=POLICY_REASONS.get(expected_policy):
            problems.append(f'{pre}: decision rationale mismatched policy')
        if d.get('observation_time_s')!=rec.get('start_s'):
            problems.append(f'{pre}: decision observation time mismatch')
        if rec.get('start_s')!=previous_end:
            problems.append(f'{pre}: non-continuous time')
        end_time=rec.get('end_s')
        if (type(end_time) not in (int,float) or not isfinite(end_time) or
                end_time!=int(end_time) or end_time<=rec.get('start_s',-1)):
            problems.append(f'{pre}: invalid or non-integral timestamp')
        previous_end=rec.get('end_s',previous_end)
        if rec.get('status') not in ('PASS','FAIL','INCONCLUSIVE'):
            problems.append(f'{pre}: invalid status')
        win=rec.get('communication_window') or {}
        if win:
            if win.get('sample_start_s',-1)<rec['start_s'] or win.get('sample_end_s',1e100)>rec['end_s']:
                problems.append(f'{pre}: communication sample outside test window')
            if win.get('first_abnormal_time_s') is not None and not (
                win['sample_start_s']<=win['first_abnormal_time_s']<=win['sample_end_s']):
                problems.append(f'{pre}: communication warning timestamp outside samples')
            if rec.get('test_window_monitor',{}).get('comms_warning') is not (win.get('maximum_packet_loss_fraction',0)>.10):
                problems.append(f'{pre}: communication monitor contradicts recorded window')
        for req,detail in (rec.get('check_details') or {}).items():
            if req not in rec.get('checks',{}):
                problems.append(f'{pre}: metric for unknown requirement {req}')
                continue
            try:derived=evaluate_bound(detail)
            except (TypeError,ValueError) as exc:
                problems.append(f'{pre}: invalid measurement for {req}: {exc}')
                continue
            if derived is not rec['checks'][req]:
                problems.append(f'{pre}: measured bound disagrees with {req} status')
    if previous_end>budget_min*60:problems.append('Campaign exceeds budget')
    return {'passed':not problems,'problems':problems,'checked_steps':len(evidence),
            'checked_metrics':sum(len(r.get('check_details') or {}) for r in evidence),
            'scope':'Policy consistency, time ordering, and available numeric bounds; not independent physics validation'}
