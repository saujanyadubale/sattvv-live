"""v0.9.3 gates: causal closed loop, safety, evidence, and browser contracts."""
import json,threading,unittest
from http.server import ThreadingHTTPServer
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from satvv.pipeline_v093 import run_pipeline,audit_evidence
from satvv.web_server import PreviewHandler

class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.standard=run_pipeline('resistance_ramp',budget_min=15,onset_s=300)
    def test_all_five_stages(self):
        self.assertEqual(set(self.standard['stages']),{'detection','forecasting','diagnosis','verification','audit'})
    def test_only_executed_checks_fail(self):
        self.assertEqual(self.standard['detected'],any(x['status']=='FAIL' for x in self.standard['evidence']))
        self.assertIsInstance(self.standard['forecast_risk_seen'],bool)
    def test_audit_valid(self):
        self.assertTrue(self.standard['audit']['passed'])
        self.assertFalse(self.standard['audit']['problems'])
    def test_hidden_fault_not_in_decisions(self):
        for r in self.standard['evidence']:
            self.assertNotIn('fault_label',r['decision'])
            self.assertNotIn('scenario',r['decision'])
            self.assertNotIn('fault_type',r['decision'])
    def test_monitor_and_forecast_outputs(self):
        forecasts=self.standard['last_forecast']
        self.assertIn('bus_voltage_v',forecasts)
        self.assertIn('temperature_c',forecasts)
        self.assertIn('lower',forecasts['bus_voltage_v'])
    def test_repeatability(self):
        second=run_pipeline('resistance_ramp',budget_min=15,onset_s=300)
        self.assertEqual([(x['test_id'],x['status']) for x in second['evidence']],
                         [(x['test_id'],x['status']) for x in self.standard['evidence']])
    def test_audit_detects_false_pass(self):
        from copy import deepcopy
        evidence=deepcopy(self.standard['evidence'])
        evidence[0]['status']='INVALID'
        self.assertFalse(audit_evidence(evidence,15)['passed'])
    def test_safety_exclusion_on_low_charge(self):
        r=run_pipeline('healthy',budget_min=12,initial_soc=.1,onset_s=0)
        self.assertTrue(r['audit']['passed'])
        self.assertTrue(all(x['test_id'] not in ('T07','T13','T14') for x in r['evidence']))
    def test_horizon_parameter_affects_forecast(self):
        r=run_pipeline('heater_fault',budget_min=10,horizon_s=120,onset_s=0)
        self.assertEqual(r['meta']['horizon_s'],120)
    def test_reject_bad_inputs(self):
        for params in ({'policy':'bad'},{'scenario':'bad'},{'horizon_s':200},{'initial_soc':1.5},
                       {'budget_min':91},{'detector':'bad'},{'seed':'7'}):
            with self.subTest(params=params),self.assertRaises(ValueError):run_pipeline(**params)
    def test_fixed_and_predictive_use_catalog(self):
        fixed=run_pipeline('healthy',policy='fixed',budget_min=8)
        self.assertEqual(fixed['evidence'][0]['test_id'],'T01')
        self.assertTrue(all(x['test_id'].startswith('T') for x in fixed['evidence']))
    def test_compound_stress_supported(self):
        stress=run_pipeline('dual_resistance_sensor',budget_min=12,seed=801)
        self.assertTrue(stress['meta']['randomized_stress_environment'])
        self.assertTrue(stress['audit']['passed'])

class PipelineApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),PreviewHandler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.thread.join(timeout=3);cls.server.server_close()
    def post(self,body):
        req=Request(self.url+'/api/lab-run',data=json.dumps(body).encode(),
                    headers={'Content-Type':'application/json'},method='POST')
        with urlopen(req,timeout=45) as r:return json.load(r)
    def test_integrated_api(self):
        x=self.post({'scenario':'sensor_drift','policy':'predictive_active','budget_min':10,
                     'horizon_s':300,'detector':'trend'})
        self.assertEqual(x['meta']['version'],'0.9.4')
        self.assertTrue(x['audit']['passed'])
    def test_validation_is_400(self):
        with self.assertRaises(HTTPError) as e:self.post({'scenario':'invented'})
        self.assertEqual(e.exception.code,400)
    def test_html_has_predictive_option(self):
        with urlopen(self.url+'/lab.js') as r:
            self.assertIn('predictive_active',r.read().decode())
