"""v1.0 beta presentation/provenance contracts; scientific algorithms remain unchanged."""
import json
import unittest
from pathlib import Path
from satvv.web_server import PreviewHandler, WEB_DIR
ROOT=WEB_DIR.parent

class BetaPresentationTests(unittest.TestCase):
    def test_3d_asset_renderer_and_graceful_fallback(self):
        page=(WEB_DIR/'challenge.html').read_text()
        js=(WEB_DIR/'mission_beta.js').read_text()
        for term in ('/mission_beta.js', '/mission3d.js', 'missionGlbUpload','missionAsset','missionAssetStatus','Compact 6U CubeSat', 'http'):
            self.assertIn(term,page)
        for term in ('GLTFLoader','WebGLRenderer','loadCustom','renderModel(buildConceptual())','setOracle','applyOracle','reveal','record?.status','HYP'):
            self.assertIn(term,js)
        self.assertLess(page.index('src="/mission3d.js"'),page.index('src="/mission_beta.js"'))
        self.assertIn('NASA ICECube 3D model source',page)
    def test_workflow_has_explicit_feedback_and_offline_learning(self):
        page=(WEB_DIR/'how-it-works.html').read_text()
        for word in ('SYSTEM ARCHITECTURE','LIVE CAMPAIGN','OFFLINE LEARNING','Spacecraft simulator',
                     'Anomaly monitors','Forecast risk','Choose next test','Run test','Evidence check',
                     'Feedback loop','/workflow_beta.js'):
            self.assertIn(word,page)
        self.assertEqual(page.count('data-architecture='),10)
        self.assertIn('not calibrated', (WEB_DIR/'workflow_beta.js').read_text())
    def test_industry_contribution_language(self):
        html=(WEB_DIR/'industry.html').read_text()
        self.assertIn('Research contribution: evidence-driven verification decisions',html)
        self.assertNotIn('not a claim of invention',html)
        self.assertIn('not a performance ranking',html)
    def test_existing_methods_are_still_documented(self):
        guide=(WEB_DIR/'how-it-works.html').read_text()
        for method in ('Isolation Forest','Gradient-Boosted Classifier','Random Forest Test Ranker','CUSUM','Bayesian Fault Hypotheses'):
            self.assertIn(method,guide)
    def test_server_exposes_beta_assets_and_version(self):
        from inspect import getsource
        source=getsource(PreviewHandler.do_GET)
        for route in ('/workflow_beta.js','/mission_beta.js','/mission3d.js'):
            self.assertIn(route,source)
        self.assertIn('1.0.0',source)

if __name__=='__main__':unittest.main()
