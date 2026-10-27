"""Test updater visual states with a simulated native bridge in a browser.

Requires the Vite dev server. No Rust, GitHub network, downloads or installers
are used here; Windows CI separately checks the immutable real Tauri bridge.
"""
import argparse,json,os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:1420');args=parser.parse_args()
with sync_playwright() as pw:
 options={'headless':True}
 if os.environ.get('ELYSIA_CHROMIUM_PATH'):options['executable_path']=os.environ['ELYSIA_CHROMIUM_PATH']
 browser=pw.chromium.launch(**options);page=browser.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.add_init_script("""(()=>{
  let stored=null, next=0;const callbacks=new Map(),listeners=new Map();
  window.isTauri=true;window.__updateCalls=[];window.__clearFixtureStore=()=>{stored=null};
  const current={supported:true,installed:true,current_version:'2.2.0',current_build:9,current_source:'0'.repeat(40),status:'up-to-date',candidate:null};
  window.__TAURI_INTERNALS__={metadata:{currentWindow:{label:'main'},currentWebview:{label:'main'}},
   transformCallback(fn){callbacks.set(++next,fn);return next},
   unregisterCallback(id){callbacks.delete(id)},
   async invoke(cmd,args){
    if(cmd==='updater_info')return current;
    if(cmd==='read_interface_store')return stored;
    if(cmd==='write_interface_store'){stored=args.value;return}
    if(cmd==='core_request')return {status:200,mime:'application/json',body:Array.from(new TextEncoder().encode(JSON.stringify({ready:true})))};
    if(cmd==='plugin:window|set_theme')return;
    if(cmd==='plugin:event|listen'){listeners.set(args.event,args.handler);return next}
    if(cmd==='plugin:event|unlisten')return;
    if(cmd==='check_update'){window.__updateCalls.push(cmd);return {...current,status:'available',candidate:{version:'2.2.1',build:10,source_sha:'a'.repeat(40),tag:'native-'+ 'a'.repeat(12),bytes:1000000,sha256:'b'.repeat(64),release_url:'https://github.com/Lorran1690/elysia-2.0/releases/tag/native-'+ 'a'.repeat(12)}}}
    if(cmd==='download_update'){window.__updateCalls.push(cmd);const fn=callbacks.get(listeners.get('elysia-update-progress'));fn?.({event:'elysia-update-progress',id:1,payload:{stage:'downloading',downloaded:500000,total:1000000}});await new Promise(r=>setTimeout(r,500));return {verified:true,version:'2.2.1',build:10,bytes:1000000,sha256:'b'.repeat(64)}}
    if(cmd==='install_update'){window.__updateCalls.push(cmd);if(!stored)throw Error('Store was not flushed before installation');throw Error('Fixture: instalação impedida para manter o teste aberto.')}
    throw Error('Unexpected fixture command: '+cmd)
   }};
 })();""")
 page.goto(args.url);page.get_by_text('Vamos criar',exact=False).wait_for()
 assert page.evaluate('window.__updateCalls')==[]
 page.get_by_role('button',name='Atualizar Elysia',exact=True).click()
 page.get_by_role('button',name='Baixar atualização',exact=True).wait_for()
 assert page.evaluate('window.__updateCalls')==['check_update']
 page.get_by_role('button',name='Baixar atualização',exact=True).click()
 expect(page.get_by_role('progressbar',name='Progresso da atualização')).to_have_attribute('value','50')
 page.get_by_role('button',name='Fechar Elysia e instalar',exact=True).wait_for()
 page.evaluate('window.__clearFixtureStore()')
 page.get_by_role('button',name='Fechar Elysia e instalar',exact=True).click()
 page.get_by_role('alert').filter(has_text='Fixture: instalação impedida').wait_for()
 assert page.evaluate('window.__updateCalls')==['check_update','download_update','install_update']
 assert not errors,errors
 browser.close()
result={'passed':True,'actual_tauri_webview2':False,'all_native_commands_simulated':True,'github_network_download_and_installer_executed':False,'manual_check_only':True,'available_download_progress_verified_and_install_states':True,'private_store_flushed_before_install':True,'javascript_errors':errors}
Path(__file__).with_name('source-updater-fixture.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
