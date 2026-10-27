"""Validate the compiled interface in Chromium or the real Tauri WebView2 window."""
import argparse,json,os,subprocess,tempfile,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
parser=argparse.ArgumentParser();parser.add_argument('--native',type=Path);parser.add_argument('--url',default='http://127.0.0.1:1420');parser.add_argument('--output',type=Path,default=Path('reports/native-desktop'));a=parser.parse_args();a.output.mkdir(parents=True,exist_ok=True)
process=None;browser=None
private=tempfile.TemporaryDirectory(prefix='elysia-native-check-')
try:
 with sync_playwright() as pw:
  if a.native:
   env={**os.environ,'ELYSIA_DATA_DIR':private.name,'WEBVIEW2_USER_DATA_FOLDER':str(Path(private.name)/'webview'),'WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS':'--remote-debugging-port=9223 --enable-unsafe-swiftshader'}
   process=subprocess.Popen([str(a.native.resolve())],env=env)
   deadline=time.monotonic()+120
   while True:
    try:
     browser=pw.chromium.connect_over_cdp('http://127.0.0.1:9223');break
    except Exception:
     if time.monotonic()>deadline or process.poll() is not None:raise RuntimeError('Native WebView2 failed to open')
     time.sleep(.4)
   page=browser.contexts[0].pages[0]
  else:
   options={'headless':True,'args':['--enable-unsafe-swiftshader']}
   if os.environ.get('ELYSIA_CHROMIUM_PATH'):options['executable_path']=os.environ['ELYSIA_CHROMIUM_PATH']
   browser=pw.chromium.launch(**options);page=browser.new_page(viewport={'width':1440,'height':960},accept_downloads=True);page.goto(a.url)
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.get_by_text('Vamos criar',exact=False).wait_for(timeout=60000)
  if a.native:assert page.evaluate('!!window.__TAURI_INTERNALS__')
  page.locator('.local-indicator').filter(has_text='Núcleo local conectado').wait_for(timeout=90000)
  page.screenshot(path=str(a.output/'conversation.png'))
  page.get_by_label('Mensagem',exact=True).fill('Olá')
  page.get_by_role('button',name='Enviar mensagem',exact=True).click()
  page.locator('.message-assistant').wait_for(timeout=120000)
  assert page.locator('.message-assistant p').inner_text().strip()
  page.get_by_role('button',name='Configurações',exact=True).click()
  page.get_by_role('button',name='Aparência',exact=True).click()
  page.get_by_role('button',name='Luz',exact=True).click()
  page.wait_for_function("document.documentElement.dataset.theme==='light'")
  page.get_by_role('button',name='Noite',exact=True).click()
  page.get_by_role('button',name='Som e música',exact=True).click()
  page.get_by_role('button',name='Reproduzir música',exact=True).click()
  page.wait_for_function("document.querySelector('audio[data-owner=elysia-background]').currentTime > .2",timeout=20000)
  page.get_by_label('Volume da música',exact=True).evaluate("e=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,'37');e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));}")
  page.wait_for_function("document.querySelector('audio').volume===.37")
  page.get_by_role('button',name='Órbita tranquila',exact=False).click()
  page.wait_for_function("document.querySelector('audio').currentSrc.includes('orbita.mp3') && !document.querySelector('audio').paused")
  page.screenshot(path=str(a.output/'settings-audio.png'))
  page.get_by_role('button',name='Pausar música',exact=True).click()
  page.wait_for_function("document.querySelector('audio').paused")
  page.get_by_role('button',name='Geral',exact=True).click()
  page.get_by_role('checkbox',name='Mostrar presença da Elysia',exact=False).uncheck()
  page.get_by_role('button',name='Conversas',exact=True).first.click()
  assert not page.locator('.presence-pane').count()
  page.get_by_role('button',name='Biblioteca',exact=True).click()
  page.get_by_label('Título do registro',exact=True).fill('Nota da interface nativa')
  page.get_by_label('Conteúdo do registro',exact=True).fill('Fixture privada para verificar o Vault existente.')
  page.get_by_role('button',name='Salvar registro',exact=True).click()
  page.locator('.vault-list li').filter(has_text='Nota da interface nativa').wait_for()
  page.get_by_role('button',name='Desenvolvimento',exact=True).click()
  assert page.get_by_label('Editor de código',exact=True).is_visible()
  assert not page.get_by_role('tab',name='Ferramentas',exact=True).count()
  page.get_by_role('tab',name='Utilitários',exact=True).click()
  page.get_by_label('Entrada da ferramenta',exact=True).fill('17*3')
  page.get_by_role('button',name='Executar ferramenta',exact=True).click()
  page.get_by_label('Resultado da ferramenta',exact=True).filter(has_text='51').wait_for()
  page.get_by_role('tab',name='Análise e revisão',exact=True).click()
  page.get_by_label('Código Python para análise',exact=True).fill('def dobro(x):\n    return abs(x)*2\n')
  page.get_by_role('button',name='Extrair estrutura Python',exact=True).click()
  page.get_by_role('img',name='Grafo de chamadas sintáticas Python').wait_for()
  page.get_by_role('button',name='Criação',exact=True).click()
  page.get_by_role('tab',name='Composição e áudio',exact=True).click()
  assert not page.get_by_role('tab',name='Abrir arquivo',exact=True).count()
  page.get_by_role('button',name='Gerar PNG',exact=True).click()
  page.get_by_role('button',name='Baixar arquivo gerado',exact=True).wait_for()
  page.get_by_role('tab',name='Geração por IA',exact=True).click()
  assert page.get_by_role('button',name='Diagnosticar motor e modelos',exact=True).is_visible()
  page.keyboard.press('Control+k')
  page.get_by_role('dialog',name='Busca no aplicativo').wait_for()
  page.get_by_label('Buscar ferramentas e conversas',exact=True).fill('Olá')
  page.locator('.palette-results button').filter(has_text='Olá').click()
  assert page.locator('.message-assistant').is_visible()
  assert not errors,errors
  # Wait for the debounced SQLite/browser write before checking persistence.
  page.wait_for_timeout(900)
  if a.native:
   try:page.evaluate("window.__TAURI_INTERNALS__.invoke('plugin:window|close',{label:'main'})")
   except Exception:pass
   process.wait(timeout=30)
   browser.close();browser=None
   process=subprocess.Popen([str(a.native.resolve())],env=env)
   deadline=time.monotonic()+90
   while True:
    try:browser=pw.chromium.connect_over_cdp('http://127.0.0.1:9223');break
    except Exception:
     if time.monotonic()>deadline:raise RuntimeError('Native relaunch failed')
     time.sleep(.4)
   page=browser.contexts[0].pages[0]
   page.locator('.message-assistant').wait_for(timeout=60000)
   assert not page.locator('.presence-pane').count()
   assert not page.evaluate("!window.__TAURI_INTERNALS__")
   try:page.evaluate("window.__TAURI_INTERNALS__.invoke('plugin:window|close',{label:'main'})")
   except Exception:pass
   process.wait(timeout=30)
  else:
   page.reload();page.locator('.message-assistant').wait_for();assert not page.locator('.presence-pane').count()
  report={'passed':True,'actual_tauri_webview2':bool(a.native),'source_neural_core_simulated':not bool(a.native),'chat_and_history_persistence':True,'theme_switch':True,'real_audio_playback_volume_track_pause':True,'vault_save':True,'code_tools_and_analysis':True,'redundant_editor_and_preview_tabs_removed':True,'composition_png':True,'command_search':True,'javascript_errors':errors,'realistic_video_quality_evaluated':False}
  (a.output/'ui-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
finally:
 if browser:
  try:browser.close()
  except Exception:pass
 if process and process.poll() is None:process.terminate();process.wait(timeout=15)
 private.cleanup()
