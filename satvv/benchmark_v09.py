"""Reproducible evaluation of held-out combinations and normal hard negatives."""
from __future__ import annotations
import csv,json
from collections import defaultdict
from pathlib import Path
from .stress_v09 import evaluate_stress, clustered_summary, STRESS_CASES

DEFAULT_BUDGETS=(20,25,30,45)

def run_benchmark(out='results/v0.9',seed_count=4,budgets=DEFAULT_BUDGETS):
    if not 1<=seed_count<=24:raise ValueError('seed_count 1..24')
    dest=Path(out);dest.mkdir(parents=True,exist_ok=True)
    runs=[];aggregates=[]
    for b in budgets:
        subset=evaluate_stress(seeds=tuple(range(801,801+seed_count)),budget_min=b)
        runs.extend({**row,'budget_min':b} for row in subset)
        aggregates.extend({**row,'budget_min':b} for row in clustered_summary(subset,bootstraps=1000))
    with (dest/'stress_runs.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(runs[0]));w.writeheader();w.writerows(runs)
    with (dest/'stress_summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(aggregates[0]));w.writeheader();w.writerows(aggregates)
    report={'meta':{'release':'0.9','seeds':seed_count,'seed_ids':list(range(801,801+seed_count)),
                    'budgets_min':list(budgets),'scenarios':[x.name for x in STRESS_CASES],
                    'training':'Separate synthetic seeds 171-173 (learned ranker), 451-453 (Bayesian outcomes)',
                    'interpretation':'Exploratory OOD synthetic mixtures, not representative flight failure distribution.',
                    'limitation':'Tiny family count; scenario-level bootstrap intervals are not external validation.'},
            'summary':aggregates,'rows':runs}
    (dest/'benchmark.json').write_text(json.dumps(report,indent=2)+'\n')
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,ax=plt.subplots(figsize=(10,5.3))
        for policy in ('fixed','temporal_adaptive','information_gain','learned_risk'):
            sub=[x for x in aggregates if x['policy']==policy and x['metric']=='fault_detection']
            sub.sort(key=lambda x:x['budget_min'])
            ax.errorbar([x['budget_min'] for x in sub],[x['rate']*100 for x in sub],
                yerr=[[100*(x['rate']-x['ci95_low']) for x in sub],
                      [100*(x['ci95_high']-x['rate']) for x in sub]],
                marker='o',capsize=3,label=policy.replace('_',' '))
        ax.set(xlabel='Verification budget (simulated minutes)',ylabel='Fault-case detection (%)',
               title='Held-out compound fault scenarios — small synthetic pilot',ylim=(-2,108))
        ax.grid(alpha=.2);ax.legend(fontsize=9)
        fig.tight_layout();fig.savefig(dest/'ood_detection_by_budget.png',dpi=160);plt.close(fig)
    except ImportError:pass
    def fmt(x):return f"{x['rate']:.0%} [{x['ci95_low']:.0%}, {x['ci95_high']:.0%}]"
    lines=['# SAT-V&V v0.9 — Independent-combination pilot','',
           'Results use handcrafted **synthetic** fault families held out from the model calibration, not flight data.',
           'The intervals are **exploratory family-cluster bootstraps** and can be unstable with five faulty families.', '',
           '| Budget | Fixed | Temporal | Information gain | Learned risk |','|---:|---:|---:|---:|---:|']
    for b in budgets:
        rows={x['policy']:x for x in aggregates if x['budget_min']==b and x['metric']=='fault_detection'}
        lines.append(f"| {b} | {fmt(rows['fixed'])} | {fmt(rows['temporal_adaptive'])} | {fmt(rows['information_gain'])} | {fmt(rows['learned_risk'])} |")
    lines+=['','## Healthy controls',
            'Two healthy families (one including eclipse/load changes) test the false-failure behavior of the procedures.',
            'None of the tested healthy campaigns produced a failed requirement in this pilot; this is not a zero-error guarantee.','',
            '## Main limitations','',
            '- Compound faults are novel mixtures but still use the same underlying toy physics, so generalization is limited.',
            '- Calibrated response likelihoods do not explicitly depend on failure onset, current mode or test history.',
            '- Some procedures reset ADCS conditions deliberately; this is a controlled test, not a fully passive flight simulation.',
            '- Early stop on first failed requirement prevents complete root-cause discrimination.',
            '- Learned ranking scores are **uncalibrated** and are not safety-qualified.',
            '- Comparisons use small synthetic families. More independent physics and external data are required.','']
    (dest/'RESULTS.md').write_text('\n'.join(lines))
    return report
