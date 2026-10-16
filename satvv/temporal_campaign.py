"""v0.4: temporal verification research on the unchanged v0.2 spacecraft.

Three new policies share exactly the same simulator/test executor as v0.3:
- scheduled_retest: predefined time-independent patrol (including repeats)
- temporal_blind: online freshness/coverage scheduler without telemetry risk weights
- temporal_adaptive: same scheduler with only *observed* telemetry risk weights

Ground-truth injection parameters are handled by the evaluation harness ONLY.
A wait makes time pass and collects telemetry but NEVER passes/fails a requirement.
This is a synthetic experiment, not a flight-qualified diagnostic system.
"""
from __future__ import annotations

from dataclasses import asdict
from math import isfinite
from typing import Any

from .core import Fault, TESTS, TestCase
from .dynamics import DynamicSpacecraft, DynamicsConfig, FaultInjection
from .dynamic_campaign import (DynamicCampaign, POLICIES, SAMPLE_S, SECONDS_PER_COST,
                               _execute_test, _focus_from_telemetry,
                               run_dynamic_campaign)

TEMPORAL_POLICIES = ('scheduled_retest', 'temporal_blind', 'temporal_adaptive')
ALL_POLICIES = POLICIES + TEMPORAL_POLICIES
WAIT_S = 60
MIN_TEST_UTILITY = 3.0  # minimum marginal utility to run a test instead of passively monitoring
# Fixed in advance, independent of fault information. Repeat T01 as a periodic
# health spot check; rotate through all tests before repeating the patrol.
PATROL_IDS = ('T01', 'T03', 'T05', 'T01', 'T11', 'T04', 'T06', 'T01',
              'T10', 'T12', 'T07', 'T08', 'T09', 'T02')
BY_ID = {t.id: t for t in TESTS}


def _check_inputs(policy: str, fault: Fault | str, budget_min: int,
                  seed: int, severity: float, fault_start_s: int,
                  sunlit: bool, initial_soc: float) -> Fault:
    if policy not in ALL_POLICIES:
        raise ValueError('Unsupported policy')
    if type(budget_min) is not int or not 1 <= budget_min <= 60:
        raise ValueError('budget_min must be an integer in [1,60]')
    if type(seed) is not int or not 0 <= seed <= 1000000:
        raise ValueError('seed must be an integer in [0,1000000]')
    if type(fault_start_s) is not int or fault_start_s < 0 or fault_start_s % SAMPLE_S:
        raise ValueError('fault_start_s must be a nonnegative 10-second multiple')
    if type(sunlit) is not bool:
        raise ValueError('sunlit must be a boolean')
    if type(initial_soc) not in (int, float) or not isfinite(initial_soc) or not 0 <= initial_soc <= 1:
        raise ValueError('initial_soc must be a finite number in [0,1]')
    if type(severity) not in (int, float) or not isfinite(severity) or not 0 <= severity <= 3:
        raise ValueError('severity must be a finite number in [0,3]')
    return Fault(fault)


