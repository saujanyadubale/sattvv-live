import unittest
from satvv.adcs_v08 import SpacecraftWithADCS,ADCS_TESTS,execute_adcs_test,run_adcs_suite
from satvv.core import Mode
class ADCS(unittest.TestCase):
    def test_healthy(self):
        r=run_adcs_suite('healthy')
        self.assertTrue(all(v['status']=='PASS' for v in r['procedures'].values()),r)
    def test_wheel_weak(self):
        r=run_adcs_suite('adcs_wheel_weak',onset_s=0)
        self.assertEqual(r['procedures']['T17']['status'],'FAIL')
    def test_bias(self):
        self.assertEqual(run_adcs_suite('adcs_gyro_bias',onset_s=0)['procedures']['T19']['status'],'FAIL')
    def test_star_drop(self):
        self.assertEqual(run_adcs_suite('adcs_star_dropout',onset_s=0)['procedures']['T19']['status'],'FAIL')
    def test_clock_and_physical_power(self):
        sim=SpacecraftWithADCS('healthy')
        sim.command(Mode.SAFE);sim.command(Mode.NOMINAL)
        sim.adcs.theta_rad=.2
        orig=sim.state.soc
        sim.step(10)
        self.assertEqual(sim.state.time_s,10)
        self.assertLess(sim.state.soc,orig+.005)
    def test_test_load_survives_adcs_update(self):
        sim=SpacecraftWithADCS('healthy')
        sim.extra_load_w=3.
        sim.command(Mode.SAFE);sim.command(Mode.NOMINAL)
        sim.step(10)
        self.assertEqual(sim.extra_load_w,3.)
        self.assertGreater(sim.telemetry()['load_w'],5.)
    def test_repeatable(self):
        self.assertEqual(run_adcs_suite('healthy',seed=99),run_adcs_suite('healthy',seed=99))
