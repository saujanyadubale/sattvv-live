"""v0.9.9 UI/documentation contract without modifying spacecraft research results."""
import unittest
from pathlib import Path
from io import BytesIO
from unittest.mock import patch
from satvv.web_server import PreviewHandler,WEB_DIR

class Mission099Tests(unittest.TestCase):
    def test_mission_asset_and_html_contract(self):
        html=(WEB_DIR/'challenge.html').read_text()
        js=(WEB_DIR/'challenge.js').read_text()
        mission=(WEB_DIR/'mission3d.js').read_text()
        for needle in ('id="missionPanel"','id="missionCanvas"','/mission3d.js','id="missionLayout"','id="missionFollow"','id="missionReset"'):
            self.assertIn(needle,html)
        self.assertIn('new window.SATVV_MissionView',js)
        self.assertIn('mission.setOracle(current.oracle_after_run,truthShown)',js)
        self.assertIn('mission.focus(rec?.subsystem||null)',js)
        self.assertIn('if(this.showTruth)',mission)
        self.assertIn("this.truth=show?(oracle?.faults||[]):[]",mission)
        self.assertIn("draw(){",mission)
        self.assertIn('document.hidden',mission)
    def test_source_grounded_methods_guide(self):
        html=(WEB_DIR/'how-it-works.html').read_text()
        for needle in ('Isolation Forest','Gradient-Boosted Classifier','Random Forest Test Ranker','Bayesian Fault Hypotheses','CUSUM','Five Verification Strategies','uncalibrated','<table>'):
            self.assertIn(needle,html)
        reference=(WEB_DIR.parent/'docs/v0.9.9_models_and_algorithms.md').read_text()
        for needle in ('RandomForestClassifier','HistGradientBoostingClassifier','HistGradientBoostingRegressor','split-conformal','not a root-cause'):
            self.assertIn(needle.lower(),reference.lower())
    def test_server_route_declared(self):
        from inspect import getsource
        self.assertIn("'/mission3d.js'",getsource(PreviewHandler.do_GET))
    def test_model_without_oracle_fallback(self):
        js=(WEB_DIR/'mission3d.js').read_text()
        self.assertIn('this.showTruth=false',js)
        self.assertIn('this.showTruth=!!show',js)
    def test_all_original_routes_preserved(self):
        html=(WEB_DIR/'challenge.html').read_text()
        for path in ('/','/industry','/how-it-works','/#compare-workspace','/reference'):
            self.assertIn(f'href="{path}"',html)
