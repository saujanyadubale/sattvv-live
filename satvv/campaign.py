"""Fair-budget campaigns: policy observes previous test evidence, not fault labels."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import random
from .core import Fault, TESTS, REQUIREMENTS, SpacecraftEmulator, TestCase


@dataclass
class Campaign:
    policy: str
    fault: str  # experiment harness only; not supplied to the policy
    budget: int
    spent: int
    detected: bool
    detection_cost: int | None
    checked_requirements: tuple[str, ...]
    visited_transitions: tuple[str, ...]
    evidence: list[dict[str, Any]]


def _focus_signals(telemetry: dict[str, float | bool]) -> dict[str, float]:
    """Risk signals based only on observed non-failing sensor margins."""
    result: dict[str, float] = {}
    if float(telemetry['bus_voltage_v']) < 7.10:
        result['EPS'] = 9.0
    if float(telemetry['temperature_c']) > 59.0:
        result['THERMAL'] = 1.5
    if float(telemetry['latency_ms']) > 175:
        result['COMMS'] = 1.5
    return result


def _choose_adaptive(remaining: list[TestCase], budget_left: int,
                     checked: set[str], visited: set[str], focus: dict[str, float]) -> TestCase:
    """Cost-normalized requirement/transition novelty + risk + telemetry-derived focus.

    The score never uses Fault or fault-to-test mappings. Tie-breaking is by ID.
    """
    eligible = [t for t in remaining if t.cost <= budget_left]
    if not eligible:
        raise ValueError('No feasible test')

    def score(test: TestCase) -> float:
        path = SpacecraftEmulator._PATHS[test.target]
        transitions = {f'{a.value}->{b.value}' for a, b in zip(path, path[1:])}
        unseen_req = len(set(test.checks) - checked)
        unseen_transitions = len(transitions - visited)
        reward = (3.0 * unseen_req + 1.0 * unseen_transitions +
                  1.3 * test.criticality + focus.get(test.subsystem, 0))
        return reward / (test.cost ** 0.65)

    return sorted(eligible, key=lambda t: (-score(t), t.id))[0]


def run_campaign(policy: str, fault: Fault, budget: int = 15, seed: int = 0) -> Campaign:
    if policy not in ('fixed', 'random', 'model_fixed', 'adaptive'):
        raise ValueError(f'Unknown policy: {policy}')
    if budget < 1:
        raise ValueError('budget must be >= 1')
    rng = random.Random(seed)
    simulator = SpacecraftEmulator(fault, seed=seed)
    remaining = list(TESTS)
    if policy == 'random':
        rng.shuffle(remaining)
    elif policy == 'model_fixed':
        # Stronger ablation: preplan the same greedy coverage/risk strategy,
        # but do it ONCE without observing any campaign telemetry.
        plan: list[TestCase] = []
        pool = remaining.copy()
        planned_coverage: set[str] = set()
        planned_transitions: set[str] = set()
        plan_cost = 0
        while any(t.cost <= budget - plan_cost for t in pool):
            chosen = _choose_adaptive(pool, budget - plan_cost, planned_coverage, planned_transitions, {})
            plan.append(chosen)
            pool.remove(chosen)
            plan_cost += chosen.cost
            planned_coverage.update(chosen.checks)
            path = SpacecraftEmulator._PATHS[chosen.target]
            planned_transitions.update(f'{a.value}->{b.value}' for a, b in zip(path, path[1:]))
        remaining = plan
    checked: set[str] = set()
    visited: set[str] = set()
    focus: dict[str, float] = {}
    evidence = []
    spent = 0
    detected = False
    detection_cost = None

    while remaining:
        if policy == 'adaptive':
            if not any(t.cost <= budget - spent for t in remaining):
                break
            test = _choose_adaptive(remaining, budget - spent, checked, visited, focus)
        else:
            # The scripted and random-permutation baselines execute their chosen
            # sequences *in order*; no skipping/reordering to back-fill spare time.
            # This also makes fault detection monotone in budget for each seed.
            if remaining[0].cost > budget - spent:
                break
            test = remaining[0]
        remaining.remove(test)
        obs = simulator.execute(test)
        spent += test.cost
        checked.update(obs.results)
        visited.update(obs.transitions)
        focus.update(_focus_signals(obs.telemetry))
        evidence.append({
            'test_id': test.id, 'test_name': test.name,
            'cost': test.cost, 'cumulative_cost': spent,
            'mode': obs.mode, 'transitions': list(obs.transitions),
            'checks': obs.results, 'telemetry': obs.telemetry,
            'pass': not obs.detected,
        })
        if obs.detected:
            detected = True
            detection_cost = spent
            break  # all policies share identical stop-on-detection rule

    return Campaign(policy, fault.value, budget, spent, detected,
                    detection_cost, tuple(sorted(checked)), tuple(sorted(visited)), evidence)
