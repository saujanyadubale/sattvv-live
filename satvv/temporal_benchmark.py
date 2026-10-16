"""Paired, reproducible v0.4 policy benchmark including delayed-onset faults.

Reports *requirement-check* failure rates and healthy false-failure controls.
Confidence intervals use a paired hierarchical fault-family/seed bootstrap; they
quantify variation across THIS synthetic library, not real spacecraft uncertainty.
"""
from __future__ import annotations

import csv
import json
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean

from .core import Fault
from .temporal_campaign import ALL_POLICIES, run_temporal_campaign

DEFAULT_BUDGETS = (12, 20, 26, 33)
DEFAULT_ONSETS = (0, 600)


def _bootstrap_rates(rows: list[dict], n: int = 400, seed: int = 303) -> dict[str, tuple[float, float]]:
    """Paired resampling of fault families, then seeds within each family.

    SAME sampled cases for all policies, making relative differences meaningful.
    """
    groups: dict[str, dict[int, dict[str, int]]] = defaultdict(lambda: defaultdict(dict))
    for r in rows:
        if r['fault'] != Fault.NONE.value:
            groups[r['fault']][r['seed']][r['policy']] = r['detected']
    faults = sorted(groups)
    rng = random.Random(seed)
    samples: dict[str, list[float]] = {p: [] for p in ALL_POLICIES}
    for _ in range(n):
        scores = {p: [] for p in ALL_POLICIES}
        for _ in faults:
            group = groups[rng.choice(faults)]
            seeds = sorted(group)
            for _ in seeds:
                item = group[rng.choice(seeds)]
                for p in ALL_POLICIES:
                    scores[p].append(item[p])
        for p in ALL_POLICIES:
            samples[p].append(mean(scores[p]))
    result = {}
    for p in ALL_POLICIES:
        ordered = sorted(samples[p])
        result[p] = (ordered[int((n-1)*.025)], ordered[int((n-1)*.975)])
    return result


def benchmark_temporal(outdir: Path, *, seeds: int = 8,
                       budgets: tuple[int, ...] = DEFAULT_BUDGETS,
                       onsets: tuple[int, ...] = DEFAULT_ONSETS,
                       severity: float = 1.0, initial_soc: float = .8,
                       sunlit: bool = True) -> list[dict]:
    if type(seeds) is not int or not 1 <= seeds <= 100:
        raise ValueError('seeds must be in [1,100]')
    if not budgets or not onsets:
        raise ValueError('budgets and onsets must be nonempty')
    outdir.mkdir(parents=True, exist_ok=True)
    raw: list[dict] = []
    summary: list[dict] = []
    for onset in onsets:
        for budget in budgets:
            subset: list[dict] = []
            for fault in Fault:
                for seed in range(seeds):
                    for policy in ALL_POLICIES:
                        c = run_temporal_campaign(policy, fault,
                            budget_min=budget, seed=seed, severity=severity,
                            fault_start_s=onset, initial_soc=initial_soc,
                            sunlit=sunlit)
                        actions = [x for x in c.evidence if x.get('kind', 'test') == 'test']
                        row = {
                            'fault_start_s': onset, 'budget_min': budget,
                            'fault': fault.value, 'seed': seed, 'policy': policy,
                            'detected': int(c.detected),
                            'detection_min': c.detection_s/60 if c.detected else '',
                            'spent_min': c.spent_s/60,
                            'tests': len(actions),
                            'retests': sum(x.get('repeat_index', 0)>0 for x in actions),
                            'wait_min': sum((x['end_s']-x['start_s'])/60 for x in c.evidence
                                            if x.get('kind') == 'wait'),
                            'requirements_checked': len(c.requirements_checked),
                        }
                        subset.append(row)
                        raw.append(row)
            cis = _bootstrap_rates(subset, seed=404 + onset + budget)
            for p in ALL_POLICIES:
                policy_rows = [x for x in subset if x['policy'] == p]
                cases = [x for x in policy_rows if x['fault'] != Fault.NONE.value]
                controls = [x for x in policy_rows if x['fault'] == Fault.NONE.value]
                detected = [x for x in cases if x['detected']]
                lo, hi = cis[p]
                summary.append({
                    'fault_start_s': onset, 'budget_min': budget, 'policy': p,
                    'fault_cases': len(cases), 'healthy_cases': len(controls),
                    'detection_rate': round(mean(x['detected'] for x in cases), 5),
                    'ci95_low': round(lo, 5), 'ci95_high': round(hi, 5),
                    'healthy_false_fail_rate': round(mean(x['detected'] for x in controls), 5),
                    'mean_campaign_min': round(mean(x['spent_min'] for x in policy_rows), 3),
                    'mean_retests': round(mean(x['retests'] for x in policy_rows), 3),
                    'mean_wait_min': round(mean(x['wait_min'] for x in policy_rows), 3),
                    'mean_detection_min_when_detected': (
                        round(mean(x['detection_min'] for x in detected), 3) if detected else ''),
                })
    for name, dataset in [('temporal_runs.csv', raw), ('temporal_summary.csv', summary)]:
        with (outdir/name).open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=dataset[0].keys())
            writer.writeheader()
            writer.writerows(dataset)
    (outdir/'run_config.json').write_text(json.dumps({
        'version':'0.4', 'seeds':seeds, 'budgets':budgets, 'onsets':onsets,
        'severity':severity, 'initial_soc':initial_soc, 'sunlit':sunlit,
        'confidence_intervals': 'Paired hierarchical bootstrap across fault family and seed; synthetic scope only',
        'caveats':'Fault onset is known only to evaluator. No calibration or generalization guarantee.'
    }, indent=2) + '\n')
    return summary


def plot_temporal(rows: list[dict], path: Path, *, onset_s: int) -> bool:
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    palette = ['#60bceb','#bd9ef8','#ffbc75','#55d9b6','#e68fbd','#d2d6e0','#f2de72']
    fig, ax = plt.subplots(figsize=(10.5, 6))
    for p, color in zip(ALL_POLICIES, palette):
        selected = sorted((r for r in rows if r['policy'] == p and
                           r['fault_start_s'] == onset_s), key=lambda v:v['budget_min'])
        if not selected: continue
        xs=[r['budget_min'] for r in selected]
        ys=[100*r['detection_rate'] for r in selected]
        ax.plot(xs,ys,'o-',label=p.replace('_',' ').title(),color=color,linewidth=2)
        if p in ('temporal_blind','temporal_adaptive'):
            ax.fill_between(xs,[100*r['ci95_low'] for r in selected],
                            [100*r['ci95_high'] for r in selected],alpha=.11,color=color)
    ax.set(xlabel='Verification budget (simulated minutes)',
           ylabel='Fault-case detection rate (%)',
           title=f'SAT-V&V v0.4 — fault begins at {onset_s/60:g} min (synthetic)')
    ax.set_ylim(0,105)
    ax.grid(alpha=.18)
    ax.legend(fontsize=9,ncol=2,loc='lower right')
    fig.tight_layout()
    fig.savefig(path,dpi=150)
    plt.close(fig)
    return True
