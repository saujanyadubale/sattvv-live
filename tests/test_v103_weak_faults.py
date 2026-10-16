"""Causal weak-fault warning versus requirement verification boundaries."""
import unittest
import threading, json
from urllib.request import urlopen,Request
from http.server import ThreadingHTTPServer
from satvv.web_server import PreviewHandler
from satvv.coupled import simulate_health
from satvv.weak_monitor_v103 import WeakSignalMonitor
from satvv.challenge_v096 import run_challenge

class WeakSignalTests(unittest.TestCase):
    def run_monitor(self, scenario='healthy', *, severity=.5, mode='NOMINAL', seed=504):
        result=simulate_health(scenario,seed=seed,severity=severity,onset_s=420,
            duration_s=1800,step_s=10,mode=mode)
        m=WeakSignalMonitor()
        for row in result['telemetry']:m.update(row)
        return m

    def test_no_false_warnings_in_healthy_and_normal_load(self):
        for scenario in ('healthy','normal_load_cycle'):
            for mode in ('NOMINAL','PAYLOAD','DOWNLINK'):
                for seed in (500,503,509):
                    with self.subTest(scenario=scenario,mode=mode,seed=seed):
                        self.assertFalse(self.run_monitor(scenario,mode=mode,seed=seed).events)

    def test_low_severity_synthetic_signatures(self):
        cases={'sensor_drift':'sensor_drift','resistance_ramp':'battery_residual',
               'heater_fault':'thermal_innovation','radio_burst':'comms_loss'}
        for fault,kind in cases.items():
            mode='DOWNLINK' if fault=='radio_burst' else 'NOMINAL'
            with self.subTest(fault=fault):
                events=self.run_monitor(fault,mode=mode).events
                self.assertTrue(any(e['kind']==kind and e['time_s']>=420 for e in events))
                self.assertTrue(all(e['source']=='online_weak_signal_monitor' for e in events))

    def test_unobservable_radio_without_downlink(self):
        self.assertFalse(self.run_monitor('radio_burst',mode='NOMINAL').events)

    def test_single_temperature_spike_not_sufficient(self):
        m=WeakSignalMonitor()
        for i in range(50):
            value=24. if i!=22 else 27.
            m.update({'time_s':i*10,'mode':'NOMINAL','temperature_c':value,
              'redundant_temperature_c':24.,'battery_soc_pct':80.,'load_w':7.,
              'bus_voltage_v':7.73,'bus_current_a':.8,'packet_loss_fraction':0.})
        self.assertFalse(any(e['kind']=='sensor_drift' for e in m.events))

    def test_oracle_labels_do_not_affect_warning(self):
        sim=simulate_health('sensor_drift',seed=501,severity=.5,onset_s=420,
                 duration_s=1200,step_s=10)
        a,b=WeakSignalMonitor(),WeakSignalMonitor()
        for row in sim['telemetry']:
            a.update(row)
            b.update({**row,'injected_fault':'NONE','oracle':{'mechanism':'heater_fault'}})
        self.assertEqual(a.events,b.events)

    def test_seed7_weak_fault_warns_without_falsifying_requirement(self):
        result=run_challenge('mixed',7,90,'predictive_active')
        self.assertFalse(result['detected'])
        self.assertTrue(result['audit']['passed'])
        warnings=result['weak_fault_analysis']['warning_events']
        self.assertTrue(any(x['kind']=='sensor_drift' and 4580<=x['time_s']<4930 for x in warnings))
        self.assertTrue(all(x['kind']!='formal_requirement_failure' for x in warnings))
        during=[x for x in result['evidence'] if 4580<=x['start_s']<4930]
        self.assertTrue(any(x['decision']['weak_signal_risks_before'].get('THERMAL',0)>0 for x in during))
        self.assertTrue(all(x['status']!='FAIL' for x in result['evidence']))

    def test_unified_api_displays_early_warning_not_verified_failure(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),PreviewHandler)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            payload=json.dumps({'mode':'random','difficulty':'mixed','seed':7,
                  'intensity':'exploratory','budget_min':90,'policy':'predictive_active'}).encode()
            request=Request('http://127.0.0.1:'+str(server.server_port)+'/api/unified',
                 data=payload,headers={'Content-Type':'application/json'})
            with urlopen(request,timeout=30) as response:result=json.load(response)
            self.assertFalse(result['detected'])
            self.assertTrue(result['weak_fault_analysis']['warning_events'])
            self.assertEqual(result['insights_v11']['status'],'early_warning')
            self.assertFalse(result['insights_v11']['failed_checks'])
        finally:
            server.shutdown();thread.join(timeout=3);server.server_close()

    def test_dashboard_separates_formal_failure_and_weak_warning(self):
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]/'web'
        self.assertIn('id="chWarningTag"',(root/'challenge.html').read_text())
        js=(root/'challenge.js').read_text()
        self.assertIn('weak_fault_analysis',js)
        self.assertIn('First warning', (root/'challenge.html').read_text())
        self.assertIn('No failure · early warning',js)

    def test_weak_monitor_priority_not_pretending_to_guarantee_failures(self):
        a=run_challenge('mixed',7,90,'predictive_active',_weak_monitor_priority=False)
        b=run_challenge('mixed',7,90,'predictive_active',_weak_monitor_priority=True)
        self.assertFalse(a['detected'])
        self.assertFalse(b['detected'])
        self.assertTrue(b['weak_fault_analysis']['formal_verification_unchanged'])

if __name__=='__main__':unittest.main()
