"""Loopback web interface for the project's own experimental dialogue model."""
from __future__ import annotations

import argparse
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'interface/web'
MAX_BODY = 32768


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
    def __init__(self, *args, core, **kwargs):
        self.core = core
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
                                            'device': 'cpu', 'voice': False})
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
        if self.path != '/api/chat':
            return self.json_response(404, {'error': 'Não encontrado.'})
        try:
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise ValueError('Use JSON.')
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= MAX_BODY:
                raise ValueError('Conversa longa demais; inicie uma nova conversa.')
            messages = validate_messages(json.loads(self.rfile.read(size)))
            text = self.core.respond(messages)
            return self.json_response(200, {'reply': text})
        except (ValueError, UnicodeDecodeError) as exc:
            return self.json_response(400, {'error': str(exc)})
        except BlockingIOError as exc:
            return self.json_response(409, {'error': str(exc)})
        except Exception:
            return self.json_response(500, {'error': 'Falha no núcleo. Tente novamente ou reinicie o servidor.'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--checkpoint', type=Path,
                        default=ROOT / 'artifacts/aira-dialogue-v1/run-001/sft-model.pt')
    args = parser.parse_args()
    core = NeuralCore(args.checkpoint)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), partial(Handler, core=core))
    print(f'Elysia experimental: http://127.0.0.1:{server.server_port} — Ctrl+C encerra.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
