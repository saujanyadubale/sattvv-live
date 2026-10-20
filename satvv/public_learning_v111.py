"""Read-only, bounded public learning comparison for SAT-V&V v1.1.1.

No persistence, training, arbitrary policy selection, or filesystem writes.
The bundled model is a frozen synthetic classifier, not a flight-certified policy.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path

from .learning_v11 import load_active
from .challenge_v096 import DIFFICULTIES, INTENSITIES, run_challenge

FROZEN_MODEL_DIR = Path(__file__).resolve().parent / 'model_v111'
ORIGINAL = 'predictive_active'
CANDIDATE = 'predictive_learned_soft_retest'
PUBLIC_POLICIES = (ORIGINAL, CANDIDATE)

@lru_cache(maxsize=1)
def _model():
    import sklearn
    if sklearn.__version__ != '1.9.1':
        raise RuntimeError('Frozen research model requires scikit-learn 1.9.1')
    model, meta = load_active(FROZEN_MODEL_DIR)
    if model is None or not meta.get('validation_pass'):
        raise RuntimeError('Validated public model unavailable')
    return model, meta


def public_status():
    _, meta = _model()
    return {
        'version': '1.1.1-public-pilot',
        'model_id': meta['id'],
        'validation_auc': meta['validation_auc'],
        'validation_brier': meta['validation_brier'],
        'policies': list(PUBLIC_POLICIES),
        'model_is_frozen': True,
        'public_training_enabled': False,
        'scope': 'Synthetic verification research only; no field qualification or guaranteed improvement.'
    }


def public_compare(data):
    if type(data) is not dict or set(data) - {'seed', 'budget_min', 'difficulty', 'intensity'}:
        raise ValueError('Unsupported public learning parameters')
    seed = data.get('seed', 8)
    budget = data.get('budget_min', 90)
    difficulty = data.get('difficulty', 'mixed')
    intensity = data.get('intensity', 'exploratory')
    if type(seed) is not int or not 0 <= seed <= 1_000_000:
        raise ValueError('Seed must be an integer between 0 and 1000000')
    if type(budget) is not int or not 15 <= budget <= 90:
        raise ValueError('Budget must be an integer between 15 and 90')
    if type(difficulty) is not str or difficulty not in DIFFICULTIES:
        raise ValueError('Unknown challenge difficulty')
    if type(intensity) is not str or intensity not in INTENSITIES:
        raise ValueError('Unknown fault intensity')
    model, meta = _model()
    runs=[]
    for policy in PUBLIC_POLICIES:
        outcome=run_challenge(difficulty=difficulty,seed=seed,budget_min=budget,policy=policy,
            intensity=intensity,_weak_monitor_priority=False,_continue_after_fail=False,
            _learning_model=model if policy==CANDIDATE else None,
            _learning_version=meta['id'] if policy==CANDIDATE else None)
        audit = outcome['audit']
        if not audit['passed']:
            raise RuntimeError('A verification evidence audit failed')
        # Only first-failure summary and procedure history are returned; no raw telemetry
        # arrays, persistent results, training/validation labels or future observations.
        history = [{
            'id': rec['test_id'],
            'start_min': round(rec['start_s']/60, 2),
            'end_min': round(rec['end_s']/60, 2),
            'status': rec['status'],
            'selection_guard': rec['decision'].get('coverage_guard', ''),
            'learned_score': rec['decision'].get('learned_test_scores',{}).get(rec['test_id']),
            'selected_was_repeat': rec['decision'].get('v111_decision_trace',{}).get('selected_was_repeat',False),
        } for rec in outcome['evidence']]
        runs.append({
            'policy': policy,
            'detected': bool(outcome['detected']),
            'first_failure_min': None if outcome['detection_s'] is None else round(outcome['detection_s']/60,2),
            'budget_censored_min': round(outcome['detection_s']/60,2) if outcome['detection_s'] is not None else budget,
            'distinct_tests': outcome['distinct_procedures'],
            'requirements_checked': len(outcome['requirements_checked']),
            'audit_passed': True,
            'test_history': history,
        })
    return {
        'settings': {'seed': seed, 'budget_min': budget, 'difficulty': difficulty,
                     'intensity': intensity, 'model_id': meta['id']},
        'runs': runs,
        'injected_faults_revealed_after_run': outcome['oracle_after_run']['faults'],
        'limitations': [
            'Synthetic physics, shared generator; no flight validation or proven improvement.',
            'A verified detection means at least one executed test produced a formal FAIL, not all injected mechanisms were detected.',
            'Active tests can change subsequent spacecraft state and telemetry.',
            'A warning or learned score is not a formal requirement failure.',
            'Development and model-training seeds may be available; this public demo is not an independent evaluation.',
        ],
    }
