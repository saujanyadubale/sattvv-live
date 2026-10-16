import unittest
from satvv.core import Fault, TESTS, REQUIREMENTS, SpacecraftEmulator
from satvv.campaign import run_campaign
from satvv.experiment import FAULTS


class SatVVTests(unittest.TestCase):
    def test_catalog_references_real_requirements(self):
        self.assertEqual(len(TESTS), 12)
        for test in TESTS:
            self.assertTrue(set(test.checks).issubset(REQUIREMENTS))

    def test_no_fault_passes_all_tests(self):
        for test in TESTS:
            obs = SpacecraftEmulator(Fault.NONE, 7).execute(test)
            self.assertFalse(obs.detected, f'False alarm in {test.id}')

    def test_every_fault_detectable_by_some_test(self):
        for fault in FAULTS:
            self.assertTrue(any(SpacecraftEmulator(fault, 7).execute(t).detected for t in TESTS),
                            f'Unobservable fault: {fault}')

    def test_budget_never_exceeded(self):
        for strategy in ('fixed', 'random', 'model_fixed', 'adaptive'):
            for budget in (1, 5, 12, 20, 33):
                for fault in Fault:
                    result = run_campaign(strategy, fault, budget, seed=11)
                    self.assertLessEqual(result.spent, budget)

    def test_precursor_changes_adaptive_test_order(self):
        # No privileged fault info: a near-limit voltage reading prioritizes EPS.
        adaptive = run_campaign('adaptive', Fault.UNDERVOLTAGE, 12, 7)
        planned = run_campaign('model_fixed', Fault.UNDERVOLTAGE, 12, 7)
        self.assertEqual(adaptive.evidence[1]['test_id'], 'T03')
        self.assertNotEqual(adaptive.evidence[1]['test_id'], planned.evidence[1]['test_id'])

    def test_reproducibility(self):
        a = run_campaign('random', Fault.PACKET_LOSS, 16, 123)
        b = run_campaign('random', Fault.PACKET_LOSS, 16, 123)
        self.assertEqual(a.__dict__, b.__dict__)

    def test_healthy_no_false_detection(self):
        for policy in ('fixed', 'random', 'model_fixed', 'adaptive'):
            self.assertFalse(run_campaign(policy, Fault.NONE, 33, 3).detected)

    def test_test_case_independence(self):
        a = SpacecraftEmulator(Fault.NONE, 41).execute(TESTS[1])
        b = SpacecraftEmulator(Fault.NONE, 41).execute(TESTS[1])
        self.assertEqual(a.results, b.results)


if __name__ == '__main__':
    unittest.main()
