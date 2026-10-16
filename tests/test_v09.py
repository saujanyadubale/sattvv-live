import unittest
from satvv.learned_v09 import fit_failure_ranker,feature_row
from satvv.stress_v09 import make_stress_sim,STRESS_CASES,evaluate_stress,clustered_summary
from satvv.integrated_v08 import run_integrated,CATALOG
class StressTests(unittest.TestCase):
 def test_model_fitted(self):
  m=fit_failure_ranker()
  self.assertGreater(m.training_summary['samples'],100)
  self.assertEqual(m.n_features_in_,14)
 def test_deterministic_generator(self):
  x=make_stress_sim(STRESS_CASES[1],801)
  y=make_stress_sim(STRESS_CASES[1],801)
  self.assertEqual(x._episodes,y._episodes)
  self.assertTrue(len(x._episodes)>1)
 def test_learner_does_not_see_hidden_label(self):
  m=fit_failure_ranker()
  sim=make_stress_sim(STRESS_CASES[2],801)
  row=feature_row(sim.telemetry(),CATALOG[0])
  self.assertEqual(len(row),14)
  self.assertTrue(0<=m.predict_proba([row])[0,1]<=1)
 def test_learned_policy_replays(self):
  a=run_integrated('adcs_gyro_bias',policy='learned_risk',budget_min=20,seed=19)
  b=run_integrated('adcs_gyro_bias',policy='learned_risk',budget_min=20,seed=19)
  self.assertEqual(a,b)
 def test_evaluation_no_oracle_and_ci(self):
  r=evaluate_stress(seeds=(801,))
  self.assertEqual(len(r),len(STRESS_CASES)*4)
  s=clustered_summary(r,bootstraps=60)
  self.assertTrue(all(0<=v['ci95_low']<=v['rate']<=v['ci95_high']<=1 for v in s),s)

class PolicyIsolation(unittest.TestCase):
 def test_metadata_does_not_determine_policy_choice(self):
  from satvv.adcs_v08 import SpacecraftWithADCS
  a=run_integrated('healthy',policy='information_gain',budget_min=18,seed=21,
      _sim=SpacecraftWithADCS('sensor_drift',seed=21,onset_s=0))
  b=run_integrated('adcs_wheel_weak',policy='information_gain',budget_min=18,seed=21,
      _sim=SpacecraftWithADCS('sensor_drift',seed=21,onset_s=0))
  self.assertEqual(a['evidence'],b['evidence'])
