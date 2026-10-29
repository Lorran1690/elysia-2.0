"""Exercise authentication and remote boundary over an actual HTTP socket."""
import json
import threading
import unittest
from functools import partial
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from interface.phone_server import PhoneHandler

class Core:
    def __init__(self): self.calls = []
    def respond(self, messages):
        self.calls.append(messages)
        return 'Synthetic transport fixture, not model inference'

class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.core = Core()
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), partial(PhoneHandler, core=self.core))
        self.server.phone_token = 'a'*43
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()
    def call(self, method, path, body=None, token=None, origin='https://localhost', extra=None):
        c = HTTPConnection('127.0.0.1', self.server.server_port)
        headers = {'Origin': origin, 'Content-Type': 'application/json', **(extra or {})}
        if token: headers['Authorization'] = 'Bearer '+token
        c.request(method, path, json.dumps(body) if body is not None else None, headers)
        r = c.getresponse(); data = r.read(); result = (r.status, dict(r.getheaders()), data); c.close()
        return result
    def test_unauthorized_requests_never_reach_model(self):
        payload={'messages':[{'role':'user','content':'Synthetic test'}]}
        for token in [None, 'wrong']:
            self.assertEqual(self.call('POST','/api/chat',payload,token)[0],401)
        self.assertEqual(self.call('POST','/api/chat',payload,'a'*43,origin='https://attacker.invalid')[0],401)
        self.assertEqual(self.call('HEAD','/index.html')[0],405)
        self.assertEqual(self.core.calls,[])
    def test_authenticated_chat_and_private_routes(self):
        payload={'messages':[{'role':'user','content':'Synthetic test'}]}
        status,headers,body=self.call('POST','/api/chat',payload,'a'*43)
        self.assertEqual(status,200);self.assertEqual(len(self.core.calls),1)
        self.assertEqual(headers['Access-Control-Allow-Origin'],'https://localhost')
        self.assertIn('Synthetic transport fixture',json.loads(body)['reply'])
        for route in ['/api/vault','/api/vault/export','/','/api/health?token=secret','/api/generation/file/../0']:
            self.assertEqual(self.call('GET',route,token='a'*43)[0],404)
        self.assertEqual(self.call('POST','/api/vault/save',{},'a'*43)[0],404)
    def test_preflight_allows_only_app_and_explicit_operations(self):
        args={'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'authorization,content-type'}
        self.assertEqual(self.call('OPTIONS','/api/chat',extra=args)[0],204)
        self.assertEqual(self.call('OPTIONS','/api/chat',origin='https://attacker.invalid',extra=args)[0],403)
        self.assertEqual(self.call('OPTIONS','/api/vault/save',extra=args)[0],403)

if __name__=='__main__': unittest.main()
