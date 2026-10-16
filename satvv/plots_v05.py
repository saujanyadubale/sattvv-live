"""Charts from completed v0.5 benchmarks. Optional matplotlib dependency."""
from pathlib import Path

def plot_benchmarks(resultdir='results/v0.5'):
    import csv
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    source=Path(resultdir)
    with (source/'monitor_summary.csv').open() as f:
        monitor=list(csv.DictReader(f))
    fig,ax=plt.subplots(figsize=(9.2,5.2))
    methods=[r['method'].replace('_',' ') for r in monitor]
    rates=[float(r['fault_detection_fraction'])*100 for r in monitor]
    ax.barh(methods[::-1],rates[::-1])
    ax.set_xlim(0,105);ax.set_xlabel('Fault campaigns with a warning during active fault (%)')
    ax.set_title('v0.5 monitoring methods | synthetic holdout campaigns')
    ax.grid(axis='x',alpha=.2);fig.tight_layout()
    path=source/'monitor_detection.png';fig.savefig(path,dpi=145);plt.close(fig)
    with (source/'verification_summary.csv').open() as f:
        checks=list(csv.DictReader(f))
    chosen=[r for r in checks if r['onset_s']=='600' and r['budget_min']=='35']
    fig,ax=plt.subplots(figsize=(9.5,5.2))
    names=[r['policy'].replace('_',' ') for r in chosen]
    values=[100*float(r['fault_detection_fraction']) for r in chosen]
    ax.barh(names[::-1],values[::-1])
    ax.set_xlim(0,105);ax.set_xlabel('Fault campaigns with a failed verification check (%)')
    ax.set_title('v0.5 sixteen-test policies | delayed fault, 35 min budget')
    ax.grid(axis='x',alpha=.2);fig.tight_layout()
    path2=source/'verification_detection.png';fig.savefig(path2,dpi=145);plt.close(fig)
    return [str(path),str(path2)]
