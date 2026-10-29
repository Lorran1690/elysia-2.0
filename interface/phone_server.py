"""Private authenticated gateway. Publish only through a private HTTPS tunnel."""
import argparse
import hmac
import os
import re
import secrets
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from interface.server import Handler, NeuralCore, ROOT

GET = {'/api/health', '/api/generation/status'}
POST = {'/api/chat', '/api/generation/probe', '/api/generation/start', '/api/generation/cancel', '/api/generation/resume'}

class PhoneHandler(Handler):
    def route_allowed(self, method):
        return (self.path in GET or bool(re.fullmatch(r'/api/generation/file/[A-Za-z0-9_-]{1,100}/[0-9]{1,4}', self.path))) if method == 'GET' else method == 'POST' and self.path in POST

    def allowed(self):
        return self.headers.get('Origin') in (None, 'https://localhost') and hmac.compare_digest(self.headers.get('Authorization', '').encode('utf-8'), ('Bearer ' + self.server.phone_token).encode('utf-8'))

    def end_headers(self):
        if self.headers.get('Origin') == 'https://localhost':
            self.send_header('Access-Control-Allow-Origin', 'https://localhost')
            self.send_header('Vary', 'Origin')
        super().end_headers()

    def do_OPTIONS(self):
        headers = {v.strip().lower() for v in self.headers.get('Access-Control-Request-Headers', '').split(',') if v.strip()}
        if self.headers.get('Origin') != 'https://localhost' or not self.route_allowed(self.headers.get('Access-Control-Request-Method')) or not headers <= {'authorization', 'content-type'}:
            return self.json_response(403, {'error': 'Origem ou operação não permitida.'})
        self.send_response(204)
        self.send_header('Access-Control-Allow-Methods', 'GET, POST')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_HEAD(self):
        self.send_response(405)
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_GET(self):
        if not self.allowed(): return self.json_response(401, {'error': 'Conexão não autorizada.'})
        if not self.route_allowed('GET'): return self.json_response(404, {'error': 'Operação não disponível.'})
        super().do_GET()

    def do_POST(self):
        if not self.allowed(): return self.json_response(401, {'error': 'Conexão não autorizada.'})
        if not self.route_allowed('POST'): return self.json_response(404, {'error': 'Operação não disponível.'})
        super().do_POST()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--token-file', type=Path, required=True)
    parser.add_argument('--init-token', action='store_true')
    args = parser.parse_args()
    if args.init_token:
        fd = os.open(args.token_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as out: out.write(secrets.token_urlsafe(32)+'\n')
        print('Chave privada criada; não a envie ao GitHub.')
        return
    token = args.token_file.read_text().strip()
    if not re.fullmatch(r'[A-Za-z0-9_-]{43,128}', token): parser.error('Arquivo de chave inválido.')
    core = NeuralCore(ROOT/'artifacts/aira-dialogue-v1/run-001/sft-model.pt')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), partial(PhoneHandler, core=core))
    # The desktop process has its own state.tmp/state.json; never race its writes.
    from actions.media_generation import MediaService
    from memory.vault import data_directory
    server.media_ai = MediaService(data_directory()/'phone-media-ai')
    server.phone_token = token
    print(f'Gateway em 127.0.0.1:{server.server_port}; use um túnel HTTPS privado.', flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__ == '__main__': main()
