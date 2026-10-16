"""Command-line interface: v0.1 legacy, v0.2 dynamics, v0.3 integrated verification."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
from .core import Fault
from .campaign import run_campaign
from .experiment import benchmark, chart
from .dynamics import run_scenario
from .dynamic_plot import plot_scenario
from .dynamic_campaign import compare_dynamic
from .dynamic_benchmark import benchmark_dynamic, plot_dynamic
from .temporal_campaign import compare_temporal
from .temporal_benchmark import benchmark_temporal, plot_temporal
from .coupled import simulate_health, SCENARIOS
from .verification_v05 import run_verification_v05
from .ml_benchmark import run_benchmark
from .verification_benchmark_v05 import benchmark_verification
from .forecast_v06 import train_forecasters, forecast_trajectory
from .forecast_benchmark_v06 import benchmark_forecasting
from .active_v07 import run_active, pilot_benchmark
from .integrated_v08 import run_integrated, benchmark as benchmark_integrated
from .adcs_v08 import run_adcs_suite, ALL_SCENARIOS
from .benchmark_v09 import run_benchmark


def main():
    parser = argparse.ArgumentParser(description='SAT-V&V software-only research prototype v0.9.6')
    sub = parser.add_subparsers(dest='command', required=True)
    demo = sub.add_parser('demo', help='Run a legacy v0.1 test campaign')
    demo.add_argument('--policy', choices=('fixed', 'random', 'model_fixed', 'adaptive'), default='adaptive')
    demo.add_argument('--fault', choices=[f.value for f in Fault], default='undervoltage')
    demo.add_argument('--budget', type=int, default=20)
    demo.add_argument('--seed', type=int, default=7)
    bench = sub.add_parser('bench', help='Run legacy v0.1 paired multi-seed benchmark')
    bench.add_argument('--seeds', type=int, default=30)
    bench.add_argument('--out', default='results')
    sim = sub.add_parser('sim', help='Run time-evolving v0.2 spacecraft simulation')
    sim.add_argument('--fault', choices=[f.value for f in Fault], default='thermal_runaway')
    sim.add_argument('--severity', type=float, default=1.0)
    sim.add_argument('--fault-start', type=int, default=600)
    sim.add_argument('--duration', type=int, default=3000)
    sim.add_argument('--step', type=int, default=30)
    sim.add_argument('--sunlit', choices=('yes', 'no'), default='yes')
    sim.add_argument('--seed', type=int, default=7)
    sim.add_argument('--out', default='results/v0.2')
    integrated = sub.add_parser('verify', help='v0.3 four-policy persistent dynamics comparison')
    integrated.add_argument('--fault', choices=[f.value for f in Fault], default='undervoltage')
    integrated.add_argument('--budget', type=int, default=20, help='Simulated minutes')
    integrated.add_argument('--fault-start', type=int, default=0, help='Simulated seconds, multiple of 10')
    integrated.add_argument('--severity', type=float, default=1.0)
    integrated.add_argument('--soc', type=float, default=.8)
    integrated.add_argument('--sunlit', choices=('yes', 'no'), default='yes')
    integrated.add_argument('--seed', type=int, default=7)
    integrated.add_argument('--out', default='results/v0.3/comparison.json')
    bigbench = sub.add_parser('bench-dynamic', help='v0.3 multi-seed dynamic campaigns')
    bigbench.add_argument('--seeds', type=int, default=10)
    bigbench.add_argument('--fault-start', type=int, default=0)
    bigbench.add_argument('--out', default='results/v0.3')
    temporal = sub.add_parser('verify-temporal', help='v0.4 seven-policy comparison and decision traces')
    temporal.add_argument('--fault', choices=[f.value for f in Fault], default='undervoltage')
    temporal.add_argument('--budget', type=int, default=20)
    temporal.add_argument('--fault-start', type=int, default=600, help='Simulated seconds, 10-second aligned')
    temporal.add_argument('--severity', type=float, default=1.0)
    temporal.add_argument('--soc', type=float, default=.8)
    temporal.add_argument('--sunlit', choices=('yes','no'), default='yes')
    temporal.add_argument('--seed', type=int, default=7)
    temporal.add_argument('--out', default='results/v0.4/comparison.json')
    tbench = sub.add_parser('bench-temporal', help='v0.4 onset-sensitive quantitative benchmark')
    tbench.add_argument('--seeds', type=int, default=8)
    tbench.add_argument('--severity', type=float, default=1.0)
    tbench.add_argument('--soc', type=float, default=.8)
    tbench.add_argument('--sunlit', choices=('yes','no'), default='yes')
    tbench.add_argument('--out', default='results/v0.4')
    v05sim = sub.add_parser('health', help='v0.5 coupled simulator and telemetry')
    v05sim.add_argument('--scenario',choices=SCENARIOS,default='resistance_ramp')
    v05sim.add_argument('--severity',type=float,default=1.)
    v05sim.add_argument('--onset',type=int,default=480)
    v05sim.add_argument('--eclipse',action='store_true')
    v05sim.add_argument('--out',default='results/v0.5/health.json')
    v05verify=sub.add_parser('verify-v05',help='Run all seven strategies on v0.5 16-test catalog')
    v05verify.add_argument('--scenario',choices=SCENARIOS,default='resistance_ramp')
    v05verify.add_argument('--budget',type=int,default=35)
    v05verify.add_argument('--severity',type=float,default=1.)
    v05verify.add_argument('--onset',type=int,default=480)
    v05verify.add_argument('--eclipse',action='store_true')
    v05verify.add_argument('--out',default='results/v0.5/verification.json')
    v05ml=sub.add_parser('bench-ml',help='Train/evaluate v0.5 classical and ML detectors')
    v05ml.add_argument('--seeds',type=int,default=4)
    v05ml.add_argument('--train-seeds',type=int,default=5)
    v05ml.add_argument('--out',default='results/v0.5')
    vb=sub.add_parser('bench-v05',help='Seven-policy benchmark on expanded coupled simulator')
    vb.add_argument('--seeds',type=int,default=4)
    vb.add_argument('--out',default='results/v0.5')
    forecast = sub.add_parser('forecast-v06',help='v0.6 causal multistep voltage/thermal forecasts')
    forecast.add_argument('--scenario',choices=SCENARIOS,default='resistance_ramp')
    forecast.add_argument('--signal',choices=('bus_voltage_v','temperature_c'),default='bus_voltage_v')
    forecast.add_argument('--horizon',type=int,choices=(120,300,600),default=300)
    forecast.add_argument('--severity',type=float,default=1.)
    forecast.add_argument('--onset',type=int,default=480)
    forecast.add_argument('--mode',choices=('SAFE','NOMINAL','PAYLOAD','DOWNLINK'),default='PAYLOAD')
    forecast.add_argument('--eclipse',action='store_true')
    forecast.add_argument('--seed',type=int,default=7)
    forecast.add_argument('--out',default='results/v0.6/forecast_example.json')
    forecast_bench=sub.add_parser('bench-forecast',help='v0.6 held-out campaign prediction benchmark')
    forecast_bench.add_argument('--train-seeds',type=int,default=4)
    forecast_bench.add_argument('--calibration-seeds',type=int,default=4)
    forecast_bench.add_argument('--eval-seeds',type=int,default=3)
    forecast_bench.add_argument('--horizon',type=int,choices=(120,300,600),default=300)
    forecast_bench.add_argument('--out',default='results/v0.6')
    ac=sub.add_parser('active-v07',help='Bayesian information gain / coverage verification')
    ac.add_argument('--scenario',choices=SCENARIOS,default='resistance_ramp')
    ac.add_argument('--policy',choices=('information_gain','coverage'),default='information_gain')
    ac.add_argument('--budget',type=int,default=35)
    ac.add_argument('--onset',type=int,default=600)
    ac.add_argument('--seed',type=int,default=7)
    ac.add_argument('--out',default='results/v0.7/active_example.json')
    ab=sub.add_parser('bench-active',help='Paired pilot against temporal adaptive')
    ab.add_argument('--out',default='results/v0.7/pilot.json')
    adcs=sub.add_parser('adcs-suite',help='v0.8 single-axis coupled ADCS tests T17-T20')
    adcs.add_argument('--scenario',choices=ALL_SCENARIOS,default='adcs_wheel_weak')
    adcs.add_argument('--onset',type=int,default=0)
    adcs.add_argument('--out',default='results/v0.8/adcs_suite.json')
    iv=sub.add_parser('integrated-v08',help='20-procedure coupled multi-subsystem campaign')
    iv.add_argument('--scenario',choices=ALL_SCENARIOS,default='adcs_gyro_bias')
    iv.add_argument('--policy',choices=('fixed','temporal_adaptive','information_gain'),default='information_gain')
    iv.add_argument('--budget',type=int,default=45)
    iv.add_argument('--onset',type=int,default=600)
    iv.add_argument('--out',default='results/v0.8/integrated_example.json')
    ib=sub.add_parser('bench-integrated',help='Paired integrated 20-procedure pilot')
    ib.add_argument('--out',default='results/v0.8/pilot.json')
    stress=sub.add_parser('bench-stress',help='v0.9 independent OOD and ML ranking benchmark')
    stress.add_argument('--seeds',type=int,default=4)
    stress.add_argument('--out',default='results/v0.9')
    sr=sub.add_parser('stress-v09',help='One held-out stress-case verification campaign')
    sr.add_argument('--case',default='dual_resistance_sensor')
    sr.add_argument('--policy',choices=('fixed','temporal_adaptive','information_gain','learned_risk'),default='information_gain')
    sr.add_argument('--budget',type=int,default=25)
    sr.add_argument('--seed',type=int,default=801)
    sr.add_argument('--out',default='results/v0.9/stress_example.json')
    for cmd_name in ('pipeline-v093','pipeline-v094'):
        pl = sub.add_parser(cmd_name,help='v0.9.4 closed-loop verification with auditable evidence')
        pl.add_argument('--scenario',default='resistance_ramp')
        pl.add_argument('--policy',default='predictive_active',choices=('fixed','temporal_adaptive','information_gain','learned_risk','predictive_active','predictive_greedy_v101'))
        pl.add_argument('--budget',type=int,default=30)
        pl.add_argument('--onset',type=int,default=600)
        pl.add_argument('--horizon',type=int,default=300,choices=(120,300,600))
        pl.add_argument('--seed',type=int,default=7)
        pl.add_argument('--out',default='results/v0.9.4/example.json')
    pb = sub.add_parser('bench-pipeline',help='v0.9.3 paired compound-fault policy benchmark')
    pb.add_argument('--seeds',type=int,default=2)
    pb.add_argument('--out',default='results/v0.9.3')
    auditbench=sub.add_parser('bench-audit',help='v0.9.4 paired monitoring/diagnostic audit benchmark')
    auditbench.add_argument('--seeds',type=int,default=3,help='Independent seeds per scenario family')
    auditbench.add_argument('--out',default='results/v0.9.4')
    bc=sub.add_parser('bench-challenge',help='v0.9.6 seeded paired random and multi-fault challenge benchmark')
    bc.add_argument('--seeds',type=int,default=3)
    bc.add_argument('--budget',type=int,default=30)
    bc.add_argument('--out',default='results/v0.9.6')
    serve = sub.add_parser('serve', help='Interactive browser preview backed by Python')
    serve.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if args.command == 'bench-challenge':
        from .benchmark_v096 import benchmark
        if not 1<=args.seeds<=30:raise ValueError('Seed count must be 1–30')
        report=benchmark(tuple(range(77,77+args.seeds)),args.budget)
        dest=Path(args.out);dest.mkdir(parents=True,exist_ok=True)
        (dest/'challenge_benchmark.json').write_text(json.dumps(report,indent=2)+'\n')
        with (dest/'summary.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=report['summary'][0]);writer.writeheader();writer.writerows(report['summary'])
        print('Results saved:',dest.resolve())
        for r in report['summary']:
            print(r['difficulty'],r['policy'],f"detection {r['detection_rate']:.1%}",
                  f"partial diagnosis {r['diagnosis_partial_match_rate']:.1%}")
    elif args.command == 'bench-audit':
        from .benchmark_v094 import benchmark as audit_benchmark,save as save_audit
        if not 1<=args.seeds<=100:raise ValueError('seeds must be in [1,100]')
        r=audit_benchmark(seeds=tuple(901+i for i in range(args.seeds)))
        save_audit(r,args.out)
        for row in r['summary']:
            print(row['budget_min'],row['policy'],row['population'],
                  f"{row['positives']}/{row['campaigns']}")
        print('Saved',args.out)
    elif args.command == 'bench-pipeline':
        from .benchmark_v093 import benchmark,save
        report=benchmark(seeds=tuple(801+i for i in range(args.seeds)))
        save(report,args.out)
        print('Saved benchmark to',args.out)
    elif args.command in ('pipeline-v093','pipeline-v094'):
        from .pipeline_v093 import run_pipeline
        result=run_pipeline(args.scenario,policy=args.policy,budget_min=args.budget,
                            seed=args.seed,onset_s=args.onset,horizon_s=args.horizon)
        output=Path(args.out);output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(result,indent=2))
        print('Saved to',output.resolve(),'Detected:',result['detected'],'Audit:',result['audit']['passed'])
    elif args.command == 'bench-stress':
        report=run_benchmark(args.out,args.seeds)
        for r in report['summary']:
            if r['metric']=='fault_detection':print(r['budget_min'],r['policy'],f"{r['rate']:.1%}")
        print('Saved',Path(args.out).resolve())
    elif args.command == 'stress-v09':
        from .stress_v09 import STRESS_CASES,make_stress_sim
        case=next((x for x in STRESS_CASES if x.name==args.case),None)
        if case is None:raise ValueError('Unknown stress case')
        result=run_integrated(case.base,policy=args.policy,budget_min=args.budget,seed=args.seed,
                         onset_s=600,_sim=make_stress_sim(case,args.seed))
        result['meta']['stress_case']=case.name
        dest=Path(args.out);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(result,indent=2)+'\n')
        print('Saved',dest,'detected:',result['detected'])
    elif args.command == 'adcs-suite':
        result=run_adcs_suite(args.scenario,onset_s=args.onset)
        dest=Path(args.out);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(result,indent=2)+'\n')
        print('Saved',dest)
    elif args.command == 'integrated-v08':
        result=run_integrated(args.scenario,policy=args.policy,budget_min=args.budget,onset_s=args.onset)
        dest=Path(args.out);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(result,indent=2)+'\n')
        print('Saved',dest,'detected:',result['detected'])
    elif args.command == 'bench-integrated':
        result=benchmark_integrated()
        dest=Path(args.out);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(result,indent=2)+'\n')
        print('Saved',dest,'rows:',len(result))
    elif args.command == 'active-v07':
        result=run_active(args.scenario,policy=args.policy,budget_min=args.budget,onset_s=args.onset,seed=args.seed)
        target=Path(args.out);target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(result,indent=2)+'\n')
        print('Saved',target,'detected:',result['detected'],'estimated cause:',result['estimated_cause'])
    elif args.command == 'bench-active':
        rows=pilot_benchmark();target=Path(args.out);target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(rows,indent=2)+'\n')
        for policy in ('information_gain','coverage','temporal_adaptive'):
            f=[x for x in rows if x['policy']==policy and x['scenario'] not in ('healthy','normal_load_cycle')]
            print(policy,sum(x['detected'] for x in f),'/',len(f))
    elif args.command == 'forecast-v06':
        models=train_forecasters(horizon_s=args.horizon)
        sim=simulate_health(args.scenario,severity=args.severity,onset_s=args.onset,
                            duration_s=2400,step_s=30,mode=args.mode,seed=args.seed,
                            eclipse=args.eclipse)
        output=forecast_trajectory(sim['telemetry'],models,args.signal)
        output['scenario']=sim['meta'];output['telemetry']=sim['telemetry']
        destination=Path(args.out);destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_text(json.dumps(output,indent=2)+'\n')
        print('Saved forecast:',destination.resolve())
        print('Synthetic 90% campaign-band half-width:',round(output['interval_half_width'],4))
    elif args.command == 'bench-forecast':
        res=benchmark_forecasting(train_seeds=args.train_seeds,calibration_seeds=args.calibration_seeds,
                 eval_seeds=args.eval_seeds,horizon_s=args.horizon,out=args.out)
        print('Forecast horizon:',res['meta']['horizon_s'],'seconds; split campaigns:',
              res['meta']['train_campaigns'],res['meta']['calibration_campaigns'],res['meta']['evaluation_campaigns'])
        for row in res['summary']:
            print(f"{row['signal']:15} {row['method']:19} MAE={row['macro_mae']:.4f}  coverage={row['simultaneous_campaign_coverage']}")
    elif args.command == 'demo':
        result = run_campaign(args.policy, Fault(args.fault), args.budget, args.seed)
        print(json.dumps(result.__dict__, indent=2))
    elif args.command == 'bench':
        outdir = Path(args.out)
        rows = benchmark(outdir, seeds=args.seeds)
        made_chart = chart(rows, outdir / 'detection_curve.png')
        print('Budget | Fixed | Random | Model-fixed | Adaptive (fault-case detection rates)')
        for b in sorted(set(x['budget'] for x in rows)):
            r = {x['policy']: x for x in rows if x['budget'] == b}
            print(f"{b:>6} | {r['fixed']['detection_rate']:.1%} | {r['random']['detection_rate']:.1%} | {r['model_fixed']['detection_rate']:.1%} | {r['adaptive']['detection_rate']:.1%}")
        print(f'CSV outputs: {outdir.resolve()}')
        print(f'Chart generated: {made_chart}')
    elif args.command == 'sim':
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        result = run_scenario(fault=args.fault, severity=args.severity,
                              fault_start_s=args.fault_start, duration_s=args.duration,
                              step_s=args.step, sunlit=(args.sunlit == 'yes'), seed=args.seed)
        (out / 'scenario.json').write_text(json.dumps(result, indent=2) + '\n')
        with (out / 'telemetry.csv').open('w', newline='') as f:
            rows = result['telemetry']
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows({**r, 'alarms': ';'.join(r['alarms'])} for r in rows)
        (out / 'events.json').write_text(json.dumps(result['events'], indent=2) + '\n')
        plotted = plot_scenario(result, out / 'telemetry.png')
        print(json.dumps(result['summary'], indent=2))
        print(f'Saved v0.2 evidence: {out.resolve()} | Chart generated: {plotted}')
    elif args.command == 'verify':
        result = compare_dynamic(fault=args.fault, budget_min=args.budget, seed=args.seed,
                                 severity=args.severity, fault_start_s=args.fault_start,
                                 initial_soc=args.soc, sunlit=(args.sunlit == 'yes'))
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2) + '\n')
        print('Policy        | Detected | Test time | Tests | Checked requirements')
        for policy, info in result['policies'].items():
            print(f"{policy:13} | {str(info['detected']):8} | {info['spent_s']/60:8.1f} | {len(info['evidence']):5} | {len(info['requirements_checked']):3}")
        print(f'Saved evidence: {out.resolve()}')
    elif args.command == 'bench-dynamic':
        out = Path(args.out)
        rows = benchmark_dynamic(out, seeds=args.seeds, fault_start_s=args.fault_start)
        drawn = plot_dynamic(rows, out / 'dynamic_detection_curve.png')
        print('Budget | Fixed | Random | Model-fixed | Adaptive (dynamic fault-case detection rates)')
        for budget in sorted(set(r['budget_min'] for r in rows)):
            by = {r['policy']:r for r in rows if r['budget_min']==budget}
            print(f"{budget:>6} | {by['fixed']['detection_rate']:.1%} | {by['random']['detection_rate']:.1%} | {by['model_fixed']['detection_rate']:.1%} | {by['adaptive']['detection_rate']:.1%}")
        print(f'Saved {out.resolve()} | Chart generated: {drawn}')
    elif args.command == 'verify-temporal':
        result = compare_temporal(fault=args.fault, budget_min=args.budget, seed=args.seed,
                                  severity=args.severity, fault_start_s=args.fault_start,
                                  sunlit=(args.sunlit=='yes'), initial_soc=args.soc)
        out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result,indent=2)+'\n')
        print('Policy                  Detected    Time(min)   Tests   Repeats   Wait(min)')
        for p,c in result['policies'].items():
            tests=[r for r in c['evidence'] if r.get('kind','test')=='test']
            repeats=sum(r.get('repeat_index',0)>0 for r in tests)
            waits=sum((r['end_s']-r['start_s'])/60 for r in c['evidence'] if r.get('kind')=='wait')
            print(f'{p:24} {str(c["detected"]):9} {c["spent_s"]/60:9.0f} {len(tests):7} {repeats:9} {waits:11.0f}')
        print(f'Saved: {out.resolve()}')
    elif args.command == 'bench-temporal':
        out = Path(args.out)
        rows = benchmark_temporal(out, seeds=args.seeds, severity=args.severity,
                                  sunlit=(args.sunlit=='yes'), initial_soc=args.soc)
        for onset in (0,600):
            graph=plot_temporal(rows, out/f'detection_onset_{onset}s.png', onset_s=onset)
            print(f'\nOnset = {onset//60} min | PNG generated: {graph}')
            print('Budget | '+ ' | '.join(p[:9] for p in ('fixed','model_fixed','adaptive','scheduled_retest','temporal_blind','temporal_adaptive')))
            for budget in (12,20,26,33):
                subset={r['policy']:r for r in rows if r['fault_start_s']==onset and r['budget_min']==budget}
                print(f'{budget:>6} | '+' | '.join(f'{subset[p]["detection_rate"]:.0%}' for p in ('fixed','model_fixed','adaptive','scheduled_retest','temporal_blind','temporal_adaptive')))
        print(f'\nEvidence saved: {out.resolve()}')
    elif args.command == 'health':
        result=simulate_health(args.scenario,severity=args.severity,onset_s=args.onset,eclipse=args.eclipse)
        target=Path(args.out);target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(result,indent=2)+'\n')
        print('Saved telemetry:',target.resolve(), '| points:',len(result['telemetry']))
    elif args.command == 'verify-v05':
        rows={p:run_verification_v05(p,args.scenario,budget_min=args.budget,
                severity=args.severity,onset_s=args.onset,eclipse=args.eclipse)
              for p in ('fixed','random','model_fixed','adaptive','scheduled_retest','temporal_blind','temporal_adaptive')}
        target=Path(args.out);target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(rows,indent=2)+'\n')
        for p,c in rows.items():print(f'{p:22} detected={c["detected"]} tests={c["tests_run"]} time={c["spent_s"]/60:.0f} min')
        print('Saved verification:',target.resolve())
    elif args.command == 'bench-v05':
        result=benchmark_verification(seeds=args.seeds,out=args.out)
        print(f'Compared {result["meta"]["total_campaigns"]} synthetic campaigns')
        for row in result['summary']:
            if row['budget_min']==35 and row['onset_s']==600:print(row)
    elif args.command == 'bench-ml':
        result=run_benchmark(eval_seeds=args.seeds,train_seeds=args.train_seeds,out=args.out)
        for row in result['summary']: print(row)
    else:
        from .web_server import serve as start_server
        start_server(port=args.port)


if __name__ == '__main__':
    main()
