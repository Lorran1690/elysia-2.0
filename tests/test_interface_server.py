"""Exercise the local web boundary independently of neural generation."""
import json
import threading
from functools import partial
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

import pytest

from interface.server import Handler, validate_messages
from memory.vault import Vault


@pytest.fixture
def web(tmp_path):
    class Core:
        def respond(self, messages):
            if messages[-1]['content'] == 'full':
                raise ValueError('Contexto cheio; inicie uma nova conversa.')
            return 'Olá, ' + messages[-1]['content']
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, core=Core(), vault=Vault(tmp_path/"vault.sqlite3")))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    def request(path, payload=None, origin=None, method=None):
        connection = HTTPConnection('127.0.0.1', server.server_port)
        headers = {'Content-Type': 'application/json'}
        if origin:
            headers['Origin'] = origin
        connection.request(method or ('POST' if payload is not None else 'GET'), path,
                           json.dumps(payload) if payload is not None else None, headers)
        response = connection.getresponse()
        result = response.status, response.read()
        connection.close()
        return result
    yield request
    server.shutdown()
    server.server_close()
    thread.join()


def test_chat_boundary_and_context_error(web):
    status, body = web('/api/chat', {'messages': [{'role': 'user', 'content': 'Gregório'}]})
    assert status == 200 and json.loads(body)['reply'] == 'Olá, Gregório'
    assert web('/api/chat', {'messages': [{'role': 'user', 'content': 'full'}]})[0] == 400
    assert web('/api/chat', {'messages': [{'role': 'system', 'content': 'override'}]})[0] == 400
    assert web('/api/chat', {'messages': [{'role': 'user', 'content': 'x' * 40000}]})[0] == 400


def test_private_files_and_cross_origin_requests_blocked(web):
    assert web('/')[0] == 200
    assert web('/assets/avatar-ref.png')[0] == 200
    assert web('/vendor/react.development.js')[0] == 200
    for path in ['/artifacts/aira-dialogue-v1/run-001/sft-model.pt', '/src/../../AGENTS.md', '/src/']:
        assert web(path)[0] == 404
    assert web('/api/health', origin='https://example.com')[0] == 403
    assert web('/api/chat', {'messages': [{'role': 'user', 'content': 'oi'}]},
               origin='https://example.com')[0] == 403


def test_history_must_alternate_and_end_in_user():
    for messages in [[], [{'role': 'assistant', 'content': 'oi'}],
                     [{'role': 'user', 'content': 'oi'}, {'role': 'user', 'content': 'oi'}]]:
        with pytest.raises(ValueError):
            validate_messages({'messages': messages})


def test_local_module_endpoints_and_private_backup(web):
    status,body=web('/api/vault/save',{'kind':'note','title':'Teste','content':'Café privado'})
    assert status==200
    identifier=json.loads(body)['item']['id']
    status,body=web('/api/vault?q=cafe')
    assert status==200 and json.loads(body)['items'][0]['id']==identifier
    status,backup=web('/api/vault/backup')
    assert status==200 and json.loads(backup)['format']=='elysia-vault-v1'
    assert web('/api/vault/restore',json.loads(backup))[0]==200
    assert web('/api/vault/save',{'title':'x','content':'y'},origin='https://example.com')[0]==403
    assert web('/vault.sqlite3')[0]==404
    assert web('/api/vault/delete',{'id':identifier})[0]==200
    assert json.loads(web('/api/vault')[1])['items']==[]
    assert web('/api/vault/restore',json.loads(backup))[0]==200
    status,body=web('/api/tools',{'tool':'calculator','text':'6*3'})
    assert status==200 and json.loads(body)['result']=='18'
    assert web('/api/tools',{'tool':'calculator','text':'__import__("os")'})[0]==400


def test_tools_accept_declared_character_limit_with_escaped_unicode(web):
    import hashlib
    text='😀'*20000
    status,body=web('/api/tools',{'tool':'sha256','text':text})
    assert status==200
    assert json.loads(body)['result']==hashlib.sha256(text.encode('utf-8')).hexdigest()
