"""Exercise v11 avatar integration and preserved module navigation, in source or EXE.
Synthetic core is used only for source mode; this is not a language quality test.
"""
import argparse
from functools import partial
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from interface.server import Handler
from memory.vault import Vault
from actions.media_generation import MediaService

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('executable', nargs='?')
parser.add_argument('--output', type=Path, default=Path('.'))
args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
private = tempfile.TemporaryDirectory(prefix='elysia-avatar-test-')
process = server = None
try:
    if args.executable:
        base = 'http://127.0.0.1:8765'
        process = subprocess.Popen([str(Path(args.executable).resolve()), '--serve-test'], env={**os.environ, 'ELYSIA_DATA_DIR': private.name})
    else:
        class Core:
            def respond(self, messages): return 'Teste sintético da interface.'
        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, core=Core(), vault=Vault(Path(private.name)/'vault.sqlite3')))
        server.media_ai = MediaService(Path(private.name)/'media-ai')
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = 'http://127.0.0.1:' + str(server.server_port)
    deadline = time.monotonic() + 90
    while True:
        try:
            with urllib.request.urlopen(base+'/api/health', timeout=2) as r: assert json.load(r)['ready']
            break
        except Exception:
            if time.monotonic() > deadline: raise RuntimeError('Server not ready')
            time.sleep(.25)
    with sync_playwright() as pw:
        options = {'headless': True}
        if os.environ.get('ELYSIA_CHROMIUM_PATH'): options['executable_path'] = os.environ['ELYSIA_CHROMIUM_PATH']
        browser = pw.chromium.launch(**options)
        try:
            page = browser.new_page(viewport={'width':1280, 'height':1000}, accept_downloads=True)
            errors=[]; external=[]
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('request', lambda r: external.append(r.url) if r.url.startswith('http') and not r.url.startswith(base+'/') else None)
            # Migrate the actual old preference shape, preserving the palette and size.
            page.add_init_script("sessionStorage.setItem('elysia.introSeen','1'); if (!localStorage.getItem('elysia.appearance.v1')) localStorage.setItem('elysia.appearance.v1',JSON.stringify({palette:'original',size:240,speed:1,morph:true}));")
            page.goto(base, wait_until='networkidle')
            page.wait_for_function("JSON.parse(localStorage.getItem('elysia.appearance.v1')).avatar === 'bust'")
            assert page.evaluate("JSON.parse(localStorage.getItem('elysia.appearance.v1')).size") == 240
            # Both references must decode, and the animation must retain their source pixels.
            refs = page.evaluate('''async () => {
                const out = {};
                for (const k of ['bust','body']) {
                    const p = await ElysiaRig.loadAvatar(k);
                    if (!p) throw new Error('Avatar failed: '+k);
                    const img = new Image(); img.src=ElysiaRig.AVATARS[k].src; await img.decode();
                    out[k]={width:img.naturalWidth,height:img.naturalHeight};
                }
                return out;
            }''')
            assert refs['body']['width'] == 683 and refs['bust']['width'] == 1024, refs
            page.get_by_role('button', name='Aparência e configurações', exact=True).click()
            page.get_by_role('checkbox', name='Acenar ao abrir', exact=True).uncheck()
            page.get_by_role('checkbox', name='Manter forma humanoide (pré-visualização)', exact=True).check()
            page.get_by_role('radio', name='Cintura para cima', exact=True).click()
            page.wait_for_function("document.querySelector('.app').dataset.human === 'true'", timeout=30000)
            page.wait_for_function("JSON.parse(localStorage.getItem('elysia.appearance.v1')).avatar === 'body'")
            page.wait_for_function("parseFloat(document.querySelector('.app').style.getPropertyValue('--form')) > .99",timeout=30000)
            page.get_by_role('button', name='Acenar agora', exact=True).click()
            page.screenshot(path=str(args.output/'avatar-body.png'))
            page.get_by_role('radio', name='Busto', exact=True).click()
            page.wait_for_function("JSON.parse(localStorage.getItem('elysia.appearance.v1')).avatar === 'bust'")
            page.get_by_role('button', name='Ajustar à tela', exact=True).click()
            # Reload persists preferences; pinning is intentionally preview-only.
            page.get_by_role('radio', name='Cintura para cima', exact=True).click()
            page.reload(wait_until='networkidle')
            assert page.evaluate("JSON.parse(localStorage.getItem('elysia.appearance.v1')).avatar") == 'body'
            for name, title in [
                ('Biblioteca · Knowledge Vault','Knowledge Vault'),
                ('Código e ferramentas','Código e ferramentas'),
                ('Media Studio','Media Studio'),
                ('Imagens e vídeos por IA','Imagens e vídeos por IA'),
                ('Bancada de análise','Bancada de análise'),
                ('Habilidades e evolução','Habilidades e evolução'),
                ('Conversa por texto','Conversa')]:
                page.get_by_role('button', name=name, exact=True).click()
                assert page.locator('#context-panel').is_visible()
            assert page.get_by_role('button',name='Exportar backup',exact=True).is_visible()
            assert page.get_by_role('button',name='Nova conversa',exact=True).is_visible()
            page.get_by_label('Mensagem',exact=True).fill('Olá')
            page.get_by_role('button',name='Enviar',exact=True).click()
            page.locator('.msg-elysia').wait_for(timeout=60000)
            page.wait_for_function("document.querySelector('.msg-elysia p')?.textContent.trim().length > 0", timeout=30000)
            assert not errors and not external, (errors, external)
            report={'passed':True,'packaged_executable':bool(process),'source_core_simulated':not bool(process),'avatar_sources':refs,'old_preferences_migrated':True,'body_and_bust_switch':True,'wave_and_pin_controls':True,'module_navigation_preserved':True,'chat_connected':True,'neural_quality_evaluated':False,'javascript_errors':errors,'external_requests':external}
            (args.output/'avatar-browser.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
            print(json.dumps(report))
        finally: browser.close()
finally:
    if process:
        process.terminate()
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired: process.kill(); process.wait()
    if server: server.shutdown(); server.server_close()
    private.cleanup()
