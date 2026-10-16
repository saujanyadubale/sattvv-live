"""v0.3 persistent simulated verification: budgets, causality, baselines, API."""
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from satvv.core import Fault, Mode, TESTS
from satvv.dynamic_campaign import (POLICIES, _path, _execute_test,
                                     compare_dynamic, run_dynamic_campaign)
from satvv.dynamics import DynamicSpacecraft, FaultInjection
from satvv.web_server import PreviewHandler


class DynamicCampaignTests(unittest.TestCase):
    def test_no_budget_overrun_or_clock_disagreement(self):
        for policy in POLICIES:
            for budget in (4, 8, 12, 20, 33):
                with self.subTest(policy=policy, budget=budget):
                    result = run_dynamic_campaign(policy, 'undervoltage', budget_min=budget)
                    self.assertLessEqual(result.spent_s, 60 * budget)
                    self.assertEqual(result.spent_s,
                                     sum(e['cost_min'] * 60 for e in result.evidence))
                    self.assertEqual(result.terminal_state['time_s'], result.spent_s)

    def test_replay_is_reproducible_for_all_strategies(self):
        for policy in POLICIES:
            a = run_dynamic_campaign(policy, 'thermal_runaway', seed=9)
            b = run_dynamic_campaign(policy, 'thermal_runaway', seed=9)
            self.assertEqual(a.as_dict(), b.as_dict())

    def test_healthy_no_false_fails_at_default_settings(self):
        for policy in POLICIES:
            for seed in range(4):
                self.assertFalse(run_dynamic_campaign(policy, Fault.NONE,
                                                      budget_min=33, seed=seed).detected)

    def test_no_hidden_fault_label_inside_policy_evidence(self):
        campaign = run_dynamic_campaign('adaptive', 'undervoltage', budget_min=20)
        for record in campaign.evidence:
            for tm in (record['telemetry_start'], record['telemetry_end']):
                self.assertNotIn('fault', tm)
                self.assertNotIn('severity', tm)
                self.assertNotIn('fault_start_s', tm)
            self.assertNotIn('fault', record)

    def test_fault_onset_after_campaign_means_same_as_healthy(self):
        for policy in POLICIES:
            faulted = run_dynamic_campaign(policy, 'undervoltage',
                                           budget_min=20, fault_start_s=5000)
            healthy = run_dynamic_campaign(policy, 'none', budget_min=20)
            self.assertEqual(faulted.evidence, healthy.evidence)
            self.assertFalse(faulted.detected)

    def test_injected_fault_changes_observable_telemetry_without_oracle(self):
        normal = run_dynamic_campaign('fixed', 'none', budget_min=4)
        faulty = run_dynamic_campaign('fixed', 'undervoltage', budget_min=4)
        self.assertLess(faulty.evidence[0]['telemetry_end']['bus_voltage_v'],
                        normal.evidence[0]['telemetry_end']['bus_voltage_v'])

    def test_each_default_fault_detectable_by_some_policy_given_full_budget(self):
        for f in Fault:
            if f is Fault.NONE:
                continue
            with self.subTest(fault=f.value):
                r = compare_dynamic(fault=f, budget_min=33)
                self.assertTrue(any(x['detected'] for x in r['policies'].values()))

    def test_detection_requires_failed_check_not_telemetry_alarm(self):
        c = run_dynamic_campaign('fixed', 'undervoltage', budget_min=12)
        for record in c.evidence:
            self.assertEqual(record['detected'], any(x is False for x in record['checks'].values()))
        self.assertEqual(c.detected, any(r['detected'] for r in c.evidence))

    def test_guard_check_expected_rejection_is_not_fault(self):
        test = next(t for t in TESTS if t.id == 'T12')
        normal = _execute_test(DynamicSpacecraft(injection=FaultInjection(Fault.NONE,0)),test,True)
        faulty = _execute_test(DynamicSpacecraft(injection=FaultInjection(Fault.ILLEGAL_TRANSITION,0)),test,True)
        self.assertEqual(normal['checks']['REQ-OBC-G'], True)
        self.assertEqual(faulty['checks']['REQ-OBC-G'], False)

    def test_unreachable_payload_link_does_not_count_as_checked_link_failure(self):
        test = next(t for t in TESTS if t.id == 'T05')
        sim = DynamicSpacecraft(injection=FaultInjection(Fault.PAYLOAD_BOOT_FAIL,0))
        result = _execute_test(sim,test,True)
        self.assertEqual(result['status'],'INCONCLUSIVE')
        self.assertTrue(all(v is None for v in result['checks'].values()))
        self.assertFalse(result['detected'])

    def test_path_respects_legal_mode_transitions(self):
        from satvv.dynamics import LEGAL_TRANSITIONS
        for start in Mode:
            for goal in Mode:
                prev = start
                route = _path(start,goal)
                if route is None:
                    self.assertEqual(goal, Mode.BOOT)
                    continue
                for nxt in route:
                    self.assertIn(nxt, LEGAL_TRANSITIONS[prev])
                    prev = nxt
                self.assertEqual(prev,goal)

    def test_repeatable_comparison_structure(self):
        a=compare_dynamic(fault='packet_loss',budget_min=12,seed=3)
        b=compare_dynamic(fault='packet_loss',budget_min=12,seed=3)
        self.assertEqual(a,b)
        self.assertEqual(set(a['policies']),set(POLICIES))

    def test_input_validation(self):
        for kw in ({'budget_min':0},{'budget_min':70},{'budget_min':4.5},
                   {'fault_start_s':19},{'seed':-1},{'initial_soc':1.3},
                   {'severity':4},{'sunlit':'yes'}):
            with self.subTest(kw=kw),self.assertRaises(ValueError):
                run_dynamic_campaign('adaptive','undervoltage',**kw)
        with self.assertRaises(ValueError):
            run_dynamic_campaign('adaptive','unknown')


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),PreviewHandler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.root='http://127.0.0.1:'+str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=3)

    def request(self,path,body):
        req=Request(self.root+path,json.dumps(body).encode(),{'Content-Type':'application/json'})
        with urlopen(req,timeout=5) as r:
            return json.loads(r.read())

    def test_api_compare(self):
        result=self.request('/api/compare',{'fault':'undervoltage','budget_min':12,'seed':4})
        self.assertEqual(result['meta']['version'],'0.3')
        self.assertEqual(set(result['policies']),set(POLICIES))

    def test_api_previous_simulation_still_works(self):
        result=self.request('/api/simulate',{'fault':'none','duration_s':600,'step_s':30})
        self.assertEqual(result['meta']['version'],'0.2')
        self.assertEqual(len(result['telemetry']),21)

    def test_api_invalid_request_returns_400(self):
        for bad in ({'budget_min':10000},{'fault':'unknown'},{'sunlit':'false'},{'seed':2.1},
                    {'fault_start_s':25},{'unsupported':'value'}):
            with self.subTest(bad=bad),self.assertRaises(HTTPError) as ctx:
                self.request('/api/compare',bad)
            self.assertEqual(ctx.exception.code,400)


if __name__=='__main__': unittest.main()
