"""v1.0.2 risk-aware planner gates: no oracle, resource safety, reproducibility."""
import unittest
from satvv.planner_v102 import ranked_plan
from satvv.integrated_v08 import CATALOG,CAUSES
from satvv.challenge_v096 import run_challenge
from satvv.pipeline_v093 import run_pipeline

class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.belief={h:1/len(CAUSES) for h in CAUSES}
        self.safe=CATALOG[:]

    def choose(self,**kw):
        opts=dict(time_s=1200,remaining_min=25,warning_weights={},risk={},adcs_risk=0.)
        opts.update(kw)
        return ranked_plan(self.safe,self.belief,set(),{}, {},**opts)

    def test_deterministic_and_cost_safe(self):
        a=self.choose();b=self.choose()
        self.assertEqual(a,b)
        self.assertGreaterEqual(len(a.sequence),1)
        self.assertLessEqual(len(a.sequence),3)
        by={t.id:t for t in self.safe}
        self.assertLessEqual(sum(by[x].cost for x in a.sequence),25)
        self.assertEqual(len(a.sequence),len(set(a.sequence)))

    def test_does_not_choose_excluded_tests(self):
        safe=[t for t in self.safe if t.id not in ('T07','T13','T14')]
        plan=ranked_plan(safe,self.belief,set(),{}, {},time_s=0,remaining_min=25,
                         warning_weights={},risk={})
        self.assertNotIn(plan.test.id,('T07','T13','T14'))
        self.assertNotIn('T07',plan.sequence)

    def test_cannot_overrun_budget(self):
        for budget in (1,3,5,10):
            affordable=[t for t in self.safe if t.cost<=budget]
            p=ranked_plan(affordable,self.belief,set(),{}, {},time_s=0,
                           remaining_min=budget,warning_weights={},risk={})
            by={t.id:t for t in affordable}
            self.assertLessEqual(sum(by[x].cost for x in p.sequence),budget)

    def test_no_hidden_truth_in_decisions(self):
        p=self.choose()
        self.assertFalse(hasattr(p,'oracle'))
        result=run_challenge('mixed',8,90,'predictive_active')
        self.assertTrue(result['audit']['passed'])
        self.assertTrue(result['detected'])
        for e in result['evidence']:
            d=e['decision']
            self.assertEqual(d['selected_policy'],'predictive_active')
            self.assertIn('planned_sequence',d)
            self.assertEqual(d['planned_sequence'][0],e['test_id'])
            self.assertNotIn('scenario',d)
            self.assertNotIn('injected_fault',d)
            self.assertIn('no future physics',d['plan_assumptions'])

    def test_healthy_control_no_formal_failure(self):
        r=run_challenge('control',7,25,'predictive_active')
        self.assertFalse(r['detected'])
        self.assertTrue(r['audit']['passed'])

    def test_original_greedy_policy_retained(self):
        old=run_challenge('mixed',8,90,'predictive_greedy_v101')
        self.assertEqual(old['detection_s'],4560.)
        self.assertTrue(old['audit']['passed'])

    def test_short_budget_preserves_radio_burst_detection(self):
        r=run_pipeline('radio_burst',policy='predictive_active',onset_s=600,budget_min=25)
        self.assertTrue(r['detected'])
        self.assertTrue(r['audit']['passed'])
        self.assertTrue(all(e['decision']['scheduler_mode']=='short_budget_greedy_fallback'
                            for e in r['evidence']))
        self.assertTrue(all('planned_sequence' not in e['decision'] for e in r['evidence']))

    def test_long_budget_planning_metadata_and_audit(self):
        r=run_challenge('mixed',5,90,'predictive_active')
        self.assertTrue(r['audit']['passed'])
        self.assertGreater(r['tests_run'],0)
        for e in r['evidence']:
            d=e['decision']
            self.assertEqual(d['scheduler_mode'],'bounded_receding_horizon')
            self.assertGreater(d['candidate_sequences_evaluated'],0)
            self.assertEqual(d['planned_sequence'][0],e['test_id'])
            self.assertLessEqual(len(d['planned_sequence']),3)

    def test_observable_only_metadata_reproducible(self):
        a=run_pipeline('adcs_wheel_weak',policy='predictive_active',seed=9,budget_min=25)
        b=run_pipeline('adcs_wheel_weak',policy='predictive_active',seed=9,budget_min=25)
        self.assertEqual(a['decision_history'],b['decision_history'])
        self.assertTrue(a['audit']['passed'])

if __name__=='__main__':unittest.main()
