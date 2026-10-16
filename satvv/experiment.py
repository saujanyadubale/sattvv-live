"""Benchmark experiment and machine-readable reports."""
from __future__ import annotations
import csv
import json
import statistics
from pathlib import Path
from .core import Fault, REQUIREMENTS
from .campaign import run_campaign

POLICIES = ('fixed', 'random', 'model_fixed', 'adaptive')
FAULTS = tuple(f for f in Fault if f is not Fault.NONE)


def benchmark(outdir: Path, seeds: int = 30, budgets: tuple[int, ...] = (8, 12, 16, 20, 26, 33)) -> list[dict]:
    if seeds < 1:
        raise ValueError('seeds must be positive')
    outdir.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    summary: list[dict] = []

    for budget in budgets:
        for seed in range(seeds):
            for policy in POLICIES:
                for fault in (*FAULTS, Fault.NONE):
                    r = run_campaign(policy, fault, budget, seed)
                    records.append({
                        'policy': policy, 'fault': fault.value, 'budget': budget,
                        'seed': seed, 'detected': int(r.detected),
                        'spent': r.spent, 'detection_cost': r.detection_cost or '',
                        'requirement_coverage': round(len(r.checked_requirements)/len(REQUIREMENTS), 4),
                        'transition_count': len(r.visited_transitions),
                        'test_order': ' '.join(e['test_id'] for e in r.evidence),
                    })
        for policy in POLICIES:
            faults_only = [x for x in records if x['budget'] == budget and x['policy'] == policy and x['fault'] != 'none']
            healthy = [x for x in records if x['budget'] == budget and x['policy'] == policy and x['fault'] == 'none']
            detected = [x['detection_cost'] for x in faults_only if x['detected']]
            # Aggregate across 10 declared fault families * seeds. Not independent
            # physical faults. Percentages summarize *this emulator only*.
            summary.append({
                'policy': policy, 'budget': budget, 'fault_cases': len(faults_only),
                'detection_rate': round(statistics.mean(x['detected'] for x in faults_only), 4),
                'false_alarm_rate': round(statistics.mean(x['detected'] for x in healthy), 4),
                'mean_detection_cost_conditional': round(statistics.mean(detected), 2) if detected else '',
                'mean_req_coverage_healthy': round(statistics.mean(x['requirement_coverage'] for x in healthy), 4),
                'mean_transitions_healthy': round(statistics.mean(x['transition_count'] for x in healthy), 2),
            })
    def write_csv(path: Path, values: list[dict]) -> None:
        with path.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(values[0]))
            writer.writeheader()
            writer.writerows(values)
    write_csv(outdir / 'campaigns.csv', records)
    write_csv(outdir / 'summary.csv', summary)
    (outdir / 'demo_undervoltage_adaptive.json').write_text(
        json.dumps(run_campaign('adaptive', Fault.UNDERVOLTAGE, 20, 7).__dict__, indent=2) + '\n'
    )
    return summary


def chart(summary: list[dict], outpath: Path) -> bool:
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    for policy in POLICIES:
        rows = [x for x in summary if x['policy'] == policy]
        ax.plot([r['budget'] for r in rows], [100*r['detection_rate'] for r in rows],
                marker='o', linewidth=2, label=policy.title())
    ax.set(xlabel='Campaign budget (synthetic time units)',
           ylabel='Detected fault-case runs (%)',
           title='Illustrative emulator benchmark — NOT hardware results', ylim=(0, 103))
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(outpath, dpi=160)
    plt.close(fig)
    return True
