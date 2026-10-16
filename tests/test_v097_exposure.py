"""v0.9.7 honest challenge interpretation and new website integrity checks."""
import unittest
from pathlib import Path
from satvv.challenge_v096 import generate,assess_exposure,run_challenge

ROOT=Path(__file__).resolve().parents[1]
class ExposureTests(unittest.TestCase):
    def test_seed7_late_sensor_drift_is_not_healthy(self):
        spec=generate('mixed',7,90)
        self.assertEqual(len(spec.oracle()['faults']),1)
        self.assertEqual(spec.oracle()['faults'][0]['mechanism'],'sensor_drift')
        self.assertEqual(spec.oracle()['faults'][0]['onset_s'],4580)
    def test_fault_exposure_does_not_imply_failure(self):
        report=assess_exposure({'evidence':[{'test_id':'T11','start_s':4860,'end_s':5040,'status':'PASS'}]},
            {'faults':[{'mechanism':'sensor_drift','onset_s':4580,'end_s':4930,'severity':.482}], 'healthy':False})
        self.assertEqual(report['fault_exposures'][0]['overlapping_checks'][0]['result'],'PASS')
        self.assertTrue(report['not_a_detectability_proof'])
    def test_nonoverlap_is_explicit(self):
        report=assess_exposure({'evidence':[{'test_id':'T11','start_s':5000,'end_s':5200,'status':'PASS'}]},
            {'faults':[{'mechanism':'sensor_drift','onset_s':4580,'end_s':4930,'severity':.482}],'healthy':False})
        self.assertEqual(report['fault_exposures'][0]['overlapping_checks'],[])
    def test_full_challenge_contains_post_run_exposure(self):
        r=run_challenge('mixed',7,20,'fixed')
        self.assertIn('challenge_assessment',r)
        self.assertTrue(r['audit']['passed'])
        self.assertNotIn('fault_exposures',r['decision_history'][0])
    def test_site_uses_same_navigation_and_extra_signals(self):
        for page in ('challenge.html','how-it-works.html','industry.html'):
            t=(ROOT/'web'/page).read_text()
            self.assertIn('href="/"',t)
            self.assertIn('/reference',t)
        js=(ROOT/'web/challenge.js').read_text()
        for signal in ('bus_current_a','battery_soc_pct','sensor_delta','packet_loss_fraction'):
            self.assertIn(signal,js)
        comparison=(ROOT/'web/industry.html').read_text()
        self.assertNotIn('width:87%',comparison)
        self.assertIn('role-map',comparison)

if __name__=='__main__':unittest.main()
