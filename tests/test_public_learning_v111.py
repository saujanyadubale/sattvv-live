"""Smoke tests for public, frozen SAT-V&V v1.1.1 comparison."""
import unittest
from satvv.public_learning_v111 import public_compare, public_status, _model

class PublicLearningTests(unittest.TestCase):
    def test_frozen_model_integrity(self):
        model,meta=_model()
        self.assertTrue(meta['validation_pass'])
        self.assertEqual(len(meta['feature_names']),14)
        self.assertTrue(public_status()['model_is_frozen'])
    def test_public_policy_and_input_guards(self):
        for value in ({'seed':'8'}, {'seed':True}, {'seed':1000001}, {'budget_min':91},
                      {'policies':['predictive_learned']}, {'continue_after_fail':True},
                      {'difficulty':'unknown'}, {'intensity':'unknown'}, {'seed':1.5}):
            with self.subTest(value=value), self.assertRaises(ValueError):public_compare(value)
    def test_formal_detection_and_evidence(self):
        r=public_compare({'seed':8,'budget_min':90,'difficulty':'mixed','intensity':'exploratory'})
        self.assertEqual([x['policy'] for x in r['runs']],['predictive_active','predictive_learned_soft_retest'])
        self.assertEqual(r['runs'][0]['first_failure_min'],81)
        self.assertTrue(all(x['audit_passed'] for x in r['runs']))
        self.assertTrue(all(x['test_history'] for x in r['runs']))
        self.assertNotIn('training_rows',str(r))
if __name__=='__main__':unittest.main()
