import unittest
from satvv.challenge_v096 import generate
class V098(unittest.TestCase):
 def test_original_seed_stable(self):
  self.assertEqual(generate('mixed',7,90).oracle()['faults'][0]['mechanism'],'sensor_drift')
 def test_high_impact_seed_and_two_faults(self):
  a=generate('mixed',7,90,'high_impact');self.assertEqual(a,generate('mixed',7,90,'high_impact'));self.assertEqual(a.oracle()['fault_count'],2);self.assertTrue(all(f['severity']>=1.45 for f in a.oracle()['faults']))
 def test_control_remains_healthy(self):
  self.assertTrue(generate('control',7,90,'high_impact').oracle()['healthy'])
 def test_invalid_profile(self):
  with self.assertRaises(ValueError):generate('mixed',7,90,'invalid')
