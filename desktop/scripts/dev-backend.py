"""Isolated UI test fixture. Does not load or evaluate a neural model."""
import sys,tempfile,threading
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from interface.server import Handler
from memory.vault import Vault
from actions.media_generation import MediaService
class Core:
 def respond(self,messages):return 'Resposta sintética para testar a interface. Não avalia inteligência.'
with tempfile.TemporaryDirectory(prefix='elysia-ui-fixture-') as tmp:
 server=ThreadingHTTPServer(('127.0.0.1',8765),partial(Handler,core=Core(),vault=Vault(Path(tmp)/'vault.sqlite3')))
 server.media_ai=MediaService(Path(tmp)/'media-ai')
 print('UI fixture ready',flush=True)
 try:server.serve_forever()
 finally:server.server_close()
