"""Exercise the local web boundary independently of neural generation."""
import json
import threading
from functools import partial
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

import pytest

from interface.server import Handler, validate_messages


@pytest.fixture
def web():
    class Core:
        def respond(self, messages):
            if messages[-1]['content'] == 'full':
                raise ValueError('Contexto cheio; inicie uma nova conversa.')
            return 'Olá, ' + messages[-1]['content']
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, core=Core()))
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
