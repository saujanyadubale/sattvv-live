"""v0.9.5 public research pages and documented capability comparison."""
import json
import re
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen
from satvv.web_server import PreviewHandler

ROOT=Path(__file__).resolve().parents[1]
class ResearchPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),PreviewHandler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.thread.join(timeout=3);cls.server.server_close()
    def read(self,path):
        with urlopen(self.base+path) as resp:
            self.assertEqual(resp.status,200)
            return resp.read().decode('utf-8')
    def test_new_pages_have_live_navigation(self):
        page=self.read('/')
        self.assertIn('href="/how-it-works"',page)
        self.assertIn('href="/industry"',page)
        self.assertIn('href="/reference"',page)  # original catalog in archived classic view
        self.assertIn('v1.0',page)
    def test_guide_walkthrough_and_catalog(self):
        guide=self.read('/how-it-works')
        self.assertEqual(guide.count('role="tab"'),6)
        for s in ('walk-next','catalog-search','catalog-detail','/research.js','Forecast','Audit'):
            self.assertIn(s,guide)
    def test_industry_graphics_and_sources(self):
        page=self.read('/industry')
        for s in ('id="cap-matrix"','id="eco-detail"','role-map','source-cards','not a performance ranking'):
            self.assertIn(s,page)
        js=self.read('/research.js')
        for x in ('OpenC3 COSMOS','NASA NOS3','NASA ADAPT','NASA HyDE','OPS-SAT-AD','ECSS-E-ST-10-02C','SAT-V&V'):
            self.assertIn(x,js)
        self.assertIn('not assessed',js)
    def test_reference_endpoint_maps_20_actual_tests(self):
        ref=json.loads(self.read('/api/reference'))
        self.assertEqual(len(ref['procedures']),20)
        self.assertEqual(ref['procedures'][13]['id'],'T14')
        t14=ref['procedures'][13]
        self.assertIn('0.26 V',' '.join(r['specification'] for r in t14['requirements']))
        self.assertTrue(all(p['requirements'] for p in ref['procedures']))
        self.assertTrue(all(r['specification'] for p in ref['procedures'] for r in p['requirements']))
    def test_version_and_legacy_endpoints(self):
        self.assertEqual(json.loads(self.read('/api/health'))['version'],'1.0.0')
        self.assertIn('advancedScreen',self.read('/legacy'))
    def test_no_invented_external_performance_scores(self):
        src=self.read('/research.js')
        self.assertNotIn('performance_rating',src)
        self.assertIn('not assessed',src)

if __name__=='__main__':unittest.main()
