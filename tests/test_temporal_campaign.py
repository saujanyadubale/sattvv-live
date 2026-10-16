"""v0.4 temporal scheduler: reproducibility, repeat action, budget, API, evidence."""
import json
import math
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from satvv.core import Fault, TESTS
from satvv.dynamics import DynamicSpacecraft, FaultInjection
from satvv.temporal_campaign import (
    ALL_POLICIES, TEMPORAL_POLICIES, _temporal_score, _wait,
    compare_temporal, run_temporal_campaign,
)
from satvv.temporal_benchmark import _bootstrap_rates
from satvv.web_server import PreviewHandler


class TemporalCampaignTests(unittest.TestCase):
    def test_seven_distinct_strategies(self):
        self.assertEqual(len(ALL_POLICIES), 7)
        self.assertEqual(len(set(ALL_POLICIES)), 7)

    def test_budget_and_elapsed_time_and_no_fraudulent_detection_from_waits(self):
        for policy in TEMPORAL_POLICIES:
            for budget in (1, 4, 12, 20, 33):
                c = run_temporal_campaign(policy, 'undervoltage', budget_min=budget,
                                          fault_start_s=600)
                with self.subTest(policy=policy,budget=budget):
                    self.assertLessEqual(c.spent_s, budget*60)
                    self.assertEqual(c.spent_s, c.terminal_state['time_s'])
                    self.assertEqual(c.spent_s, sum(r['end_s']-r['start_s'] for r in c.evidence))
                    for rec in c.evidence:
                        self.assertGreater(rec['end_s'],rec['start_s'])
                        if rec['kind'] == 'wait':
                            self.assertFalse(rec['checks'])
                            self.assertFalse(rec['detected'])
                        else:
                            self.assertEqual(rec['detected'], any(x is False for x in rec['checks'].values()))

    def test_repeat_annotations_match_actual_occurrences(self):
        for policy in TEMPORAL_POLICIES:
            c = run_temporal_campaign(policy, 'none', budget_min=33)
            counts={}
            repeated=False
            for r in c.evidence:
                if r.get('kind') == 'wait': continue
                self.assertEqual(r['repeat_index'], counts.get(r['test_id'], 0))
                repeated |= r['repeat_index'] > 0
                counts[r['test_id']] = r['repeat_index']+1
            self.assertTrue(repeated,policy)

    def test_low_utility_monitoring_waits_are_explicit(self):
        c=run_temporal_campaign('temporal_blind', Fault.NONE, budget_min=33)
        self.assertTrue(any(e.get('kind')=='wait' for e in c.evidence))
        self.assertFalse(c.detected)

    def test_no_hidden_fault_truth_inside_decisions(self):
        for policy in TEMPORAL_POLICIES:
            c=run_temporal_campaign(policy,'undervoltage',budget_min=20,fault_start_s=600)
            for r in c.evidence:
                for k in ('fault', 'fault_start_s','severity'):
                    self.assertNotIn(k, r)
                    self.assertNotIn(k, r['telemetry_end'])
                    self.assertNotIn(k, r['telemetry_start'])
                self.assertIn('decision', r)

    def test_same_seed_same_trace(self):
        for p in TEMPORAL_POLICIES:
            a=run_temporal_campaign(p,'sensor_stuck',budget_min=33,seed=15,fault_start_s=600)
            b=run_temporal_campaign(p,'sensor_stuck',budget_min=33,seed=15,fault_start_s=600)
            self.assertEqual(a.as_dict(),b.as_dict())

    def test_fault_after_budget_equals_healthy(self):
        for p in TEMPORAL_POLICIES:
            a=run_temporal_campaign(p,'thermal_runaway',budget_min=20,fault_start_s=5000)
            b=run_temporal_campaign(p,'none',budget_min=20)
            self.assertEqual(a.evidence,b.evidence)
            self.assertFalse(a.detected)

    def test_default_healthy_controls_do_not_trigger_verification_failure(self):
        for p in TEMPORAL_POLICIES:
            for seed in range(5):
                c=run_temporal_campaign(p,Fault.NONE,budget_min=33,seed=seed)
                self.assertFalse(c.detected, f'{p} seed {seed}')

    def test_direct_idle_interval_has_no_requirement_checks(self):
        sim=DynamicSpacecraft(injection=FaultInjection(Fault.THERMAL_RUNAWAY,0))
        r=_wait(sim,sunlit=True)
        self.assertEqual(r['kind'],'wait')
        self.assertEqual(r['end_s'],60)
        self.assertEqual(r['checks'],{})
        self.assertFalse(r['detected'])

    def test_observed_risk_changes_ranking_no_risk_does_not(self):
        eps=next(t for t in TESTS if t.id=='T03')
        kw=dict(now_s=600,check_times={},test_times={},counts={})
        no_signal=_temporal_score(eps,focus={},use_risk=True,**kw)
        high_signal=_temporal_score(eps,focus={'EPS':7.0},use_risk=True,**kw)
        blind=_temporal_score(eps,focus={'EPS':7.0},use_risk=False,**kw)
        self.assertGreater(high_signal,no_signal)
        self.assertAlmostEqual(blind,no_signal)

    def test_measurement_age_increases_test_utility(self):
        t=next(t for t in TESTS if t.id=='T11')
        base=dict(test=t,test_times={'T11':0},counts={'T11':1},focus={},use_risk=False)
        recently=_temporal_score(now_s=100,check_times={'REQ-THM-D':100},**base)
        stale=_temporal_score(now_s=1300,check_times={'REQ-THM-D':100},**base)
        self.assertGreater(stale,recently)

    def test_all_legacy_policies_unmodified(self):
        from satvv.dynamic_campaign import compare_dynamic
        params=dict(fault='undervoltage',budget_min=20,seed=7,fault_start_s=600)
        old=compare_dynamic(**params)
        new=compare_temporal(**params)
        for p in old['policies']:
            self.assertEqual(old['policies'][p],new['policies'][p])

    def test_meaningful_campaign_metadata(self):
        result=compare_temporal(fault='none',budget_min=12,fault_start_s=600)
        self.assertEqual(result['meta']['version'],'0.4')
        self.assertEqual(set(result['policies']),set(ALL_POLICIES))

    def test_input_validation(self):
        for kw in ({'budget_min':0},{'budget_min':61},{'budget_min':True},
                   {'fault_start_s':19},{'seed':-1},{'severity':float('nan')},
                   {'initial_soc':float('inf')},{'sunlit':'yes'},
                   {'fault':'not_a_fault'}):
            with self.subTest(kw=kw),self.assertRaises((ValueError,TypeError)):
                compare_temporal(**kw)


