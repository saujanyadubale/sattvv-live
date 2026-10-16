"""Low-impact detection benchmark: warning sensitivity versus verified failure."""
import argparse,json
from pathlib import Path
from statistics import median
from .challenge_v096 import run_challenge
from .coupled import simulate_health
from .weak_monitor_v103 import WeakSignalMonitor
from .insights_v11 import analyse

KINDS={'sensor_drift':'sensor_drift','resistance_ramp':'battery_residual',
       'heater_fault':'thermal_innovation','radio_burst':'comms_loss'}

def controlled(seeds=range(500,520)):
    rows=[]
    for mode in ('NOMINAL','PAYLOAD','DOWNLINK'):
        for case in ('healthy','normal_load_cycle',*KINDS):
            warned=0;matched=0;legacy=0;delays=[]
            for seed in seeds:
                simulation=simulate_health(case,seed=seed,severity=.5,onset_s=420,
                    duration_s=2400,step_s=10,mode=mode)
                monitor=WeakSignalMonitor()
                for reading in simulation['telemetry']:monitor.update(reading)
                warned+=bool(monitor.events)
                old=analyse(simulation['telemetry'],[])['warning_events']
                legacy_kind={'sensor_drift':'thermal','resistance_ramp':'power','heater_fault':'thermal','radio_burst':'comms'}.get(case)
                legacy+=bool([e for e in old if e['kind']==legacy_kind and e['time_s']>=420]) if legacy_kind else bool(old)
                matches=[e for e in monitor.events if e['kind']==KINDS.get(case) and e['time_s']>=420]
                matched+=bool(matches)
                if matches:delays.append(matches[0]['time_s']-420)
            rows.append({'mode':mode,'scenario':case,'runs':len(seeds),
                'any_warning':warned,'legacy_warnings':legacy,'correct_signature_warning':matched if case in KINDS else None,
                'median_delay_s':median(delays) if delays else None})
    return rows

def paired(seeds=range(5,13),budget=90):
    rows=[]
    for seed in seeds:
        pairs=[]
        for flag in (False,True):
            result=run_challenge('mixed',seed,budget,'predictive_active',_weak_monitor_priority=flag)
            assert result['audit']['passed']
            warnings=result['weak_fault_analysis']['warning_events']
            faults=result['oracle_after_run']['faults']
            during=any(f['onset_s']<=w['time_s']<f['end_s'] for w in warnings for f in faults)
            pairs.append({'verified':result['detected'],'verification_time_s':result['detection_s'],
                'warnings':len(warnings),'warn_during_injection':during,'executed_tests':[e['test_id'] for e in result['evidence']]})
        rows.append({'seed':seed,'old':pairs[0],'weak_signal_priority':pairs[1]})
    return rows

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--seeds',type=int,default=8);parser.add_argument('--budget',type=int,default=90)
    args=parser.parse_args();mon=controlled();cmp=paired(range(5,5+args.seeds),args.budget)
    summary={'paired_seeds':len(cmp),'baseline_verified':sum(x['old']['verified'] for x in cmp),
             'updated_verified':sum(x['weak_signal_priority']['verified'] for x in cmp),
             'updated_warn_during_injection':sum(x['weak_signal_priority']['warn_during_injection'] for x in cmp),
             'wins':[x['seed'] for x in cmp if x['weak_signal_priority']['verified'] and not x['old']['verified']],
             'losses':[x['seed'] for x in cmp if x['old']['verified'] and not x['weak_signal_priority']['verified']]}
    output=Path('results/v1.0.3/benchmark.json');output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({'controlled':mon,'paired':cmp,'summary':summary},indent=2))
    print(json.dumps(summary,indent=2));print('saved',output)
if __name__=='__main__':main()
