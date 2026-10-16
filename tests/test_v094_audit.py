"""v0.9.4 policy and numeric evidence regression tests."""
import copy
import unittest
from satvv.pipeline_v093 import run_pipeline
from satvv.evidence_v094 import audit_trace, evaluate_bound

class V094Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.battery=run_pipeline('resistance_ramp',policy='learned_risk',
            onset_s=300,budget_min=26,seed=7,severity=2.0,initial_soc=1.)
    def test_policy_matches_each_record(self):
        r=self.battery
        self.assertEqual(r['meta']['policy'],r['display_policy'])
        self.assertTrue(all(x['decision']['selected_policy']=='learned_risk' for x in r['evidence']))
        self.assertTrue(r['audit']['provenance']['passed'])
    def test_v094_identifies_t14_failure(self):
        t=self.battery['evidence'][-1]
        self.assertEqual(t['test_id'],'T14')
        self.assertEqual(t['status'],'FAIL')
        self.assertFalse(t['checks']['REQ-EPS-R'])
        self.assertFalse(t['checks']['REQ-EPS-REC'])
        self.assertGreater(t['check_details']['REQ-EPS-R']['measured'],.26)
        self.assertGreater(t['check_details']['REQ-EPS-REC']['measured'],.18)
    def test_wrong_policy_is_flagged(self):
        e=copy.deepcopy(self.battery['evidence'])
        e[0]['decision']['selected_policy']='predictive_active'
        a=audit_trace(e,'learned_risk',26)
        self.assertFalse(a['passed'])
        self.assertIn('policy provenance mismatch',' '.join(a['problems']))
    def test_wrong_reason_is_flagged(self):
        e=copy.deepcopy(self.battery['evidence'])
        e[0]['decision']['reason']='Information gain'
        self.assertFalse(audit_trace(e,'learned_risk',26)['passed'])
    def test_changed_measurement_without_status_is_flagged(self):
        e=copy.deepcopy(self.battery['evidence'])
        t=e[-1]['check_details']['REQ-EPS-R']
        t['measured']=0.01
        self.assertFalse(audit_trace(e,'learned_risk',26)['passed'])
    def test_observation_must_precede_execution(self):
        e=copy.deepcopy(self.battery['evidence'])
        e[0]['decision']['observation_time_s']=e[0]['end_s']
        self.assertFalse(audit_trace(e,'learned_risk',26)['passed'])
    def test_healthy_control(self):
        r=run_pipeline('healthy',policy='learned_risk',budget_min=12,onset_s=300)
        self.assertFalse(r['detected'])
        self.assertTrue(r['audit']['passed'])
    def test_bound_exact_equality(self):
        self.assertTrue(evaluate_bound(dict(measured=.26,threshold=.26,operator='<=',unit='V')))
        self.assertFalse(evaluate_bound(dict(measured=.27,threshold=.26,operator='<=',unit='V')))
    def test_forecasts_alone_cannot_cause_fail(self):
        self.assertEqual(self.battery['detected'],any(x['status']=='FAIL' for x in self.battery['evidence']))
        self.assertTrue(self.battery['audit']['passed'])
    def test_reproducible_numerical_evidence(self):
        a=self.battery
        b=run_pipeline('resistance_ramp',policy='learned_risk',
            onset_s=300,budget_min=26,seed=7,severity=2.0,initial_soc=1.)
        self.assertEqual(a['evidence'],b['evidence'])

if __name__=='__main__':unittest.main()
