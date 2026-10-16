import unittest
from satvv.integrated_v08 import fit_response_table, run_integrated, CATALOG,CAUSES
class Integrated(unittest.TestCase):
 def test_count_likelihood(self):
  self.assertEqual(len(CATALOG),20)
  table=fit_response_table()
  self.assertEqual(len(table),20*len(CAUSES))
  self.assertTrue(all(0<x<1 for x in table.values()))
 def test_hidden_fault_not_decision(self):
  a=run_integrated('adcs_gyro_bias',policy='information_gain',budget_min=30,onset_s=0)
  self.assertTrue(a['tests_run']>0)
  self.assertNotIn('adcs_gyro_bias',str([x['decision'] for x in a['evidence']]))
  self.assertLessEqual(a['spent_s'],1800)
 def test_seed_replay(self):
  self.assertEqual(run_integrated('healthy',budget_min=20,seed=13),run_integrated('healthy',budget_min=20,seed=13))
 def test_policies(self):
  for p in ('fixed','temporal_adaptive','information_gain'):
   a=run_integrated('adcs_gyro_bias',policy=p,budget_min=45,onset_s=0)
   self.assertTrue(a['evidence'])
   self.assertTrue(all('test_id' in rec for rec in a['evidence']))