class TemporalApiTests(unittest.TestCase):
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
        with urlopen(req,timeout=5) as resp:
            return json.loads(resp.read())

    def test_new_comparison_api(self):
        result=self.request('/api/compare-temporal',{'fault':'thermal_runaway',
                                                     'budget_min':20,'fault_start_s':600})
        self.assertEqual(result['meta']['version'],'0.4')
        self.assertEqual(set(result['policies']),set(ALL_POLICIES))

    def test_old_api_maintained(self):
        result=self.request('/api/compare',{'fault':'none','budget_min':12})
        self.assertEqual(result['meta']['version'],'0.3')

    def test_new_api_rejects_malformed(self):
        for bad in ({'fault':'unknown'},{'severity':float('nan')},{'fault_start_s':19},
                    {'initial_soc':-0.1},{'budget_min':True},{'unapproved':'true'}):
            with self.subTest(bad=bad),self.assertRaises(HTTPError) as e:
                self.request('/api/compare-temporal',bad)
            self.assertEqual(e.exception.code,400)

    def test_ui_served_v04(self):
        with urlopen(self.root+'/legacy', timeout=4) as r:
            body=r.read().decode()
        self.assertIn('Run seven-policy comparison',body)
        self.assertIn('temporal_adaptive',body)


if __name__=='__main__': unittest.main()
