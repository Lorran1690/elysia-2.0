"""Loopback web interface for the project's own experimental dialogue model."""
from __future__ import annotations

import argparse
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from memory.vault import Vault
from actions.local_tools import run_tool
from actions.workbench import inspect_file, analyze_python, compare_sources
from actions.capabilities import catalog
from actions.media_generation import service as generation_service

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'interface/web'
MAX_BODY = 32768
MAX_VAULT_BODY = 64 * 1024 * 1024


def validate_messages(payload):
    messages = payload.get('messages') if isinstance(payload, dict) else None
    if not isinstance(messages, list) or not 1 <= len(messages) <= 31 or len(messages) % 2 != 1:
        raise ValueError('Envie uma conversa alternada terminando com uma mensagem sua.')
    for i, message in enumerate(messages):
        if (not isinstance(message, dict)
                or message.get('role') != ('user' if i % 2 == 0 else 'assistant')
                or not isinstance(message.get('content'), str)
                or not message['content'].strip() or len(message['content']) > 4000):
            raise ValueError('Mensagem inválida ou longa demais; inicie uma nova conversa.')
    return [{'role': m['role'], 'content': m['content']} for m in messages]


class NeuralCore:
    def __init__(self, checkpoint):
        import torch
        from learning.generate_text import load_inference_checkpoint
        torch.set_num_threads(2)
        metadata = torch.load(checkpoint, weights_only=True, map_location='cpu')
        if metadata.get('stage') != 'sft':
            raise ValueError('É necessário um checkpoint de diálogo (SFT).')
        self.model, self.tokenizer = load_inference_checkpoint(
            checkpoint, device=torch.device('cpu'),
            tokenizer_path=ROOT / 'data/corpus-pt-v1/tokenizer/elysia-bpe.json')
        self.lock = threading.Lock()

    def respond(self, messages):
        from learning.language_pilot import reply
        if not self.lock.acquire(blocking=False):
            raise BlockingIOError('Elysia está respondendo. Aguarde e tente novamente.')
        try:
            text = reply(self.model, self.tokenizer, messages, tokens=96, temperature=0).strip()
            if not text:
                raise ValueError('O modelo gerou uma resposta vazia. Tente outra pergunta.')
            return text
        finally:
            self.lock.release()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, core, vault=None, **kwargs):
        self.core = core
        self.vault = vault
        super().__init__(*args, directory=str(WEB), **kwargs)

    def log_message(self, format, *args):
        # Never log conversation bodies or query parameters.
        pass

    def allowed(self):
        expected = f'127.0.0.1:{self.server.server_port}'
        return (self.headers.get('Host') == expected
                and self.headers.get('Origin') in (None, f'http://{expected}'))

    def json_response(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self.allowed():
            return self.json_response(403, {'error': 'Origem não permitida.'})
        if self.path == '/api/health':
            return self.json_response(200, {'ready': True, 'model': 'Elysia · Aira pilot · experimental',
                                            'device': 'cpu', 'voice': False, 'modules': {'vault': self.vault is not None, 'tools': True}})
        if self.path == '/api/capabilities':
            return self.json_response(200, catalog())
        route = urlsplit(self.path)
        if route.path == '/api/generation/status':
            return self.json_response(200, generation_service(self.server).list())
        if route.path.startswith('/api/generation/file/'):
            try:
                pieces=route.path.split('/')
                if len(pieces)!=6:
                    raise ValueError('Arquivo não encontrado.')
                path,metadata=generation_service(self.server).file(pieces[4],int(pieces[5]))
                self.send_response(200)
                self.send_header('Content-Type',metadata['mime'])
                self.send_header('Content-Length',str(path.stat().st_size))
                self.send_header('Cache-Control','no-store')
                self.send_header('X-Content-Type-Options','nosniff')
                self.end_headers()
                with path.open('rb') as content:
                    while block:=content.read(1024*1024):
                        self.wfile.write(block)
                return
            except (ValueError,OSError):
                return self.json_response(404,{'error':'Arquivo não encontrado.'})
        if route.path in ('/api/vault', '/api/vault/backup'):
            try:
                if self.vault is None:
                    raise ValueError('Biblioteca não disponível.')
                if len(self.path) > 4096:
                    raise ValueError('Busca longa demais.')
                if route.path.endswith('/backup'):
                    return self.json_response(200, self.vault.backup())
                params = parse_qs(route.query)
                return self.json_response(200, {'items':self.vault.list(params.get('q',[''])[0],params.get('kind',[''])[0])})
            except ValueError as exc:
                return self.json_response(400, {'error':str(exc)})
            except Exception:
                return self.json_response(500, {'error':'Não foi possível ler a biblioteca local.'})
        # Serve only packaged UI assets, never repository files or directory listings.
        if self.path != '/' and not self.path.startswith(('/src/', '/assets/', '/vendor/')):
            return self.json_response(404, {'error': 'Não encontrado.'})
        resolved = Path(self.translate_path(self.path)).resolve()
        if not resolved.is_relative_to(WEB.resolve()) or resolved.is_dir() and self.path != '/':
            return self.json_response(404, {'error': 'Não encontrado.'})
        return super().do_GET()

    def do_POST(self):
        if not self.allowed():
            return self.json_response(403, {'error': 'Origem não permitida.'})
        if self.path not in ('/api/chat','/api/tools','/api/vault/save','/api/vault/delete','/api/vault/restore','/api/workbench/inspect','/api/workbench/source','/api/workbench/diff','/api/generation/probe','/api/generation/start','/api/generation/cancel','/api/generation/resume'):
            return self.json_response(404, {'error': 'Não encontrado.'})
        try:
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise ValueError('Use JSON.')
            size = int(self.headers.get('Content-Length', '0'))
            limit = MAX_VAULT_BODY if self.path == '/api/vault/restore' else (256 * 1024 if self.path in ('/api/tools','/api/vault/save') else MAX_BODY)
            if self.path == '/api/workbench/inspect':
                limit = 6 * 1024 * 1024
            elif self.path.startswith('/api/workbench/'):
                limit = 512 * 1024
            if not 0 < size <= limit:
                raise ValueError('Entrada grande demais para esta operação.')
            payload = json.loads(self.rfile.read(size))
            if self.path.startswith('/api/generation/'):
                if not isinstance(payload,dict):
                    raise ValueError('Solicitação inválida.')
                engine=generation_service(self.server)
                if self.path.endswith('/probe'):
                    return self.json_response(200,engine.probe(payload.get('port')))
                if self.path.endswith('/start'):
                    return self.json_response(200,engine.submit(payload))
                if self.path.endswith('/resume'):
                    return self.json_response(200,{'job':engine.resume(payload.get('id'))})
                return self.json_response(200,{'job':engine.cancel(payload.get('id'))})
            if self.path.startswith('/api/workbench/'):
                if not isinstance(payload,dict):
                    raise ValueError('Solicitação inválida.')
                if self.path.endswith('/inspect'):
                    return self.json_response(200, inspect_file(payload))
                if self.path.endswith('/source'):
                    return self.json_response(200, analyze_python(payload.get('text')))
                return self.json_response(200, compare_sources(payload.get('before'),payload.get('after')))
            if self.path == '/api/tools':
                return self.json_response(200, run_tool(payload))
            if self.path.startswith('/api/vault/'):
                if self.vault is None or not isinstance(payload,dict):
                    raise ValueError('Biblioteca indisponível ou solicitação inválida.')
                if self.path.endswith('/save'):
                    return self.json_response(200, {'item':self.vault.save(payload)})
                if self.path.endswith('/delete'):
                    self.vault.delete(payload.get('id'))
                    return self.json_response(200, {'deleted':True})
                return self.json_response(200, {'imported':self.vault.restore(payload)})
            messages = validate_messages(payload)
            text = self.core.respond(messages)
            return self.json_response(200, {'reply': text})
        except (ValueError, UnicodeDecodeError) as exc:
            return self.json_response(400, {'error': str(exc)})
        except BlockingIOError as exc:
            return self.json_response(409, {'error': str(exc)})
        except Exception:
            return self.json_response(500, {'error': 'Não foi possível concluir a operação local. Tente novamente ou reinicie o aplicativo.'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--checkpoint', type=Path,
                        default=ROOT / 'artifacts/aira-dialogue-v1/run-001/sft-model.pt')
    args = parser.parse_args()
    core = NeuralCore(args.checkpoint)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), partial(Handler, core=core, vault=Vault()))
    print(f'Elysia experimental: http://127.0.0.1:{server.server_port} — Ctrl+C encerra.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
