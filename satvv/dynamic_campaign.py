"""v0.3 — testing policies operating on a single persistent dynamic spacecraft per campaign.

Fairness contract:
  * Policies receive only telemetry, executed requirements, transitions and test metadata.
  * Ground-truth fault kind/severity/start remains in the harness / JSON metadata.
  * All policies get the same initialized scenario and duration-valued test costs.
  * Each campaign runs on its own spacecraft; no reset between tests in that campaign.
  * A failed precondition makes a check INCONCLUSIVE, not a detected fault.
  * Tests are a toy engineering catalog with instantaneous mode commands, not ECSS AIT.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, asdict
import random
from typing import Any

from .core import Fault, Mode, REQUIREMENTS, TESTS, TestCase
from .dynamics import DynamicSpacecraft, DynamicsConfig, FaultInjection, LEGAL_TRANSITIONS

POLICIES = ('fixed', 'random', 'model_fixed', 'adaptive')
SECONDS_PER_COST = 60  # v0.1 arbitrary costs interpreted as simulated minutes here
SAMPLE_S = 10


@dataclass
class DynamicCampaign:
    policy: str
    fault: str  # evaluation metadata ONLY
    budget_min: int
    spent_s: int
    detected: bool
    detection_s: int | None
    detection_cost_min: int | None
    requirements_checked: list[str]
    transitions_visited: list[str]
    evidence: list[dict[str, Any]]
    terminal_state: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _path(start: Mode, goal: Mode) -> list[Mode] | None:
    if start == goal:
        return []
    frontier = deque([(start, [])])
    seen = {start}
    while frontier:
        curr, steps = frontier.popleft()
        for nxt in sorted(LEGAL_TRANSITIONS[curr], key=lambda x: x.value):
            if nxt in seen:
                continue
            new_steps = steps + [nxt]
            if nxt == goal:
                return new_steps
            seen.add(nxt)
            frontier.append((nxt, new_steps))
    return None


def _navigate(sim: DynamicSpacecraft, target: Mode) -> tuple[bool, list[dict[str, Any]]]:
    path = _path(sim.state.mode, target)
    if path is None:
        return False, []
    actions = []
    for nxt in path:
        before = sim.state.mode.value
        ack = sim.command(nxt)
        actions.append({'from': before, 'to': nxt.value, **ack})
        if not ack['accepted'] or sim.state.mode != nxt:
            return False, actions
    return sim.state.mode == target, actions


def _test_score(t: TestCase, checked: set[str], visited: set[str],
                focus: dict[str, float]) -> float:
    path = [Mode.BOOT] + _path(Mode.BOOT, t.target) if t.target != Mode.BOOT else [Mode.BOOT]
    transitions = {f'{a.value}->{b.value}' for a, b in zip(path, path[1:])}
    novel_reqs = len(set(t.checks) - checked)
    novel_transitions = len(transitions - visited)
    return (3 * novel_reqs + novel_transitions + 1.3 * t.criticality +
            focus.get(t.subsystem, 0.0)) / t.cost ** 0.65


def _best(pool: list[TestCase], remaining_min: int, checked: set[str],
          visited: set[str], focus: dict[str, float]) -> TestCase:
    eligible = [t for t in pool if t.cost <= remaining_min]
    return sorted(eligible, key=lambda t: (-_test_score(t, checked, visited, focus), t.id))[0]


def _focus_from_telemetry(tm: dict[str, Any]) -> dict[str, float]:
    """Warnings intentionally conservative and based ONLY on measured values.

    Warning thresholds are toy engineering assumptions, not learned or calibrated.
    """
    signals: dict[str, float] = {}
    if tm['bus_voltage_v'] < 7.45:
        signals['EPS'] = 7.0
    if tm['temperature_c'] > 45:
        signals['THERMAL'] = 4.0
    if abs(tm['temperature_c'] - tm['redundant_temperature_c']) > 1.0:
        signals['THERMAL'] = 7.0
    if tm['mode'] == Mode.DOWNLINK.value and tm['latency_ms'] > 150:
        signals['COMMS'] = 4.0
    return signals


def _plan_fixed(budget_min: int) -> list[TestCase]:
    """One-shot coverage/risk ordering; never sees runtime observations."""
    pool = list(TESTS)
    planned: list[TestCase] = []
    checked: set[str] = set()
    visited: set[str] = set()
    spent = 0
    while any(t.cost <= budget_min - spent for t in pool):
        t = _best(pool, budget_min - spent, checked, visited, {})
        planned.append(t)
        pool.remove(t)
        spent += t.cost
        checked.update(t.checks)
        p = [Mode.BOOT] + _path(Mode.BOOT, t.target)
        visited.update(f'{a.value}->{b.value}' for a, b in zip(p, p[1:]))
    return planned


def _execute_test(sim: DynamicSpacecraft, t: TestCase, sunlit: bool) -> dict[str, Any]:
    start = sim.state.time_s
    previous_events = len(sim.events)
    actions: list[dict[str, Any]] = []
    achieved = False
    guard_ok: bool | None = None
    payload_ok: bool | None = None

    # Test T04 and T09 deliberately power-cycle the payload; no false shortcut
    # just because the payload was already active from an earlier test.
    if t.id in ('T04', 'T09'):
        ready, reset_actions = _navigate(sim, Mode.SAFE)
        actions.extend(reset_actions)
        if ready:
            achieved, nav_actions = _navigate(sim, Mode.PAYLOAD)
            actions.extend(nav_actions)
        payload_ok = achieved
    elif t.id == 'T12':
        ready, nav_actions = _navigate(sim, Mode.SAFE)
        actions.extend(nav_actions)
        if ready:
            ack = sim.command(Mode.DOWNLINK)  # intentionally invalid command
            actions.append({'from': Mode.SAFE.value, 'to': Mode.DOWNLINK.value, **ack})
            guard_ok = not ack['accepted'] and ack['reason'] == 'ILLEGAL_TRANSITION'
            achieved = True  # test precondition was met, guard is assessed below
    else:
        achieved, nav_actions = _navigate(sim, t.target)
        actions.extend(nav_actions)

    if t.exercise_watchdog and achieved:
        sim.trigger_cpu_hang()

    # Fixed sample interval means fault onsets aligned to SAMPLE_S are applied
    # inside a test, not only at its start/end. Sampling time is simulated.
    samples: list[dict[str, Any]] = [sim.telemetry(sunlit=sunlit)]
    duration = t.cost * SECONDS_PER_COST
    for _ in range(duration // SAMPLE_S):
        sim.step(SAMPLE_S, sunlit=sunlit)
        samples.append(sim.telemetry(sunlit=sunlit))

    # Checks are evaluated from *observed sampled signals*, not simulator truth.
    # Only modes satisfying the test precondition count for link measurements.
    link_samples = [x for x in samples if x['mode'] == Mode.DOWNLINK.value]
    checks: dict[str, bool | None] = {}
    for requirement in t.checks:
        result: bool | None = None
        if requirement == 'REQ-MODE':
            result = achieved
        elif requirement == 'REQ-PAY':
            result = payload_ok if payload_ok is not None else (achieved and t.target == Mode.PAYLOAD)
        elif requirement == 'REQ-OBC-G':
            result = guard_ok
        elif not achieved:
            result = None  # Blocked by another fault or a failed mode precondition.
        elif requirement == 'REQ-EPS-V':
            result = all(x['bus_voltage_v'] >= 6.70 for x in samples)
        elif requirement == 'REQ-EPS-I':
            # Align the v0.1 check with the v0.2 dynamic model (1.30 A limit).
            result = all(x['bus_current_a'] <= sim.config.max_bus_current_a for x in samples)
        elif requirement == 'REQ-THM-T':
            result = all(x['temperature_c'] <= sim.config.max_temperature_c for x in samples)
        elif requirement == 'REQ-THM-D':
            result = all(abs(x['temperature_c']-x['redundant_temperature_c']) <= 3.0 for x in samples)
        elif requirement == 'REQ-COM-L':
            result = (all(x['packet_loss_fraction'] <= .10 for x in link_samples)
                      if link_samples else None)
        elif requirement == 'REQ-COM-T':
            result = (all(x['latency_ms'] <= 250 for x in link_samples)
                      if link_samples else None)
        elif requirement == 'REQ-COM-C':
            result = (all(x['checksum_ok'] for x in link_samples)
                      if link_samples else None)
        elif requirement == 'REQ-OBC-W':
            result = not sim.state.cpu_hung  # should recover within the 180-s test
        else:
            raise AssertionError(f'Unimplemented check: {requirement}')
        checks[requirement] = result

    transitions = [f"{x['from']}->{x['to']}" for x in actions if x['accepted']]
    fail_reqs = [r for r, ok in checks.items() if ok is False]
    success_reqs = [r for r, ok in checks.items() if ok is True]
    status = 'FAIL' if fail_reqs else ('PASS' if len(success_reqs) == len(checks) else 'INCONCLUSIVE')
    return {
        'test_id': t.id, 'test_name': t.name, 'subsystem': t.subsystem,
        'start_s': int(start), 'end_s': int(sim.state.time_s),
        'cost_min': t.cost, 'mode_requested': t.target.value,
        'actions': actions, 'transitions': transitions, 'checks': checks,
        'status': status, 'detected': bool(fail_reqs),
        'telemetry_start': samples[0], 'telemetry_end': samples[-1],
        'samples': len(samples),
        'window_extrema': {
            'minimum_bus_voltage_v': min(x['bus_voltage_v'] for x in samples),
            'maximum_temperature_c': max(x['temperature_c'] for x in samples),
            'maximum_bus_current_a': max(x['bus_current_a'] for x in samples),
            'maximum_sensor_disagreement_c': round(max(
                abs(x['temperature_c'] - x['redundant_temperature_c']) for x in samples), 3),
        },
        'observed_events': sim.events[previous_events:],
        'communication_window': ({'sample_count':len(link_samples),
            'maximum_packet_loss_fraction':max(x['packet_loss_fraction'] for x in link_samples),
            'first_abnormal_time_s':next((x['time_s'] for x in link_samples
                                    if x['packet_loss_fraction']>.10),None),
            'sample_start_s':link_samples[0]['time_s'],
            'sample_end_s':link_samples[-1]['time_s']}
            if link_samples else {}),
        'warnings': _focus_from_telemetry(samples[-1]),
    }


def run_dynamic_campaign(policy: str, fault: Fault | str, *, budget_min: int = 20,
                         seed: int = 7, severity: float = 1.0, fault_start_s: int = 0,
                         sunlit: bool = True, initial_soc: float = .80) -> DynamicCampaign:
    if policy not in POLICIES:
        raise ValueError('Unsupported policy')
    if type(budget_min) is not int or not 1 <= budget_min <= 60:
        raise ValueError('budget_min must be an integer between 1 and 60')
    if type(seed) is not int or not 0 <= seed <= 1000000:
        raise ValueError('seed must be integer between 0 and 1000000')
    if type(fault_start_s) is not int or fault_start_s < 0 or fault_start_s % SAMPLE_S:
        raise ValueError('fault_start_s must be a nonnegative 10-second multiple')
    if type(sunlit) is not bool:
        raise ValueError('sunlit must be boolean')
    if not 0 <= initial_soc <= 1:
        raise ValueError('initial_soc must be in [0,1]')
    fault = Fault(fault)
    sim = DynamicSpacecraft(DynamicsConfig(initial_soc=initial_soc),
                           FaultInjection(fault, start_s=fault_start_s, severity=severity),
                           seed=seed)
    remaining = list(TESTS)
    if policy == 'random':
        random.Random(seed).shuffle(remaining)
    elif policy == 'model_fixed':
        remaining = _plan_fixed(budget_min)
    checked: set[str] = set()
    visited: set[str] = set()
    focus: dict[str, float] = {}
    evidence: list[dict[str, Any]] = []
    spent = 0
    detected_at: int | None = None
    while remaining:
        if policy == 'adaptive':
            if not any(t.cost <= budget_min - spent for t in remaining):
                break
            chosen = _best(remaining, budget_min - spent, checked, visited, focus)
        else:
            if remaining[0].cost > budget_min - spent:
                break
            chosen = remaining[0]
        remaining.remove(chosen)
        record = _execute_test(sim, chosen, sunlit=sunlit)
        evidence.append(record)
        spent += chosen.cost
        checked.update(r for r, passed in record['checks'].items() if passed is not None)
        visited.update(record['transitions'])
        focus.update(record['warnings'])
        if record['detected']:
            detected_at = record['end_s']
            break  # same stop rule for all four policies

    if int(sim.state.time_s) != spent * SECONDS_PER_COST:
        raise AssertionError('Simulator elapsed time must equal charged test budget')
    terminal = sim.telemetry(sunlit=sunlit)
    return DynamicCampaign(policy=policy, fault=fault.value, budget_min=budget_min,
                           spent_s=spent*SECONDS_PER_COST,
                           detected=detected_at is not None,
                           detection_s=detected_at,
                           detection_cost_min=spent if detected_at is not None else None,
                           requirements_checked=sorted(checked),
                           transitions_visited=sorted(visited),
                           evidence=evidence, terminal_state=terminal)


def compare_dynamic(*, fault: Fault | str = Fault.THERMAL_RUNAWAY, budget_min: int = 20,
                    seed: int = 7, severity: float = 1.0, fault_start_s: int = 0,
                    sunlit: bool = True, initial_soc: float = .8) -> dict[str, Any]:
    params = dict(fault=Fault(fault), budget_min=budget_min, seed=seed,
                  severity=severity, fault_start_s=fault_start_s,
                  sunlit=sunlit, initial_soc=initial_soc)
    rows = {p: run_dynamic_campaign(p, **params).as_dict() for p in POLICIES}
    return {'meta': {'version': '0.3', 'experiment': 'persistent_dynamic_campaign',
                     'fault': params['fault'].value, 'budget_min': budget_min, 'seed': seed,
                     'severity': severity, 'fault_start_s': fault_start_s,
                     'sunlit': sunlit, 'initial_soc': initial_soc,
                     'limitations': 'Synthetic, uncalibrated physical model; toy verification procedures; no external spacecraft validation.'},
            'policies': rows}
