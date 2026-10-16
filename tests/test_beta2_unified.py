"""Regression coverage for beta.2's integrated configuration and explainability.

No hidden truth enters the early-warning / advisory layer.
"""
import json, threading, unittest
from urllib.request import urlopen,Request
from http.server import ThreadingHTTPServer
from satvv.web_server import PreviewHandler
from satvv.insights_v11 import analyse


def sample(t,offset):
    return {'time_s':t,'temperature_c':25.+offset,'redundant_temperature_c':25.,
       'bus_voltage_v':7.65,'battery_soc_pct':80.,'load_w':8.,
       'packet_loss_fraction':0.,'mode':'NOMINAL'}

class InsightTests(unittest.TestCase):
    def test_weak_sensor_drift_warns_without_automatic_failure(self):
        rows=[sample(t,1.35) for t in (0,30,60,90)]
        result=analyse(rows,[])
        self.assertEqual(result['status'],'early_warning')
        self.assertTrue(any(a['kind']=='thermal' for a in result['warning_events']))
        self.assertEqual(result['failed_checks'],[])
        self.assertIn('T11',result['recommended_next_check'])
    def test_no_false_sensor_warning_for_small_noise(self):
        rows=[sample(t,.03 if i%2 else -.04) for i,t in enumerate(range(0,180,30))]
        self.assertFalse(any(a['kind']=='thermal' for a in analyse(rows,[])['warning_events']))
    def test_single_spike_debounced(self):
        rows=[sample(t,2 if t==60 else 0) for t in (0,30,60,90,120)]
        self.assertFalse(any(a['kind']=='thermal' for a in analyse(rows,[])['warning_events']))
    def test_results_do_not_depend_on_hidden_truth(self):
        evidence=[{'test_id':'T11','subsystem':'THERMAL','checks':{'REQ-THM-D':True},'status':'PASS','end_s':90}]
        a=analyse([sample(t,1.4) for t in (0,30,60,90)],evidence)
        self.assertEqual(a['failed_checks'],[])
        self.assertEqual(a['status'],'early_warning')
        self.assertIn('advisory',a['limitations'].lower()) if 'advisory' in a['limitations'].lower() else self.assertIn('mitigation',a['limitations'].lower())
    def test_known_failed_requirement_is_not_blurred_by_warning(self):
        r=analyse([sample(t,1.7) for t in (0,30,60)],
          [{'test_id':'T11','subsystem':'THERMAL','checks':{'REQ-THM-D':False},'status':'FAIL','end_s':60}])
        self.assertEqual(r['status'],'verified_failure')
        self.assertIn('review',r['possible_mitigation_for_review'].lower())

class UnifiedApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),PreviewHandler)
        cls.t=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.t.start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_port)
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.t.join(timeout=3);cls.server.server_close()
    def get(self,path):
        with urlopen(self.base+path) as r:return r.read().decode()
    def post(self,data):
        body=json.dumps(data).encode()
        with urlopen(Request(self.base+'/api/unified',body,{'Content-Type':'application/json'})) as r:return json.load(r)
    def test_main_entry_is_unified(self):
        page=self.get('/')
        for text in ['experimentMode','manualControls','randomControls','chartMode','interpretPanel','actionAdvice','missionCanvas']:
            self.assertIn(text,page)
        self.assertIn('id="experiment"',self.get('/classic'))
        self.assertEqual(self.get('/'),self.get('/challenge'))
    def test_manual_and_random_share_result_contract(self):
        for data in [
            {'mode':'manual','scenario':'sensor_drift','seed':9,'budget_min':15,'onset_s':300,'severity':1.5,'policy':'fixed'},
            {'mode':'random','difficulty':'single','intensity':'high_impact','seed':9,'budget_min':15,'policy':'fixed'}]:
            r=self.post(data)
            self.assertIn('insights_v11',r)
            self.assertTrue(r['insights_v11']['evidence_scope'].startswith('computed only'))
            self.assertEqual(r['meta']['version'],'1.0.0')
            self.assertTrue(isinstance(r['evidence'],list))
            self.assertEqual(r['meta']['experiment_mode'],data['mode'])
    def test_reject_cross_mode_parameters(self):
        from urllib.error import HTTPError
        with self.assertRaises(HTTPError) as caught:
            self.post({'mode':'random','scenario':'sensor_drift'})
        self.assertEqual(caught.exception.code,400)
    def test_advice_has_no_control_action(self):
        data={'mode':'manual','scenario':'healthy','budget_min':15,'seed':2,'policy':'fixed'}
        r=self.post(data)
        self.assertIn('insights_v11',r)
        self.assertNotIn('executed_mitigation',r)

if __name__=='__main__':unittest.main()
