"""Controlled policy evaluations on the persistent v0.3 dynamics engine."""
from __future__ import annotations
import csv
import json
from pathlib import Path
from statistics import mean
from .core import Fault
from .dynamic_campaign import POLICIES, run_dynamic_campaign

DEFAULT_BUDGETS = (8, 12, 20, 26, 33)


def benchmark_dynamic(outdir: Path, *, seeds: int = 10,
                      budgets: tuple[int,...] = DEFAULT_BUDGETS,
                      fault_start_s: int = 0) -> list[dict]:
    if not 1 <= seeds <= 1000:
        raise ValueError('seeds must be 1..1000')
    outdir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    raw: list[dict] = []
    for budget in budgets:
        for fault in Fault:
            for seed in range(seeds):
                for policy in POLICIES:
                    c = run_dynamic_campaign(policy, fault, budget_min=budget,
                                             seed=seed, fault_start_s=fault_start_s)
                    raw.append({'budget_min':budget, 'fault':fault.value, 'seed':seed,
                                'policy':policy, 'detected':int(c.detected),
                                'spent_min':c.spent_s / 60,
                                'detection_min':c.detection_cost_min if c.detected else '',
                                'requirements_checked':len(c.requirements_checked)})
        for policy in POLICIES:
            subset = [x for x in raw if x['budget_min'] == budget and x['policy'] == policy]
            positive = [x for x in subset if x['fault'] != Fault.NONE.value]
            negative = [x for x in subset if x['fault'] == Fault.NONE.value]
            detected = [x for x in positive if x['detected']]
            rows.append({'budget_min':budget, 'policy':policy,
                         'fault_cases':len(positive), 'healthy_cases':len(negative),
                         'detection_rate':mean(x['detected'] for x in positive),
                         'healthy_false_fail_rate':mean(x['detected'] for x in negative),
                         'mean_campaign_min':round(mean(x['spent_min'] for x in subset), 3),
                         'mean_detected_delay_min':round(mean(x['detection_min'] for x in detected),3) if detected else '',
                         'mean_checked_requirements':round(mean(x['requirements_checked'] for x in subset),3)})
    for name, data in [('dynamic_runs.csv',raw),('dynamic_summary.csv',rows)]:
        with (outdir/name).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=data[0].keys())
            writer.writeheader(); writer.writerows(data)
    with (outdir/'run_config.json').open('w') as f:
        json.dump({'seeds':seeds, 'budgets':budgets,'fault_start_s':fault_start_s,
                   'description':'Paired seed across policies; synthetic fault families, not validated detection rates.'},f,indent=2)
    return rows


def plot_dynamic(rows: list[dict], path: Path) -> bool:
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    fig, ax=plt.subplots(figsize=(9,5.4))
    for policy in POLICIES:
        r=sorted((x for x in rows if x['policy']==policy),key=lambda v:v['budget_min'])
        ax.plot([x['budget_min'] for x in r], [100*x['detection_rate'] for x in r],
                marker='o',label=policy.replace('_',' ').title())
    ax.set(xlabel='Verification budget (simulated minutes)',ylabel='Fault-case detection rate (%)',
           title='SAT-V&V v0.3 — Persistent dynamics benchmark (synthetic)')
    ax.set_ylim(0,105)
    ax.grid(alpha=.2); ax.legend()
    fig.tight_layout()
    fig.savefig(path,dpi=160)
    plt.close(fig)
    return True
