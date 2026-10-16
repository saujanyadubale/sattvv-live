"""v1.0.1 regression gates for observable-only anti-starvation safeguards."""
import unittest
from satvv.coverage_v101 import choose_with_guard,adcs_observable_risk
from satvv.integrated_v08 import CATALOG
from satvv.challenge_v096 import run_challenge

class CoverageGuardTests(unittest.TestCase):
    def test_repeat_starvation_forces_distinct_test(self):
        safe=[CATALOG[0],CATALOG[4],CATALOG[16]]
        t,reason=choose_with_guard(safe,lambda c:100 if c.id=='T01' else 1,
                                    {'T01':3,'T05':2},repeat_streak=2,remaining_min=12)
        self.assertEqual(t.id,'T17')
        self.assertEqual(reason,'repeat_streak_limit')

    def test_reserve_untried_budget(self):
        safe=[CATALOG[0],CATALOG[16]]
        t,reason=choose_with_guard(safe,lambda c:100 if c.id=='T01' else 1,
                                    {'T01':1},repeat_streak=0,remaining_min=5)
        self.assertEqual((t.id,reason),('T17','coverage_budget_reserve'))

    def test_no_unsafe_or_unaffordable_override(self):
        safe=[CATALOG[0],CATALOG[4]]
        t,_=choose_with_guard(safe,lambda c:100 if c.id=='T01' else 1,
                              {'T01':3,'T05':1},repeat_streak=10,remaining_min=10)
        self.assertIn(t,safe)

    def test_observable_adcs_signal_not_fault_label(self):
        healthy={'theta_deg':0.,'target_deg':0.,'omega_rads':0.,'gyro_rads':0.,
                 'star_rate_rads':0.,'momentum_nms':0.,'star_available':True}
        self.assertEqual(adcs_observable_risk(healthy),0.)
        self.assertGreater(adcs_observable_risk({**healthy,'theta_deg':8.}),0.)
        self.assertGreater(adcs_observable_risk({**healthy,'star_available':False}),0.)

    @classmethod
    def setUpClass(cls):
        cls.fixed=run_challenge('mixed',8,90,'fixed')
        cls.predictive=run_challenge('mixed',8,90,'predictive_greedy_v101')

    def test_regression_seed8_has_real_verified_failure(self):
        r=self.predictive
        self.assertTrue(r['detected'])
        self.assertIn(r['evidence'][-1]['test_id'],('T17','T18','T20'))
        self.assertEqual(r['evidence'][-1]['status'],'FAIL')
        self.assertTrue(r['audit']['passed'])
        self.assertLessEqual(r['detection_s'],90*60)
        self.assertGreater(r['stages']['verification']['distinct_procedures'],11)
        self.assertGreater(r['stages']['verification']['coverage_guard_overrides'],0)

    def test_oracle_never_in_policy_decision(self):
        for event in self.predictive['evidence']:
            d=event['decision']
            self.assertNotIn('fault',d)
            self.assertNotIn('scenario',d)
            self.assertIn(d['coverage_guard'],('adaptive_score','repeat_streak_limit','coverage_budget_reserve'))

    def test_paired_baseline_unchanged(self):
        self.assertTrue(self.fixed['detected'])
        self.assertEqual(self.fixed['detection_s'],3480.)

    def test_repeatability(self):
        again=run_challenge('mixed',8,90,'predictive_greedy_v101')
        self.assertEqual([(x['test_id'],x['status']) for x in again['evidence']],
                         [(x['test_id'],x['status']) for x in self.predictive['evidence']])

if __name__=='__main__':unittest.main()
