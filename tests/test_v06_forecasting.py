"""v0.6 tests, including explicit checks against temporal future leakage."""
import copy
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from satvv.coupled import simulate_health
from satvv.forecast_v06 import (
    FEATURES, METHODS, SIGNALS, _campaigns, _feature_vector,
    evaluate_trajectory, features_for_forecasting, forecast_trajectory,
    future_pairs, train_forecasters,
)
from satvv.forecast_benchmark_v06 import benchmark_forecasting
from satvv.spec_v06 import SPECIFICATION, ARTICLE_ID, validate_dynamic_specification
from satvv.verification_v05 import ALL_TESTS, _offline_model_fixed_schedule, run_verification_v05
from satvv.web_server import PreviewHandler

class PredictionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.models = train_forecasters(train_seeds=2,calibration_seeds=3,horizon_s=300)
        cls.telemetry=simulate_health('resistance_ramp',step_s=30,
                                     mode='PAYLOAD')['telemetry']

    def test_causal_features_ignore_future_mutation(self):
        orig=features_for_forecasting(self.telemetry)[30]
        mutated=copy.deepcopy(self.telemetry)
        for p in mutated[31:]:
            p['bus_voltage_v']=1.0
            p['temperature_c']=500.0
            p['battery_soc_pct']=0
        after=features_for_forecasting(mutated)[30]
        self.assertEqual(orig,after)

    def test_features_have_no_hidden_fault_labels(self):
        row=features_for_forecasting(self.telemetry)[10]
        self.assertEqual(set(FEATURES) | {'time_s'},set(row))
        self.assertNotIn('fault',row)
        self.assertNotIn('episode',row)

    def test_future_labels_are_separated_from_inputs(self):
        current,future=next(iter(future_pairs(self.telemetry,300)))
        self.assertEqual(future['time_s']-current['time_s'],300)
        self.assertNotIn('future_voltage',current)

    def test_positive_interval_widths(self):
        self.assertGreater(self.models.interval_half_width['temperature_c'],0)
        self.assertGreater(self.models.interval_half_width['bus_voltage_v'],0)
        self.assertEqual(self.models.calibration_campaigns,21)

    def test_reproducible_model_training(self):
        other=train_forecasters(train_seeds=2,calibration_seeds=3,horizon_s=300)
        self.assertEqual(self.models.interval_half_width,other.interval_half_width)
        self.assertEqual(forecast_trajectory(self.telemetry,self.models)['forecasts'][10],
                         forecast_trajectory(self.telemetry,other)['forecasts'][10])

    def test_forecast_timings_and_prediction_comparators(self):
        result=forecast_trajectory(self.telemetry,self.models)
        self.assertGreater(len(result['forecasts']),20)
        for row in result['forecasts']:
            self.assertEqual(row['target_time_s']-row['issue_time_s'],300)
            self.assertEqual(set(row['predictions']),set(METHODS))
            self.assertLess(row['ml_lower'],row['ml_upper'])
        self.assertNotIn('truth',result)
        self.assertNotIn('episode',json.dumps(result['forecasts'][0]))

    def test_thermal_forecast_also_supported(self):
        result=forecast_trajectory(self.telemetry,self.models,'temperature_c')
        self.assertEqual(result['limit'],70.)
        self.assertEqual(result['meta']['signal'],'temperature_c')

    def test_observed_future_used_only_by_evaluator(self):
        result=evaluate_trajectory(self.telemetry,self.models,'bus_voltage_v')
        self.assertIn('actual_future',result[0])
        self.assertNotIn('actual_future',forecast_trajectory(self.telemetry,self.models)['forecasts'][0])

    def test_bad_horizon_rejected(self):
        with self.assertRaises(ValueError):train_forecasters(horizon_s=125)
        with self.assertRaises(ValueError):train_forecasters(train_seeds=0)
        with self.assertRaises(ValueError):train_forecasters(calibration_seeds=1)

    def test_multiple_targets_are_distinct(self):
        voltage=forecast_trajectory(self.telemetry,self.models,'bus_voltage_v')
        temperature=forecast_trajectory(self.telemetry,self.models,'temperature_c')
        self.assertNotEqual(voltage['forecasts'][4]['predictions']['gradient_boosting'],
                            temperature['forecasts'][4]['predictions']['gradient_boosting'])

    def test_distinct_seed_splits(self):
        a={x.split(':')[0] for x,_ in _campaigns(100,2,300)}
        b={x.split(':')[0] for x,_ in _campaigns(500,3,300)}
        c={x.split(':')[0] for x,_ in _campaigns(900,2,300,extra_shift=True)}
        self.assertFalse(a&b or a&c or b&c)

    def test_versioned_current_requirement_and_coverage(self):
        validate_dynamic_specification()
        self.assertIn('1.30 A',SPECIFICATION['REQ-EPS-I'])
        self.assertTrue(all(r in SPECIFICATION for t in ALL_TESTS for r in t.checks))
        self.assertEqual(len(ALL_TESTS),16)

    def test_model_fixed_preplanned_before_telemetry(self):
        order=_offline_model_fixed_schedule()
        self.assertEqual(len(order),16)
        self.assertEqual(len({x.id for x in order}),16)
        initial=run_verification_v05('model_fixed','healthy',budget_min=30,seed=5)
        shifted=run_verification_v05('model_fixed','resistance_ramp',budget_min=30,seed=5,onset_s=2500)
        self.assertEqual([x['test_id'] for x in initial['evidence']],
                         [x['test_id'] for x in shifted['evidence']])

    def test_benchmark_writes_expected_files(self):
        with tempfile.TemporaryDirectory() as d:
            res=benchmark_forecasting(train_seeds=2,calibration_seeds=3,eval_seeds=1,out=d)
            self.assertEqual(len(res['summary']),8)
            self.assertTrue((Path(d)/'forecast_benchmark.json').exists())
            self.assertEqual(res['meta']['evaluation_campaigns'],7)
            self.assertTrue(all(row['macro_mae']>=0 for row in res['summary']))

class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),PreviewHandler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.thread.join(timeout=2);cls.server.server_close()

    def post(self,data):
        request=Request(self.url+'/api/forecast-v06',data=json.dumps(data).encode(),
            headers={'Content-Type':'application/json'},method='POST')
        with urlopen(request,timeout=30) as resp:return json.loads(resp.read())

    def test_browser_has_new_tab(self):
        with urlopen(self.url+'/legacy') as r:
            body=r.read()
            self.assertIn(b'Forecasting v0.6',body)
            self.assertIn(b'forecastScreen',body)

    def test_valid_forecast_api(self):
        out=self.post({'scenario':'heater_fault','signal':'temperature_c',
                       'horizon_s':300,'mode':'PAYLOAD'})
        self.assertEqual(out['meta']['signal'],'temperature_c')
        self.assertGreater(len(out['forecasts']),20)
        self.assertNotIn('truth',out)

    def test_bad_horizon_api_rejected(self):
        with self.assertRaises(HTTPError) as context:
            self.post({'horizon_s':175})
        self.assertEqual(context.exception.code,400)

    def test_truth_override_api_rejected(self):
        with self.assertRaises(HTTPError) as context:
            self.post({'truth':{'fault':'battery_resistance'}})
        self.assertEqual(context.exception.code,400)

if __name__=='__main__':unittest.main()
