"""v0.5 physics, fault episodes, detector boundaries, sixteen-test integration."""
import json
import unittest
from math import isclose
from satvv.coupled import (SCENARIOS, Episode, CoupledSpacecraft, make_episodes,
                           predict_nominal_voltage, simulate_health)
from satvv.monitoring import (engineer_features, classical_detector, alerts_to_episodes,
                              warning_summary, predict_methods)
from satvv.verification_v05 import (ALL_TESTS, ADDITIONAL_TESTS, EXTRA_REQUIREMENTS,
                                    run_verification_v05, _extended_test)
from satvv.temporal_campaign import ALL_POLICIES


class EpisodeTests(unittest.TestCase):
    def test_intervals_are_right_open(self):
        ep=Episode('battery_resistance',100,200,1)
        self.assertEqual([ep.weight(t) for t in (99,100,199,200)],[0,1,1,0])

    def test_ramp_is_gradual(self):
        ep=Episode('battery_resistance',100,400,2,200)
        self.assertEqual(ep.weight(100),0)
        self.assertAlmostEqual(ep.weight(200),1)
        self.assertAlmostEqual(ep.weight(300),2)

    def test_recurrence_and_recovery(self):
        first,second=make_episodes('intermittent_resistance',1,180)
        self.assertEqual(first.weight(220),1)
        self.assertEqual(first.weight(400),0)
        self.assertEqual(second.weight(570),1.35)
        self.assertEqual(second.weight(1200),0)

    def test_bad_episode_rejected(self):
        with self.assertRaises(ValueError):Episode('battery_resistance',100,99)
        with self.assertRaises(ValueError):Episode('fake',0,100)

    def test_nominal_voltage_load_dependence(self):
        self.assertGreater(predict_nominal_voltage(.8,2),predict_nominal_voltage(.8,9))

    def test_voltage_responds_to_resistance(self):
        healthy=CoupledSpacecraft(seed=1)
        faulty=CoupledSpacecraft((Episode('battery_resistance',0,1000,1),),seed=1)
        healthy.extra_load_w=faulty.extra_load_w=5
        self.assertLess(faulty._electrical()[1],healthy._electrical()[1]-.3)

    def test_heat_coupling_at_equal_load(self):
        h=CoupledSpacecraft(seed=1)
        f=CoupledSpacecraft((Episode('battery_resistance',0,1000,1),),seed=1)
        for _ in range(60):h.step(10);f.step(10)
        self.assertGreater(f.state.temperature_c,h.state.temperature_c)

    def test_eclipse_changes_soc(self):
        sun=CoupledSpacecraft(eclipse=False)
        eclipse=CoupledSpacecraft(eclipse=True)
        for _ in range(90):sun.step(10);eclipse.step(10)
        self.assertLess(eclipse.state.soc,sun.state.soc)

    def test_normal_load_cycle_is_not_labeled_as_fault(self):
        data=simulate_health('normal_load_cycle',step_s=30)
        self.assertFalse(data['truth']['is_fault'])
        self.assertEqual(data['truth']['episodes'],[])

    def test_telemetry_does_not_reveal_injection_truth(self):
        sim=CoupledSpacecraft(make_episodes('sensor_drift',1,0))
        for _ in range(40):sim.step(10)
        public=json.dumps(sim.telemetry()).lower()
        for leaked in ('severity','mechanism','sensor_drift','episode','fault'):
            self.assertNotIn('"'+leaked+'"',public)

    def test_deterministic_replay(self):
        a=simulate_health('intermittent_resistance',seed=4,step_s=30)
        b=simulate_health('intermittent_resistance',seed=4,step_s=30)
        self.assertEqual(a['telemetry'],b['telemetry'])

    def test_true_sensor_drift_changes_disagreement(self):
        d=simulate_health('sensor_drift',step_s=30)
        before=[p for p in d['telemetry'] if p['time_s']<480]
        after=[p for p in d['telemetry'] if p['time_s']>1200]
        delta=lambda xs:sum(abs(p['temperature_c']-p['redundant_temperature_c']) for p in xs)/len(xs)
        self.assertGreater(delta(after),delta(before)+2)

    def test_bad_scenario_rejected(self):
        with self.assertRaises(ValueError):simulate_health('fake')
        with self.assertRaises(ValueError):simulate_health(step_s=100)

