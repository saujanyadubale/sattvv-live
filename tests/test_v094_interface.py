"""Source-level assertions for v0.9.4 browser contract (no external browser dependency)."""
import unittest
from pathlib import Path
from satvv.pipeline_v093 import run_pipeline

ROOT=Path(__file__).resolve().parent.parent

class InterfaceTests(unittest.TestCase):
    def test_browser_labels_match_payload_contract(self):
        js=(ROOT/'web/lab.js').read_text()
        html=(ROOT/'web/index.html').read_text()
        self.assertIn("result.meta?.policy!==policy",js)
        self.assertIn("data.meta?.policy!==s.policy",js)
        self.assertIn('function renderEvidence',js)
        self.assertIn('function invalidateResults',js)
        self.assertIn('id="runContext"',html)
        self.assertIn('id="evidenceRaw"',html)
    def test_run_policy_is_returned_not_guessed_from_screen(self):
        # This also checks a different policy from the screenshot example.
        r=run_pipeline('healthy',policy='fixed',budget_min=8)
        self.assertEqual('fixed',r['meta']['policy'])
        self.assertEqual('fixed',r['display_policy'])
        self.assertTrue(all(e['decision']['selected_policy']=='fixed' for e in r['evidence']))

if __name__=='__main__':unittest.main()
