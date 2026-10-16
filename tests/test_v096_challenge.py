"""v0.9.6 regression and security tests for random challenges + evidence updates."""
import json,threading,unittest
from copy import deepcopy
from http.server import ThreadingHTTPServer
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from satvv.challenge_v096 import generate,make_sim,run_challenge,DIFFICULTIES
from satvv.diagnosis_v096 import update_requirements,expected_information
from satvv.pipeline_v093 import run_pipeline
from satvv.evidence_v094 import audit_trace
from satvv.web_server import PreviewHandler

class V096Physics(unittest.TestCase):
    def test_reproducible_generated_cases(self):
        for kind in DIFFICULTIES:
            self.assertEqual(generate(kind,91,30),generate(kind,91,30))
    def test_challenge_complexity(self):
        for kind in DIFFICULTIES:
            for seed in range(10):
                f=generate(kind,seed,30)
                c=len({x['mechanism'] for x in f.oracle()['faults']})
                if kind=='control':self.assertEqual(c,0)
                if kind=='single':self.assertEqual(c,1)
                if kind=='mixed':self.assertIn(c,(1,2))
                if kind=='stress':self.assertIn(c,(2,3))
    def test_reject_inputs(self):
        for kw in ({'difficulty':'ultra'},{'seed':-1},{'budget_min':10},{'seed':'7'},
                   {'budget_min':91},{'seed':True}):
            with self.subTest(kw=kw),self.assertRaises(ValueError):generate(**kw)
    def test_hidden_labels_not_in_telemetry(self):
        spec=generate('stress',20,30);sim=make_sim(spec)
        for k in ('faults','mechanism','fault_label','oracle'):
            self.assertNotIn(k,sim.telemetry())
    def test_result_audited_and_oracle_separate(self):
        r=run_challenge('mixed',7,25,'predictive_active')
        self.assertTrue(r['audit']['passed'])
        self.assertEqual(r['meta']['version'],'0.9.8')
        self.assertIn('oracle_after_run',r)
        for e in r['evidence']:
            for field in ('oracle','mechanism','fault_label','scenario'):
                self.assertNotIn(field,e['decision'])
    def test_fair_identical_hidden_conditions_per_policy(self):
        a=run_challenge('stress',11,20,'fixed')
        b=run_challenge('stress',11,20,'predictive_active')
        self.assertEqual(a['oracle_after_run'],b['oracle_after_run'])
        self.assertEqual(a['meta']['generated_environment'],b['meta']['generated_environment'])
    def test_healthy_control_no_fault(self):
        a=run_challenge('control',7,25,'predictive_active')
        self.assertFalse(a['oracle_after_run']['faults'])
        self.assertFalse(a['detected'])
    def test_comms_requirement_updates_correct_hypothesis(self):
        pri={h:1/9 for h in ('healthy','resistance_ramp','intermittent_resistance',
             'sensor_drift','heater_fault','radio_burst','adcs_wheel_weak','adcs_gyro_bias','adcs_star_dropout')}
        after=update_requirements(pri,{'REQ-COM-L':False,'REQ-COM-T':True,'REQ-COM-C':True})
        self.assertEqual(max(after,key=after.get),'radio_burst')
        self.assertGreater(after['radio_burst'],after['healthy'])
        self.assertGreater(expected_information(pri,('REQ-COM-L',)),0.)
    def test_actual_radio_burst_in_test_window(self):
        r=run_pipeline('radio_burst',policy='predictive_active',onset_s=600,budget_min=25)
        self.assertTrue(r['detected'])
        self.assertEqual(r['estimated_cause'],'radio_burst')
        self.assertGreater(len(r['monitor_events']),0)
        self.assertTrue(r['audit']['passed'])
        for event in r['monitor_events']:
            self.assertGreaterEqual(event['time_s'],600)
    def test_reject_tampered_comms_window(self):
        r=run_pipeline('radio_burst',policy='predictive_active',onset_s=600,budget_min=25)
        bad=deepcopy(r['evidence'])
        link=next(x for x in bad if x.get('communication_window'))
        link['communication_window']['sample_end_s']=99999
        self.assertFalse(audit_trace(bad,'predictive_active',25)['passed'])
    def test_interval_consistency_across_episodes(self):
        for seed in range(10):
            f=generate('stress',seed,30)
            for ep in f.episodes:self.assertLess(ep.start_s,ep.end_s)

class V096API(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),PreviewHandler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.thread.join(timeout=3);cls.server.server_close()
    def test_random_challenge_api(self):
        request=Request(self.url+'/api/challenge',data=json.dumps({'difficulty':'mixed','seed':7,'budget_min':25,'policy':'fixed'}).encode(),headers={'Content-Type':'application/json'})
        with urlopen(request,timeout=80) as reply:r=json.load(reply)
        self.assertEqual(r['meta']['version'],'0.9.8')
        self.assertEqual(r['display_policy'],'fixed')
        self.assertTrue(r['audit']['passed'])
    def test_bad_challenge_error(self):
        request=Request(self.url+'/api/challenge',data=b'{"difficulty":"invented"}',headers={'Content-Type':'application/json'})
        with self.assertRaises(HTTPError) as e:urlopen(request,timeout=20)
        self.assertEqual(e.exception.code,400)
    def test_website_routes_and_version(self):
        for path,needed in (('/challenge','id="replayPanel"'),('/challenge.js','stepTo'),('/','/challenge')):
            with urlopen(self.url+path) as response:
                self.assertIn(needed,response.read().decode())
        with urlopen(self.url+'/api/health') as response:
            self.assertEqual(json.load(response)['version'],'1.0.0')

if __name__=='__main__':unittest.main()