def _wait(sim: DynamicSpacecraft, *, sunlit: bool, duration_s: int = WAIT_S) -> dict[str, Any]:
    """Idle time counts against budget; observations cannot directly detect faults."""
    start_s = int(sim.state.time_s)
    first = sim.telemetry(sunlit=sunlit)
    for _ in range(duration_s // SAMPLE_S):
        sim.step(SAMPLE_S, sunlit=sunlit)
    last = sim.telemetry(sunlit=sunlit)
    return {
        'kind': 'wait', 'test_id': 'WAIT', 'test_name': 'Wait for next monitoring opportunity',
        'subsystem': 'MONITOR', 'start_s': start_s, 'end_s': int(sim.state.time_s),
        'cost_min': duration_s / 60, 'checks': {}, 'actions': [], 'transitions': [],
        'status': 'WAIT', 'detected': False,
        'telemetry_start': first, 'telemetry_end': last,
        'samples': duration_s // SAMPLE_S + 1,
        'window_extrema': {'minimum_bus_voltage_v': min(first['bus_voltage_v'], last['bus_voltage_v']),
                           'maximum_temperature_c': max(first['temperature_c'], last['temperature_c'])},
        'warnings': _focus_from_telemetry(last),
    }


def _temporal_score(test: TestCase, *, now_s: int,
                    check_times: dict[str, int], test_times: dict[str, int],
                    counts: dict[str, int], focus: dict[str, float],
                    use_risk: bool) -> float:
    """Interpretable utility: coverage + freshness + independent warning signals.

    Not trained/tuned on the benchmark test faults. No fault label is available.
    """
    never_checked = sum(req not in check_times for req in test.checks)
    # Age of each required measurement. A stale check deserves another look;
    # a never-checked check gets priority through the novelty term.
    ages = [(now_s - check_times[r]) / 360 for r in test.checks if r in check_times]
    stale = sum(min(2.0, max(0.0, age)) for age in ages) / max(1, len(test.checks))
    last = test_times.get(test.id)
    # Strong short-term cooldown avoids repeatedly probing one cheap subsystem.
    recent_penalty = 4.0 if last is not None and now_s - last < 180 else 0.0
    repeated = counts.get(test.id, 0)
    # Focus is a telemetry-derived warning; cannot alone count as detection.
    warning = focus.get(test.subsystem, 0.0) if use_risk else 0.0
    utility = (3.3 * never_checked + 2.1 * test.criticality + 2.6 * stale
               + warning * 1.35 - 1.15 * repeated - recent_penalty)
    return utility / (test.cost ** .68)


def run_temporal_campaign(policy: str, fault: Fault | str = Fault.NONE, *,
                          budget_min: int = 20, seed: int = 7, severity: float = 1.0,
                          fault_start_s: int = 0, sunlit: bool = True,
                          initial_soc: float = .8) -> DynamicCampaign:
    """Execute a continuous campaign. Only explicit test checks may detect a fault."""
    fault = _check_inputs(policy, fault, budget_min, seed, severity, fault_start_s,
                          sunlit, initial_soc)
    if policy in POLICIES:  # retain exact v0.3 implementations as controls
        return run_dynamic_campaign(policy, fault, budget_min=budget_min, seed=seed,
                                    severity=severity, fault_start_s=fault_start_s,
                                    sunlit=sunlit, initial_soc=initial_soc)
    sim = DynamicSpacecraft(DynamicsConfig(initial_soc=initial_soc),
                           FaultInjection(fault, start_s=fault_start_s, severity=severity),
                           seed=seed)
    records: list[dict[str, Any]] = []
    checked: set[str] = set()
    visited: set[str] = set()
    check_times: dict[str, int] = {}
    test_times: dict[str, int] = {}
    counts: dict[str, int] = {}
    patrol_cursor = 0
    detection_s: int | None = None
    budget_s = budget_min * SECONDS_PER_COST
    while sim.state.time_s < budget_s:
        now_s = int(sim.state.time_s)
        left_s = budget_s - now_s
        observed = sim.telemetry(sunlit=sunlit)
        focus = _focus_from_telemetry(observed)
        chosen: TestCase | None = None
        rationale = ''
        score: float | None = None
        if policy == 'scheduled_retest':
            # Predeclared cyclic patrol; skips too-expensive tests only when the
            # remaining budget is insufficient, never based on telemetry.
            for offset in range(len(PATROL_IDS)):
                index = (patrol_cursor + offset) % len(PATROL_IDS)
                candidate = BY_ID[PATROL_IDS[index]]
                if candidate.cost * SECONDS_PER_COST <= left_s:
                    chosen = candidate
                    patrol_cursor = (index + 1) % len(PATROL_IDS)
                    break
            rationale = 'Predetermined repeating patrol; ignores observed telemetry'
        else:
            candidates = [t for t in TESTS if t.cost * SECONDS_PER_COST <= left_s]
            if candidates:
                use_risk = policy == 'temporal_adaptive'
                ranked = sorted(((_temporal_score(t, now_s=now_s, check_times=check_times,
                                                   test_times=test_times, counts=counts,
                                                   focus=focus, use_risk=use_risk), t)
                                 for t in candidates), key=lambda x: (-x[0], x[1].id))
                score, chosen = ranked[0]
                # Waiting is allowed if every eligible measurement has just
                # been checked, and there is no telemetry-derived urgency.
                recent = bool(checked) and all(
                    all(req in check_times and now_s-check_times[req] < 180 for req in t.checks)
                    for t in candidates)
                if (recent or (score is not None and score < MIN_TEST_UTILITY)) and (not use_risk or not focus) and left_s > WAIT_S:
                    chosen = None
                    rationale = ('Wait: coverage is fresh' if recent else
                                 'Wait: marginal test utility is below the monitoring threshold')
                else:
                    rationale = ('Telemetry risk + coverage + measurement age' if use_risk
                                 else 'Coverage + measurement age (no telemetry risk)')
        if chosen is None:
            rec = _wait(sim, sunlit=sunlit, duration_s=min(WAIT_S, left_s))
            rec['decision'] = rationale or 'Wait: no verification procedure fits remaining budget'
            rec['risk_signals_before'] = focus if policy == 'temporal_adaptive' else {}
        else:
            count_before = counts.get(chosen.id, 0)
            rec = _execute_test(sim, chosen, sunlit)
            rec['kind'] = 'test'
            rec['repeat_index'] = count_before
            rec['decision'] = rationale
            rec['selection_score'] = round(score, 3) if score is not None else None
            rec['risk_signals_before'] = focus if policy == 'temporal_adaptive' else {}
            counts[chosen.id] = count_before + 1
            test_times[chosen.id] = int(sim.state.time_s)
            for req, passed in rec['checks'].items():
                if passed is not None:
                    checked.add(req)
                    check_times[req] = int(sim.state.time_s)
            visited.update(rec['transitions'])
        records.append(rec)
        if rec['detected']:
            detection_s = int(sim.state.time_s)
            break
        if len(records) > 100:  # never reachable at 60-min budget with >=1-min steps
            raise AssertionError('Campaign made insufficient forward progress')
    spent_s = int(sim.state.time_s)
    assert spent_s <= budget_s and spent_s == round(sum(r['end_s']-r['start_s'] for r in records))
    return DynamicCampaign(policy=policy, fault=fault.value, budget_min=budget_min,
                           spent_s=spent_s, detected=detection_s is not None,
                           detection_s=detection_s,
                           detection_cost_min=(detection_s / 60 if detection_s is not None else None),
                           requirements_checked=sorted(checked),
                           transitions_visited=sorted(visited), evidence=records,
                           terminal_state=sim.telemetry(sunlit=sunlit))


def compare_temporal(*, fault: Fault | str = Fault.THERMAL_RUNAWAY,
                     budget_min: int = 20, seed: int = 7, severity: float = 1.0,
                     fault_start_s: int = 0, sunlit: bool = True,
                     initial_soc: float = .8) -> dict[str, Any]:
    params = dict(fault=fault, budget_min=budget_min, seed=seed,
                  severity=severity, fault_start_s=fault_start_s,
                  sunlit=sunlit, initial_soc=initial_soc)
    rows = {p: run_temporal_campaign(p, **params).as_dict() for p in ALL_POLICIES}
    return {'meta': {'version': '0.4', 'experiment': 'temporal_retesting',
                     'fault': Fault(fault).value, 'budget_min': budget_min,
                     'seed': seed, 'severity': severity, 'fault_start_s': fault_start_s,
                     'sunlit': sunlit, 'initial_soc': initial_soc,
                     'limitations': ('Synthetic, uncalibrated dynamics; decisions use handcrafted '
                                     'warnings, not a trained diagnosis model. Evidence is test-specific.')},
            'policies': rows}