class MonitoringTests(unittest.TestCase):
    def test_features_only_use_observed_fields(self):
        sim=simulate_health('healthy',step_s=30)
        rows=engineer_features(sim['telemetry'])
        self.assertEqual(len(rows),len(sim['telemetry']))
        self.assertNotIn('episode',rows[0])
        self.assertNotIn('fault',rows[0])

    def test_residual_stays_small_healthy(self):
        rows=engineer_features(simulate_health('healthy',step_s=30)['telemetry'])
        self.assertLess(max(abs(x['residual_v']) for x in rows),.06)

    def test_residual_detects_resistance(self):
        rows=engineer_features(simulate_health('resistance_ramp',step_s=30)['telemetry'])
        self.assertGreater(max(x['residual_v'] for x in rows),.13)

    def test_alert_debouncing(self):
        self.assertEqual(alerts_to_episodes([0,1,1,1,0,1,1],[0,1,2,3,4,5,6]),[2,6])

    def test_no_truth_in_detector_call(self):
        s=simulate_health('healthy',step_s=30)
        methods=predict_methods(s['telemetry'])
        self.assertEqual(set(methods),{'limit','trend','cusum','physics_residual'})

    def test_limit_healthy_is_no_alert(self):
        s=simulate_health('healthy',step_s=30)
        x=engineer_features(s['telemetry'])
        self.assertFalse(any(classical_detector(x,'limit')))

    def test_warning_is_not_verification_result(self):
        sim=simulate_health('resistance_ramp',step_s=30)
        flags=classical_detector(engineer_features(sim['telemetry']),'physics_residual')
        result=warning_summary(flags,sim['telemetry'],sim['truth'])
        self.assertIn('first_warning_s',result)
        self.assertNotIn('PASS',result)
        self.assertNotIn('FAIL',result)

class VerificationTests(unittest.TestCase):
    def test_sixteen_catalog_entries_and_new_requirements(self):
        self.assertEqual(len(ALL_TESTS),16)
        self.assertEqual(len({x.id for x in ALL_TESTS}),16)
        for t in ADDITIONAL_TESTS:
            self.assertTrue(set(t.checks).issubset(set(EXTRA_REQUIREMENTS)|{'REQ-THM-T'}))

    def test_new_tests_execute_under_expected_cost(self):
        for t in ADDITIONAL_TESTS:
            sim=CoupledSpacecraft(seed=2)
            result=_extended_test(sim,t)
            self.assertEqual(result['end_s']-result['start_s'],t.cost*60)
            self.assertEqual(set(result['checks']),set(t.checks))
            self.assertEqual(result['status'],'PASS',msg=t.id)

    def test_all_policies_accept_same_catalog_and_budget(self):
        for p in ALL_POLICIES:
            c=run_verification_v05(p,'healthy',budget_min=30)
            self.assertLessEqual(c['spent_s'],1800)
            self.assertFalse(c['detected'],msg=p)
            for e in c['evidence']:
                if e['kind']=='test':self.assertIn(e['test_id'],{t.id for t in ALL_TESTS})

    def test_normal_load_is_not_mistaken_as_fail_by_adaptive(self):
        for p in ('adaptive','temporal_adaptive'):
            self.assertFalse(run_verification_v05(p,'normal_load_cycle',budget_min=40)['detected'])

    def test_targeted_load_step_can_detect_ramping_resistance(self):
        sim=CoupledSpacecraft(make_episodes('resistance_ramp',1,0))
        for _ in range(80):sim.step(10)
        record=_extended_test(sim, next(t for t in ADDITIONAL_TESTS if t.id=='T14'))
        self.assertFalse(record['checks']['REQ-EPS-R'])
        self.assertTrue(record['detected'])

    def test_repeated_fault_works_with_temporal_policy(self):
        result=run_verification_v05('temporal_adaptive','intermittent_resistance',budget_min=40)
        self.assertTrue(result['detected'])
        self.assertEqual(result['spent_s'],result['evidence'][-1]['end_s'])

    def test_seed_reproducible(self):
        a=run_verification_v05('random','resistance_ramp',budget_min=30,seed=21)
        b=run_verification_v05('random','resistance_ramp',budget_min=30,seed=21)
        self.assertEqual(a,b)

    def test_rejects_invalid_budget(self):
        with self.assertRaises(ValueError):run_verification_v05(budget_min=0)

if __name__=='__main__':unittest.main()
