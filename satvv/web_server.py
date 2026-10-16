"""Local preview adapter. Same Python simulation used by CLI and browser."""
from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import csv
from .core import Fault
from .dynamics import run_scenario
from .dynamic_campaign import compare_dynamic
from .temporal_campaign import compare_temporal
from .coupled import simulate_health
from .monitoring import engineer_features, predict_methods
from .verification_v05 import run_verification_v05, ALL_TESTS, EXTRA_REQUIREMENTS
from .ml_benchmark import train_models
from .forecast_v06 import train_forecasters, forecast_trajectory
from .active_v07 import run_active
from .integrated_v08 import run_integrated
from .adcs_v08 import run_adcs_suite
from .stress_v09 import STRESS_CASES,make_stress_sim
from functools import lru_cache

@lru_cache(maxsize=1)
def _cached_models():
    return train_models(train_seeds=4)

@lru_cache(maxsize=3)
def _cached_forecasters(horizon_s: int):
    return train_forecasters(horizon_s=horizon_s, train_seeds=4, calibration_seeds=4)

WEB_INDEX = Path(__file__).resolve().parent.parent / 'web' / 'index.html'
WEB_DIR = WEB_INDEX.parent


class PreviewHandler(BaseHTTPRequestHandler):
    def _send(self, status: int, data: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if self.path in ('/', '/index.html', '/challenge', '/lab'):
            self._send(200, (WEB_DIR/'challenge.html').read_bytes(), 'text/html; charset=utf-8')
        elif self.path == '/classic':
            self._send(200, WEB_INDEX.read_bytes(), 'text/html; charset=utf-8')
        elif self.path == '/scene-background.svg':
            self._send(200,(WEB_DIR/'scene-background.svg').read_bytes(),'image/svg+xml; charset=utf-8')
        elif self.path == '/style.css':
            self._send(200,(WEB_DIR/'style.css').read_bytes(),'text/css; charset=utf-8')
        elif self.path == '/lab.js':
            self._send(200,(WEB_DIR/'lab.js').read_bytes(),'application/javascript; charset=utf-8')
        elif self.path in ('/how-it-works','/industry'):
            file='how-it-works.html' if self.path=='/how-it-works' else 'industry.html'
            self._send(200,(WEB_DIR/file).read_bytes(),'text/html; charset=utf-8')
        elif self.path == '/mission_beta.js':
            self._send(200,(WEB_DIR/'mission_beta.js').read_bytes(),'application/javascript; charset=utf-8')
        elif self.path == '/mission3d.js':
            self._send(200,(WEB_DIR/'mission3d.js').read_bytes(),'application/javascript; charset=utf-8')
        elif self.path == '/interpret_v11.js':
            self._send(200,(WEB_DIR/'interpret_v11.js').read_bytes(),'application/javascript; charset=utf-8')
        elif self.path == '/challenge.js':
            self._send(200,(WEB_DIR/'challenge.js').read_bytes(),'application/javascript; charset=utf-8')
        elif self.path == '/workflow_beta.js':
            self._send(200,(WEB_DIR/'workflow_beta.js').read_bytes(),'application/javascript; charset=utf-8')
        elif self.path == '/benchmark_view.js':
            self._send(200,(WEB_DIR/'benchmark_view.js').read_bytes(),'application/javascript; charset=utf-8')
        elif self.path == '/research.js':
            self._send(200,(WEB_DIR/'research.js').read_bytes(),'application/javascript; charset=utf-8')
        elif self.path == '/reference':
            self._send(200,(WEB_DIR/'reference.html').read_bytes(),'text/html; charset=utf-8')
        elif self.path == '/reference.js':
            self._send(200,(WEB_DIR/'reference.js').read_bytes(),'application/javascript; charset=utf-8')
        elif self.path == '/legacy':
            self._send(200,(WEB_DIR/'legacy.html').read_bytes(),'text/html; charset=utf-8')
        elif self.path == '/api/catalog':
            from .integrated_v08 import CATALOG
            body={'procedures':[{'id':t.id,'name':t.name,'subsystem':t.subsystem,'cost_min':t.cost,'requirements':list(t.checks)} for t in CATALOG]}
            self._send(200,json.dumps(body).encode(),'application/json')
        elif self.path == '/api/reference':
            from .integrated_v08 import CATALOG
            from .adcs_v08 import ADCS_REQUIREMENTS
            spec_path=WEB_DIR.parent/'docs'/'v0.6_dynamic_traceability.csv'
            specs={}
            with spec_path.open(newline='',encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    specs[(row['test_id'],row['requirement_id'])]=row['dynamic_specification']
            procedures=[{'id':t.id,'name':t.name,'subsystem':t.subsystem,'cost_min':t.cost,
                         'requirements':[{'id':rid,'specification':specs.get((t.id,rid),ADCS_REQUIREMENTS.get(rid))} for rid in t.checks]} for t in CATALOG]
            self._send(200,json.dumps({'procedures':procedures,'scope':'synthetic dynamic specifications'}).encode(),'application/json')
        elif self.path == '/api/health':
            self._send(200, b'{"ok":true,"version":"1.0.0"}', 'application/json')
        else:
            self._send(404, b'Not found', 'text/plain')

    def do_POST(self) -> None:
        if self.path not in ('/api/simulate', '/api/compare', '/api/compare-temporal', '/api/v05', '/api/forecast-v06', '/api/research', '/api/lab-run', '/api/challenge', '/api/unified'):
            self._send(404, b'Not found', 'text/plain')
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 8192:
                raise ValueError('Request payload must be 1–8192 bytes')
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError('Expected a JSON object')
            allowed = ({'mode','difficulty','policy','seed','budget_min','intensity','scenario','onset_s','severity','eclipse','initial_soc','horizon_s','detector'} if self.path == '/api/unified' else
                       {'difficulty','policy','seed','budget_min','intensity'} if self.path == '/api/challenge' else
                       {'scenario','policy','onset_s','budget_min','seed','severity','eclipse',
                        'initial_soc','horizon_s','detector'} if self.path == '/api/lab-run' else
                       {'scenario','policy','onset_s','budget_min','seed','severity','eclipse','initial_soc','experiment'}
                       if self.path == '/api/research' else
                       {'scenario','severity','onset_s','duration_s','seed','eclipse','initial_soc','mode','budget_min'}
                       if self.path == '/api/v05' else
                       {'scenario','severity','onset_s','duration_s','seed','eclipse','initial_soc','mode','horizon_s','signal'}
                       if self.path == '/api/forecast-v06' else
                       {'fault', 'severity', 'fault_start_s', 'duration_s', 'step_s',
                        'sunlit', 'seed', 'initial_soc', 'probe_watchdog'}
                       if self.path == '/api/simulate' else
                       {'fault', 'severity', 'fault_start_s', 'budget_min',
                        'sunlit', 'seed', 'initial_soc'})
            if not set(data).issubset(allowed):
                raise ValueError('Unsupported fields')
            if 'fault' in data:
                data['fault'] = Fault(data['fault'])
            # Strict primitive validation rather than accidentally accepting strings.
            for key in ('duration_s', 'step_s', 'seed', 'budget_min', 'fault_start_s', 'onset_s', 'horizon_s'):
                if key in data and type(data[key]) is not int:
                    raise ValueError(f'{key} must be an integer')
            for key in ('severity', 'initial_soc'):
                if key in data and type(data[key]) not in (float, int):
                    raise ValueError(f'{key} must be numeric')
            for key in ('sunlit', 'probe_watchdog', 'eclipse'):
                if key in data and type(data[key]) is not bool:
                    raise ValueError(f'{key} must be boolean')
            if self.path == '/api/unified':
                from .challenge_v096 import run_challenge
                from .pipeline_v093 import run_pipeline
                from .insights_v11 import analyse
                mode=data.pop('mode','random')
                if mode=='random':
                    keep=('difficulty','policy','seed','budget_min','intensity')
                    if any(k not in keep for k in data):raise ValueError('Manual parameters are not valid in random mode')
                    result=run_challenge(**data)
                elif mode=='manual':
                    keep=('scenario','policy','seed','budget_min','onset_s','severity','eclipse','initial_soc','horizon_s','detector')
                    if any(k not in keep for k in data):raise ValueError('Challenge parameters are not valid in manual mode')
                    result=run_pipeline(**data)
                    result['meta'].update({'challenge_level':'manual','challenge_intensity':'configured','challenge_seed':result['meta']['seed']})
                    result['oracle_after_run']={'healthy':result['meta']['scenario']=='healthy','faults':[],
                        'scope':'Manual scenario is user-selected; no hidden fault record is needed.'}
                    result['challenge_assessment']={'fault_exposures':[]}
                    result['diagnosis_match']=None
                else:raise ValueError('Unknown experiment mode')
                result['meta']['version']='1.0.0'
                result['meta']['experiment_mode']=mode
                result['insights_v11']=analyse(result.get('observations',[]),result.get('evidence',[]),result.get('weak_fault_analysis',{}).get('warning_events',[]))
            elif self.path == '/api/challenge':
                from .challenge_v096 import run_challenge
                from .insights_v11 import analyse
                result=run_challenge(**data)
                result['insights_v11']=analyse(result.get('observations',[]),result.get('evidence',[]),result.get('weak_fault_analysis',{}).get('warning_events',[]))
            elif self.path == '/api/lab-run':
                from .pipeline_v093 import run_pipeline
                result=run_pipeline(**data)
            elif self.path == '/api/research':
                if data.get('experiment','active') not in ('active','integrated','adcs_suite','stress'):raise ValueError('Unsupported research experiment')
                if data.get('experiment')=='stress':
                    case=next((x for x in STRESS_CASES if x.name==data.get('scenario')),None)
                    if case is None:raise ValueError('Unknown stress case. Select one of: '+', '.join(x.name for x in STRESS_CASES))
                    seed=data.get('seed',801)
                    onset=data.get('onset_s',600)
                    result=run_integrated(case.base,policy=data.get('policy','information_gain'),
                       budget_min=data.get('budget_min',25),seed=seed,onset_s=onset,
                       _sim=make_stress_sim(case,seed,onset_s=onset))
                    result['meta']['stress_case']=case.name
                elif data.get('experiment')=='adcs_suite':
                    result=run_adcs_suite(data.get('scenario','adcs_wheel_weak'),onset_s=data.get('onset_s',0),severity=data.get('severity',1.0))
                elif data.get('experiment')=='integrated':
                    result=run_integrated(scenario=data.get('scenario','adcs_gyro_bias'),policy=data.get('policy','information_gain'),
                        budget_min=data.get('budget_min',45),onset_s=data.get('onset_s',600),seed=data.get('seed',7),
                        severity=data.get('severity',1.0),eclipse=data.get('eclipse',False),initial_soc=data.get('initial_soc',.8))
                else:
                    result=run_active(scenario=data.get('scenario','resistance_ramp'),policy=data.get('policy','information_gain'),
                    budget_min=data.get('budget_min',35),onset_s=data.get('onset_s',600),seed=data.get('seed',7),
                    severity=data.get('severity',1.0),eclipse=data.get('eclipse',False),initial_soc=data.get('initial_soc',.8))
            elif self.path == '/api/forecast-v06':
                horizon=data.get('horizon_s',300)
                if horizon not in (120,300,600):
                    raise ValueError('Invalid forecast horizon')
                signal=data.get('signal','bus_voltage_v')
                if signal not in ('bus_voltage_v','temperature_c'):
                    raise ValueError('Invalid signal')
                sim=simulate_health(scenario=data.get('scenario','resistance_ramp'),
                    severity=data.get('severity',1.),onset_s=data.get('onset_s',480),
                    duration_s=data.get('duration_s',2400),step_s=30,
                    seed=data.get('seed',7),eclipse=data.get('eclipse',False),
                    initial_soc=data.get('initial_soc',.8),mode=data.get('mode','PAYLOAD'))
                result=forecast_trajectory(sim['telemetry'],_cached_forecasters(horizon),signal)
                result['scenario_meta']=sim['meta']
                result['telemetry']=sim['telemetry']
                result['notes']='Forecast warning is not a requirement failure. The website uses synthetic validation-calibrated forecast intervals.'
            elif self.path == '/api/v05':
                scenario=data.get('scenario','resistance_ramp')
                duration_s=data.get('duration_s',2400)
                sim=simulate_health(scenario=scenario,severity=data.get('severity',1.),
                   onset_s=data.get('onset_s',480),duration_s=duration_s,step_s=30,
                   seed=data.get('seed',7),eclipse=data.get('eclipse',False),
                   initial_soc=data.get('initial_soc',.8),mode=data.get('mode','NOMINAL'))
                ft=engineer_features(sim['telemetry'])
                detections=predict_methods(sim['telemetry'], _cached_models())
                verifications={}
                for policy in ('fixed','random','model_fixed','adaptive','scheduled_retest','temporal_blind','temporal_adaptive'):
                    c=run_verification_v05(policy,scenario,budget_min=data.get('budget_min',35),
                       severity=data.get('severity',1.),onset_s=data.get('onset_s',480),
                       seed=data.get('seed',7),eclipse=data.get('eclipse',False),
                       initial_soc=data.get('initial_soc',.8))
                    verifications[policy]={'detected':c['detected'],'detection_s':c['detection_s'],
                       'spent_s':c['spent_s'],'tests_run':c['tests_run'],'repeats':c['repeats'],
                       'evidence':[{'test_id':r.get('test_id','WAIT'),'status':r['status'],
                                    'checks':r.get('checks',{}),'start_s':r['start_s'],'end_s':r['end_s']}
                                   for r in c['evidence']]}
                result={'meta':sim['meta'],'telemetry':sim['telemetry'],'features':ft,
                     'detectors':{k:{'warning_times_s':v['warning_times_s'],
                         'flags':v['flags']} for k,v in detections.items()},
                     'verification':verifications,
                     'test_catalog':[{'id':t.id,'name':t.name,'cost_min':t.cost} for t in ALL_TESTS],
                     'notes':'Warnings are not formal failures; diagnostic truth is hidden from controllers.'}
            elif self.path == '/api/simulate':
                duration = data.get('duration_s', 3000)
                step = data.get('step_s', 30)
                if step <= 0 or duration / step > 1500:
                    raise ValueError('Browser preview limited to 1501 telemetry samples')
                result = run_scenario(**data)
            else:
                result = compare_temporal(**data) if self.path == '/api/compare-temporal' else compare_dynamic(**data)
            self._send(200, json.dumps(result, allow_nan=False).encode('utf-8'), 'application/json')
        except (ValueError, TypeError, OverflowError, json.JSONDecodeError) as exc:
            self._send(400, json.dumps({'error': str(exc)}).encode(), 'application/json')


def serve(port: int = 8765) -> None:
    if not 1024 <= port <= 65535:
        raise ValueError('Port must be in [1024, 65535]')
    httpd = ThreadingHTTPServer(('127.0.0.1', port), PreviewHandler)
    print(f'SAT-V&V interactive preview: http://127.0.0.1:{port}')
    print('Local-only server. Ctrl+C to stop.')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
