"""Public-hosting adapter: same SAT-V&V original HTML and Python simulation API.

No changes to source simulator, validation criteria, fault generator or policies.
The local preview server remains available as before.
"""
from __future__ import annotations
from io import BytesIO
from http.server import ThreadingHTTPServer
import json
import os
import threading
import time
from .web_server import PreviewHandler

_semaphore = threading.BoundedSemaphore(int(os.environ.get('SATVV_MAX_COMPUTE', '3')))
_rate_lock = threading.Lock()
_recent_requests = []
MAX_POSTS_PER_MINUTE = int(os.environ.get('SATVV_POSTS_PER_MINUTE','60'))

class PublicHandler(PreviewHandler):
    server_version = 'SATVV/1.0.3'
    sys_version = ''
    def end_headers(self):
        # Parent iframe restricted to the official portfolio and our service itself.
        self.send_header('Content-Security-Policy', "frame-ancestors 'self' https://saujanyadubale.github.io")
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        self.send_header('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        super().end_headers()

    def do_GET(self):
        if self.path == '/api/health':
            return self._send(200, b'{"ok":true,"version":"1.0.3","mode":"public"}', 'application/json')
        # Original frontend and its known read-only API GET paths.
        return super().do_GET()

    def do_POST(self):
        try:
            size = int(self.headers.get('Content-Length','0'))
            if size < 1 or size > 8192:
                return self._reject(413, 'Invalid request length')
            raw = self.rfile.read(size)
            obj = json.loads(raw)
            if type(obj) is not dict:
                return self._reject(400, 'Expected JSON object')
            for k, (lo, hi) in {
                'budget_min':(1,90), 'seed':(0,1000000), 'onset_s':(0,7200),
                'fault_start_s':(0,7200), 'duration_s':(1,7200),
                'step_s':(10,600), 'horizon_s':(120,600),
            }.items():
                if k in obj and (type(obj[k]) is not int or not lo<=obj[k]<=hi):
                    return self._reject(400, k+' outside public bounds')
            for k,(lo,hi) in {
                'severity':(0,3), 'initial_soc':(.1,1.0),
            }.items():
                if k in obj and (type(obj[k]) not in (int,float) or not lo<=obj[k]<=hi):
                    return self._reject(400, k+' outside public bounds')
            if 'horizon_s' in obj and obj['horizon_s'] not in (120,300,600):
                return self._reject(400,'Invalid forecast horizon')
            # Only fixed finite compute sizes allowed; no arbitrary injected code.
            if obj.get('policy') and obj['policy'] not in (
                'fixed','random','model_fixed','adaptive','scheduled_retest',
                'temporal_blind','temporal_adaptive','information_gain',
                'learned_risk','predictive_active','predictive_greedy_v101',
            ):
                return self._reject(400,'Unsupported policy')
        except (ValueError,TypeError,json.JSONDecodeError):
            return self._reject(400,'Malformed JSON')
        now=time.monotonic()
        with _rate_lock:
            _recent_requests[:]=[t for t in _recent_requests if now-t<60]
            if len(_recent_requests)>=MAX_POSTS_PER_MINUTE:
                return self._reject(429,'Server busy: public rate limit reached',retry=True)
            _recent_requests.append(now)
        if not _semaphore.acquire(blocking=False):
            return self._reject(429,'Server busy: simulation concurrency limit reached',retry=True)
        try:
            self.rfile=BytesIO(raw)
            return super().do_POST()
        except Exception:
            # Do not leak internal stack traces or file paths to public users.
            try:
                return self._reject(500,'Simulation failed; please retry with other parameters')
            except (OSError,BrokenPipeError):
                pass
        finally:
            _semaphore.release()

    def _reject(self,code:int,message:str,retry:bool=False):
        payload=json.dumps({'error':message}).encode()
        self.send_response(code)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(payload)))
        self.send_header('Cache-Control','no-store')
        if retry: self.send_header('Retry-After','10')
        self.end_headers()
        self.wfile.write(payload)

def main():
    port=int(os.environ.get('PORT','10000'))
    if not 1024<=port<=65535: raise ValueError('Invalid port')
    host='0.0.0.0'
    httpd=ThreadingHTTPServer((host,port),PublicHandler)
    httpd.daemon_threads=True
    print(f'SAT-V&V v1.0.3 live server listening on {host}:{port}',flush=True)
    try: httpd.serve_forever(poll_interval=.25)
    finally: httpd.server_close()

if __name__=='__main__': main()
