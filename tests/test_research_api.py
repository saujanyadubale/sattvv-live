"""Browser controls and response schemas for the v0.7–0.9 research lab."""
import json,threading,unittest
from http.server import ThreadingHTTPServer
from urllib.request import urlopen,Request
from urllib.error import HTTPError
from satvv.web_server import PreviewHandler
class ResearchAPI(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.server=ThreadingHTTPServer(('127.0.0.1',0),PreviewHandler)
  cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
  cls.url=f'http://127.0.0.1:{cls.server.server_port}'
 @classmethod
 def tearDownClass(cls):
  cls.server.shutdown();cls.thread.join(timeout=2);cls.server.server_close()
 def post(self,payload):
  req=Request(self.url+'/api/research',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
  with urlopen(req,timeout=20) as resp:return json.loads(resp.read())
 def test_browser_contains_research(self):
  with urlopen(self.url+'/legacy') as resp:
   body=resp.read().decode()
   self.assertIn('advancedScreen',body)
   self.assertIn('stress',body)
 def test_active_api(self):
  d=self.post({'experiment':'active','scenario':'sensor_drift','budget_min':20,'seed':7})
  self.assertEqual(d['meta']['version'],'0.7');self.assertTrue(d['evidence'])
 def test_integrated_api(self):
  d=self.post({'experiment':'integrated','scenario':'adcs_gyro_bias','budget_min':20,'seed':7})
  self.assertEqual(d['meta']['version'],'0.8')
 def test_frontend_stress_menus_are_defined(self):
  with urlopen(self.url+'/legacy') as resp:body=resp.read().decode()
  self.assertIn('function updateResearchControls()',body)
  self.assertIn("scenarios: ['healthy_eclipse_and_load','dual_resistance_sensor','heater_plus_radio'",body)
  self.assertIn("updateResearchControls();",body)
  self.assertIn('policySelect.disabled=true',body)
 def test_stress_custom_onset_is_applied(self):
  d=self.post({'experiment':'stress','scenario':'dual_resistance_sensor','policy':'fixed','budget_min':20,'seed':801,'onset_s':120})
  self.assertEqual(d['meta']['onset_s'],120)
  self.assertEqual(d['meta']['stress_case'],'dual_resistance_sensor')
 def test_all_stress_scenarios_accepted(self):
  from satvv.stress_v09 import STRESS_CASES
  for case in STRESS_CASES:
   with self.subTest(case=case.name):
    d=self.post({'experiment':'stress','scenario':case.name,'policy':'fixed','budget_min':5,'seed':801})
    self.assertEqual(d['meta']['stress_case'],case.name)
 def test_stress_api(self):
  d=self.post({'experiment':'stress','scenario':'dual_resistance_sensor','budget_min':20,'seed':801})
  self.assertEqual(d['meta']['stress_case'],'dual_resistance_sensor')
 def test_adcs_api(self):
  d=self.post({'experiment':'adcs_suite','scenario':'adcs_gyro_bias','onset_s':0})
  self.assertEqual(len(d['procedures']),4)
 def test_invalid_policy_and_scenario(self):
  for req in ({'experiment':'active','policy':'not-a-policy'},
              {'experiment':'stress','scenario':'invalid'},
              {'experiment':'integrated','policy':'coverage'}):
   with self.assertRaises(HTTPError) as e:self.post(req)
   self.assertEqual(e.exception.code,400)
