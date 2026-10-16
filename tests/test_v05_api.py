"""New HTTP API smoke tests; no internet access required."""
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from satvv.web_server import PreviewHandler

class V05Api(unittest.TestCase):
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
        req=Request(self.url+'/api/v05',data=json.dumps(data).encode(),
                    headers={'Content-Type':'application/json'},method='POST')
        with urlopen(req,timeout=20) as r:
            return json.loads(r.read())

    def test_v05_get_has_tab(self):
        with urlopen(self.url+'/legacy') as response:
            self.assertIn(b'Predictive health v0.5',response.read())

    def test_v05_http_health(self):
        d=self.post({'scenario':'sensor_drift','seed':7,'budget_min':20})
        self.assertEqual(len(d['test_catalog']),16)
        self.assertEqual(len(d['verification']),7)
        self.assertEqual(len(d['detectors']),6)
        self.assertEqual(d['meta']['scenario'],'sensor_drift')
        self.assertNotIn('truth',d)
        self.assertNotIn('fault',d['telemetry'][0])

    def test_invalid_scenario_returns_400(self):
        with self.assertRaises(HTTPError) as c:
            self.post({'scenario':'unknown'})
        self.assertEqual(c.exception.code,400)

    def test_extra_fields_rejected(self):
        with self.assertRaises(HTTPError) as c:
            self.post({'scenario':'healthy','hidden_truth':True})
        self.assertEqual(c.exception.code,400)

if __name__=='__main__':unittest.main()
