"""Validate the compiled interface in Chromium or the real Tauri WebView2 window."""
import argparse,contextlib,json,os,sqlite3,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
parser=argparse.ArgumentParser();parser.add_argument('--native',type=Path);parser.add_argument('--url',default='http://127.0.0.1:1420');parser.add_argument('--output',type=Path,default=Path('reports/native-desktop'));a=parser.parse_args();a.output.mkdir(parents=True,exist_ok=True)
process=None;browser=None;page=None;errors=[]
private=tempfile.TemporaryDirectory(prefix='elysia-native-check-')
note_title='Nota interface '+Path(private.name).name
@contextlib.contextmanager
def preserve_failure_diagnostics():
 try:
  yield
 except BaseException as failure:
  # This context exits before sync_playwright(), so the failing page is still
  # available. Every capture is best effort; never replace the original error.
  details={'exception_type':type(failure).__name__,'exception':str(failure),'javascript_errors':list(errors),'urls':[],'capture_errors':[]}
  try:
   available=[]
   if browser:
    try:
     available=[p for context in browser.contexts for p in context.pages if not p.is_closed()]
     details['urls']=[p.url for p in available]
    except Exception as error:details['capture_errors'].append('targets: '+str(error))
   candidate=page if page and not page.is_closed() else next(iter(available),None)
   if candidate:
    details['page_url']=candidate.url
    try:candidate.screenshot(path=str(a.output/'failure.png'),timeout=5000)
    except Exception as error:details['capture_errors'].append('screenshot: '+str(error))
    try:
     visible=candidate.locator('body').inner_text(timeout=3000)
     (a.output/'failure-visible.txt').write_text(visible[:100000],encoding='utf-8')
    except Exception as error:details['capture_errors'].append('visible_text: '+str(error))
   details['javascript_errors']=list(errors)
   details['process_returncode']=process.poll() if process else None
   (a.output/'failure-diagnostics.json').write_text(json.dumps(details,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  except Exception as error:
   print('Could not preserve failure diagnostics: '+str(error),file=sys.stderr)
  raise
def wait_js(page,expression,timeout=30000):
 # Scheduled browser-side eval in wait_for_function violates strict CSP in
 # WebView2. Use explicit CDP evaluations without weakening the app policy.
 deadline=time.monotonic()+timeout/1000
 while True:
  if page.evaluate(expression):return
  if time.monotonic()>deadline:raise AssertionError('Condition timed out: '+expression)
  page.wait_for_timeout(100)
def app_page(browser):
 deadline=time.monotonic()+45
 while True:
  for context in browser.contexts:
   if not context.pages:
    try:context.wait_for_event('page',timeout=1000)
    except PlaywrightTimeout:pass
   for page in context.pages:
    try:
     # These protocol waits pump CDP events; cached .url + time.sleep does not.
     page.wait_for_url('**tauri.localhost**',wait_until='domcontentloaded',timeout=2500)
     return page
    except PlaywrightTimeout:pass
  if time.monotonic()>deadline:
   targets=[p.url for c in browser.contexts for p in c.pages]
   (a.output/'native-targets.json').write_text(json.dumps(targets,indent=2))
   raise RuntimeError('Native application target did not load: '+repr(targets))
  if browser.contexts and browser.contexts[0].pages:browser.contexts[0].pages[0].wait_for_timeout(100)
  else:time.sleep(.1)
try:
 with sync_playwright() as pw, preserve_failure_diagnostics():
  if a.native:
   env={**os.environ,'ELYSIA_DATA_DIR':private.name,'WEBVIEW2_USER_DATA_FOLDER':str(Path(private.name)/'webview'),'ELYSIA_E2E':'1'}
   process=subprocess.Popen([str(a.native.resolve())],env=env)
   deadline=time.monotonic()+120
   while True:
    try:
     browser=pw.chromium.connect_over_cdp('http://127.0.0.1:9223');break
    except Exception:
     if time.monotonic()>deadline or process.poll() is not None:raise RuntimeError('Native WebView2 failed to open')
     time.sleep(.4)
   page=app_page(browser)
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
  wait_js(page,"document.documentElement.dataset.theme==='light'")
  original_font=page.locator('.settings-content h2').evaluate('e=>parseFloat(getComputedStyle(e).fontSize)')
  page.get_by_label('Tamanho do texto',exact=True).evaluate("e=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,'125');e.dispatchEvent(new Event('input',{bubbles:true}));}")
  assert abs(page.locator('.settings-content h2').evaluate('e=>parseFloat(getComputedStyle(e).fontSize)')-original_font*1.25)<.1
  page.get_by_label('Tamanho do texto',exact=True).evaluate("e=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,'100');e.dispatchEvent(new Event('input',{bubbles:true}));}")
  page.get_by_role('button',name='Noite',exact=True).click()
  page.get_by_role('button',name='Som e música',exact=True).click()
  page.get_by_role('button',name='Reproduzir música',exact=True).click()
  wait_js(page,"document.querySelector('audio[data-owner=elysia-background]').currentTime > .2",timeout=20000)
  page.get_by_label('Volume da música',exact=True).evaluate("e=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,'37');e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));}")
  wait_js(page,"document.querySelector('audio').volume===.37")
  page.get_by_role('button',name='Órbita tranquila',exact=False).click()
  wait_js(page,"document.querySelector('audio').currentSrc.includes('orbita.mp3') && !document.querySelector('audio').paused")
  page.screenshot(path=str(a.output/'settings-audio.png'))
  page.get_by_role('button',name='Pausar música',exact=True).click()
  wait_js(page,"document.querySelector('audio').paused")
  page.get_by_role('button',name='Geral',exact=True).click()
  page.get_by_role('checkbox',name='Mostrar presença da Elysia',exact=False).uncheck()
  page.get_by_role('button',name='Conversas',exact=True).first.click()
  assert not page.locator('.presence-pane').count()
  page.get_by_role('button',name='Biblioteca',exact=True).click()
  page.get_by_label('Título do registro',exact=True).fill(note_title)
  page.get_by_label('Conteúdo do registro',exact=True).fill('Fixture privada para verificar o Vault existente.')
  page.get_by_role('button',name='Salvar registro',exact=True).click()
  page.locator('.vault-list li').filter(has_text=note_title).wait_for()
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
  # An unreadable history must never be replaced by a fresh empty store.
  if a.native:
   connection=sqlite3.connect(Path(private.name)/'interface.sqlite3')
   saved=connection.execute("SELECT value FROM preferences WHERE key='interface-v2'").fetchone()[0]
   connection.execute("UPDATE preferences SET value=? WHERE key='interface-v2'",('invalid-fixture',));connection.commit();connection.close()
  else:
   saved=page.evaluate("localStorage.getItem('elysia.interface.v2')")
   page.evaluate("localStorage.setItem('elysia.interface.v2','invalid-fixture')")
  page.reload();page.get_by_role('alert').filter(has_text='Gravação automática suspensa').wait_for();page.wait_for_timeout(900)
  if a.native:
   connection=sqlite3.connect(Path(private.name)/'interface.sqlite3')
   assert connection.execute("SELECT value FROM preferences WHERE key='interface-v2'").fetchone()[0]=='invalid-fixture'
   connection.execute("UPDATE preferences SET value=? WHERE key='interface-v2'",(saved,));connection.commit();connection.close()
  else:
   assert page.evaluate("localStorage.getItem('elysia.interface.v2')")=='invalid-fixture'
   page.evaluate("s=>localStorage.setItem('elysia.interface.v2',s)",saved)
  page.reload();page.locator('.message-assistant').wait_for();assert not page.locator('.presence-pane').count()
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
   page=app_page(browser)
   page.locator('.message-assistant').wait_for(timeout=60000)
   assert not page.locator('.presence-pane').count()
   assert not page.evaluate("!window.__TAURI_INTERNALS__")
   try:page.evaluate("window.__TAURI_INTERNALS__.invoke('plugin:window|close',{label:'main'})")
   except Exception:pass
   process.wait(timeout=30)
  else:
   page.reload();page.locator('.message-assistant').wait_for();assert not page.locator('.presence-pane').count()
  report={'passed':True,'actual_tauri_webview2':bool(a.native),'source_neural_core_simulated':not bool(a.native),'chat_and_history_persistence':True,'failed_restore_does_not_overwrite_history':True,'theme_switch':True,'interface_text_scaling':True,'real_audio_playback_volume_track_pause':True,'vault_save':True,'code_tools_and_analysis':True,'redundant_editor_and_preview_tabs_removed':True,'composition_png':True,'command_search':True,'javascript_errors':errors,'realistic_video_quality_evaluated':False}
  (a.output/'ui-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
finally:
 if browser:
  try:browser.close()
  except Exception:pass
 if process and process.poll() is None:
  if os.name=='nt':subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True)
  else:process.terminate()
  process.wait(timeout=15)
 deadline=time.monotonic()+20
 while True:
  try:private.cleanup();break
  except OSError:
   if time.monotonic()>deadline:print('Temporary WebView profile cleanup deferred to the runner.');break
   time.sleep(.2)
