import unittest
from satvv.active_v07 import HYPOTHESES,entropy,information_gain,update_belief,calibrated_likelihoods,run_active
class ActiveTests(unittest.TestCase):
    def test_information(self):
        p={h:1/len(HYPOTHESES) for h in HYPOTHESES}
        self.assertAlmostEqual(information_gain(p,{h:.5 for h in HYPOTHESES}),0)
        q=update_belief(p,{h:(.9 if h=='sensor_drift' else .1) for h in HYPOTHESES},True)
        self.assertGreater(q['sensor_drift'],p['sensor_drift'])
        self.assertAlmostEqual(sum(q.values()),1)
    def test_calibration_valid(self):
        x=calibrated_likelihoods()
        self.assertEqual(len(x),6*16)
        self.assertTrue(all(0<v<1 for v in x.values()))
    def test_no_fault_label_in_evidence(self):
        a=run_active('sensor_drift',budget_min=16,seed=78)
        self.assertTrue(a['evidence'])
        self.assertTrue(all('scenario' not in str(r['decision']) for r in a['evidence']))
        self.assertEqual(a['spent_s']%60,0)
    def test_reproducible(self):
        a=run_active('resistance_ramp',budget_min=20,seed=4)
        b=run_active('resistance_ramp',budget_min=20,seed=4)
        self.assertEqual(a,b)
    def test_reject_invalid(self):
        with self.assertRaises(ValueError):run_active('invented')
        with self.assertRaises(ValueError):run_active(budget_min=-2)
