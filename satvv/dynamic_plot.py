"""Optional Matplotlib diagnostic, explicitly labelled synthetic."""
from __future__ import annotations
from pathlib import Path
from typing import Any


def plot_scenario(result: dict[str, Any], target: Path) -> bool:
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    rows = result['telemetry']
    x = [r['time_s'] / 60 for r in rows]
    fig, axs = plt.subplots(3, 1, sharex=True, figsize=(11, 8.3))
    metrics = (
        ('bus_voltage_v', 'Bus voltage (V)'),
        ('battery_soc_pct', 'Battery SOC (%)'),
        ('temperature_c', 'Temperature (°C)'),
    )
    for ax, (key, label) in zip(axs, metrics):
        ax.plot(x, [r[key] for r in rows], linewidth=2, label='telemetry')
        ax.set_ylabel(label)
        ax.grid(alpha=0.22)
        if result['meta']['fault'] != 'none':
            ax.axvline(result['meta']['fault_start_s'] / 60, ls='--', c='tab:orange', alpha=0.7,
                       label='injection time')
        if key == 'bus_voltage_v':
            ax.axhline(6.70, ls=':', c='tab:red', label='limit')
        if key == 'temperature_c':
            ax.plot(x, [r['redundant_temperature_c'] for r in rows], lw=1.2, alpha=.65,
                    label='redundant sensor')
            ax.axhline(70, ls=':', c='tab:red', label='limit')
        ax.legend(loc='upper right', fontsize=8)
    axs[-1].set_xlabel('Elapsed simulation time (minutes)')
    fig.suptitle('SAT-V&V v0.2 — simulated spacecraft (illustrative, not flight-validated)', fontsize=12)
    fig.tight_layout()
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(target, dpi=155)
    plt.close(fig)
    return True
