"""New interface contract; legacy views remain available under /legacy."""
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import urlopen
from satvv.web_server import PreviewHandler

class InterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1',0),PreviewHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.thread.join(timeout=3);cls.server.server_close()
    def get(self,uri):
        with urlopen(self.url+uri) as response:
            self.assertEqual(response.status,200)
            return response.read().decode()
    def test_three_workspaces(self):
        page=self.get('/classic')
        for key in ('id="experiment"','id="compare"','id="research"','id="advanced"'):
            self.assertIn(key,page)
        self.assertIn('lab.js',page)
    def test_catalog_contains_all_20(self):
        body=json.loads(self.get('/api/catalog'))
        self.assertEqual(len(body['procedures']),20)
        self.assertIn('T20',[p['id'] for p in body['procedures']])
    def test_legacy_is_preserved(self):
        legacy=self.get('/legacy')
        self.assertIn('advancedScreen',legacy)
        self.assertIn('updateResearchControls',legacy)
    def test_frontend_assets(self):
        self.assertIn('setup()',self.get('/lab.js'))
        self.assertIn('.stages',self.get('/style.css'))
