import sys,ssl,subprocess,tempfile,threading,secrets,json,mimetypes
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from interface.phone_server import PhoneHandler
from interface.server import NeuralCore,ROOT
from playwright.sync_api import sync_playwright
core=NeuralCore(ROOT/'artifacts/aira-dialogue-v1/run-001/sft-model.pt')
server=ThreadingHTTPServer(('127.0.0.1',0),partial(PhoneHandler,core=core))
server.phone_token=secrets.token_urlsafe(32)
output=ROOT/'reports/phone-connection';output.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='elysia-test-tls-') as temp:
 from actions.media_generation import MediaService
 server.media_ai=MediaService(Path(temp)/'media')
 key=Path(temp)/'key.pem';cert=Path(temp)/'cert.pem'
 subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=localhost'],check=True,capture_output=True)
 tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);tls.load_cert_chain(cert,key)
 server.socket=tls.wrap_socket(server.socket,server_side=True)
 thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 try:
  with sync_playwright() as p:
   browser=p.chromium.launch(executable_path=__import__('os').environ.get('ELYSIA_CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader','--disable-features=LocalNetworkAccessChecks'])
   context=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,ignore_https_errors=True)
   page=context.new_page();page.on('console',lambda m:print('BROWSER',m.type,m.text,flush=True) if m.type=='error' else None);page.on('requestfailed',lambda r:print('FAILED',r.url,r.failure,flush=True));errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
   def assets(route):
    from urllib.parse import urlsplit
    path=urlsplit(route.request.url).path
    file=ROOT/'desktop/dist'/path.lstrip('/') if path!='/' else ROOT/'desktop/dist/index.html'
    if not file.is_file():route.fulfill(status=404,body='');return
    route.fulfill(status=200,body=file.read_bytes(),content_type=mimetypes.guess_type(str(file))[0] or 'application/octet-stream')
   page.route('https://localhost/**',assets)
   page.goto('https://localhost/')
   nav=page.get_by_role('navigation',name='Navegação do telefone',exact=True)
   nav.get_by_role('button',name='Configurações',exact=True).click()
   page.get_by_label('Categoria de configurações',exact=True).select_option('system')
   page.get_by_label('Endereço HTTPS do computador',exact=True).fill('https://127.0.0.1:'+str(server.server_port))
   page.get_by_label('Chave privada do computador',exact=True).fill(server.phone_token)
   page.get_by_role('button',name='Conectar e testar',exact=True).click()
   
   try: page.get_by_role('status').filter(has_text='Conectado ao computador').wait_for(timeout=15000)
   except:
    print('STATUS',page.get_by_role('status').all_text_contents(),flush=True);raise
   nav.get_by_role('button',name='Conversas',exact=True).click()
   field=page.get_by_role('textbox',name='Mensagem',exact=True);field.wait_for()
   field.fill('Olá, Elysia. Esta é uma verificação sintética da conexão com meu computador.')
   page.get_by_role('button',name='Enviar mensagem',exact=True).click()
   reply=page.locator('.message-assistant p');reply.wait_for(timeout=180000)
   text=reply.inner_text();assert text.strip()
   page.screenshot(path=str(output/'real-core-conversation.png'))
   status=page.evaluate("async()=>{const r=await fetch('/api/generation/status');return {status:r.status,body:await r.json()}}")
   assert status['status']==200 and isinstance(status['body']['jobs'],list)
   nav.get_by_role('button',name='Configurações',exact=True).click()
   page.get_by_label('Categoria de configurações',exact=True).select_option('system')
   page.get_by_role('button',name='Desconectar',exact=True).click()
   nav.get_by_role('button',name='Conversas',exact=True).click()
   page.get_by_role('textbox',name='Mensagem',exact=True).wait_for(state='hidden')
   assert not errors,errors
   report={'passed':True,'actual_project_neural_core':True,'synthetic_prompt':True,'authenticated_generation_status':True,'disconnect_hides_composer':True,'reply_nonempty':True,'conversation_quality_evaluated':False,'real_https_socket':True,'app_origin':'https://localhost','browser_assets_served_by_test_route':True,'self_signed_certificate_accepted_only_in_test_context':True,'browser_local_network_permission_check_disabled_only_for_test':True,'actual_owner_phone_connected':False,'media_gpu_generation_evaluated':False,'javascript_errors':errors}
   (output/'browser-real-core.json').write_text(json.dumps(report,indent=2)+'\n')
   print(json.dumps(report));browser.close()
 finally:
  server.shutdown();server.server_close();thread.join()
