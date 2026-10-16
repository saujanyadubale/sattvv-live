"""Science/engineering regression tests for dynamic v0.2, no NumPy required."""
import unittest
from satvv.core import Fault, Mode
from satvv.dynamics import (DynamicSpacecraft, DynamicsConfig,
                             FaultInjection, run_scenario)


class DynamicsTests(unittest.TestCase):
    def test_healthy_command_guard_and_mode_sequence(self):
        sim = DynamicSpacecraft()
        self.assertFalse(sim.command(Mode.DOWNLINK)['accepted'])
        self.assertTrue(sim.command(Mode.SAFE)['accepted'])
        self.assertFalse(sim.command(Mode.DOWNLINK)['accepted'])
        self.assertTrue(sim.command(Mode.NOMINAL)['accepted'])
        self.assertTrue(sim.command(Mode.PAYLOAD)['accepted'])
        self.assertTrue(sim.command(Mode.DOWNLINK)['accepted'])
        self.assertEqual(sim.state.mode, Mode.DOWNLINK)

    def test_energy_integrates_with_correct_units(self):
        config = DynamicsConfig(initial_soc=.5, solar_array_w=0)
        sim = DynamicSpacecraft(config)
        sim.command(Mode.SAFE)
        sim.step(3600, sunlit=False)
        self.assertAlmostEqual(sim.state.soc, .5 - 1.8 / 24.0, places=7)

    def test_eclipse_lowers_soc_relative_to_sunlight(self):
        sunlight = run_scenario(fault='none', sunlit=True)
        eclipse = run_scenario(fault='none', sunlit=False)
        self.assertGreater(sunlight['telemetry'][-1]['battery_soc_pct'],
                           eclipse['telemetry'][-1]['battery_soc_pct'])

    def test_thermal_response_is_time_dependent(self):
        a = DynamicSpacecraft()
        a.command(Mode.SAFE)
        a.command(Mode.NOMINAL)
        a.command(Mode.PAYLOAD)
        initial = a.state.temperature_c
        a.step(120)
        self.assertGreater(a.state.temperature_c, initial)
        self.assertLess(a.state.temperature_c, 60)
        self.assertAlmostEqual(a.state.time_s, 120)

    def test_no_fault_no_alarms_or_safety_interventions(self):
        healthy = run_scenario(fault=Fault.NONE)
        self.assertIsNone(healthy['summary']['first_alarm_s'])
        self.assertIsNone(healthy['summary']['first_evidence_s'])
        self.assertEqual(healthy['summary']['autonomous_safe_entries'], 0)
        self.assertEqual(healthy['summary']['watchdog_recoveries'], 1)

    def test_each_fault_has_an_observable_effect(self):
        for fault in (f for f in Fault if f is not Fault.NONE):
            with self.subTest(fault=fault.value):
                result = run_scenario(fault=fault)
                self.assertIsNotNone(result['summary']['first_evidence_s'])

    def test_guard_fault_does_not_bypass_unrelated_guard(self):
        sim = DynamicSpacecraft(injection=FaultInjection(Fault.ILLEGAL_TRANSITION, 0))
        sim.command(Mode.SAFE)
        self.assertTrue(sim.command(Mode.DOWNLINK)['accepted'])
        self.assertFalse(sim.command(Mode.NOMINAL)['accepted'])
        self.assertEqual(len([e for e in sim.events if e['type'] == 'guard_violation']), 1)

    def test_payload_fault_rejects_payload_command(self):
        sim = DynamicSpacecraft(injection=FaultInjection(Fault.PAYLOAD_BOOT_FAIL, 0))
        sim.command(Mode.SAFE)
        sim.command(Mode.NOMINAL)
        response = sim.command(Mode.PAYLOAD)
        self.assertFalse(response['accepted'])
        self.assertEqual(sim.state.mode, Mode.NOMINAL)

    def test_watchdog_recovers_healthy_hang_but_not_faulty_hang(self):
        normal = DynamicSpacecraft()
        normal.command(Mode.SAFE)
        normal.trigger_cpu_hang()
        normal.step(120)
        self.assertFalse(normal.state.cpu_hung)
        failed = DynamicSpacecraft(injection=FaultInjection(Fault.WATCHDOG_FAILURE, 0))
        failed.command(Mode.SAFE)
        failed.trigger_cpu_hang()
        failed.step(120)
        self.assertTrue(failed.state.cpu_hung)
        self.assertIn('WATCHDOG_TIMEOUT', failed.telemetry()['alarms'])

    def test_repeatability_and_no_hidden_fault_in_telemetry(self):
        first = run_scenario(fault='thermal_runaway', seed=3)
        second = run_scenario(fault='thermal_runaway', seed=3)
        self.assertEqual(first, second)
        for row in first['telemetry']:
            self.assertNotIn('fault', row)
            self.assertNotIn('severity', row)

    def test_validation(self):
        for args in ({'step_s': 0}, {'duration_s': 31}, {'duration_s': 90000},
                     {'initial_soc': 1.2}, {'severity': -1},
                     {'fault_start_s': 601}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                run_scenario(**args)
        with self.assertRaises(ValueError):
            DynamicsConfig(battery_capacity_wh=0)

    def test_fault_free_one_at_a_time_still_uses_legacy_benchmark(self):
        from satvv.campaign import run_campaign
        self.assertTrue(run_campaign('adaptive', Fault.UNDERVOLTAGE, 20, 7).detected)


if __name__ == '__main__':
    unittest.main()
