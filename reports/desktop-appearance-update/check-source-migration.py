"""Extra legacy migration and compact-window checks against the dev UI fixture.
Run backend and Vite as described in desktop/README.md before this script.
"""
import json,os,argparse
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:1420');a=parser.parse_args()
out=Path(__file__).resolve().parent
legacy={'palette':'gold','custom':{'from':'#112233','to':'#aabbcc'},'size':300,'speed':0,'morph':False,'avatar':'body','orbCount':1800,'holoCount':10000,'holoScale':.7,'greet':False}
with sync_playwright() as pw:
 options={'headless':True,'args':['--enable-unsafe-swiftshader']}
 if os.environ.get('ELYSIA_CHROMIUM_PATH'):options['executable_path']=os.environ['ELYSIA_CHROMIUM_PATH']
 b=pw.chromium.launch(**options)
 p=b.new_page(viewport={'width':850,'height':600})
 p.add_init_script('localStorage.setItem("elysia.appearance.v1",'+json.dumps(json.dumps(legacy))+')')
 p.goto(a.url)
 p.get_by_text('Vamos criar',exact=False).wait_for()
 p.wait_for_timeout(1000)
 prefs=p.evaluate('JSON.parse(localStorage.getItem("elysia.interface.v2")).prefs.appearance')
 assert prefs['speed']==0 and prefs['palette']=='gold' and prefs['avatar']=='body' and not prefs['greet'],prefs
 p.get_by_role('button',name='Configurações',exact=True).click()
 p.get_by_role('button',name='Aparência',exact=True).click()
 p.get_by_label('Forma da presença',exact=True).select_option('avatar')
 p.get_by_role('button',name='Paleta Gelo',exact=True).click()
 p.wait_for_timeout(650)
 p.reload()
 p.get_by_role('button',name='Configurações',exact=True).click()
 p.get_by_role('button',name='Aparência',exact=True).click()
 assert p.get_by_label('Forma da presença',exact=True).input_value()=='avatar'
 expect(p.get_by_role('button',name='Paleta Gelo',exact=True)).to_have_attribute('aria-pressed','true')
 p.get_by_label('Tamanho do texto',exact=True).evaluate("e=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,'125');e.dispatchEvent(new Event('input',{bubbles:true}));}")
 p.get_by_role('button',name='Ver no centro',exact=True).click()
 d=p.get_by_role('dialog',name='No centro do seu espaço',exact=True)
 expect(d.get_by_role('button',name='Fechar visualização central',exact=True)).to_be_in_viewport()
 expect(d.get_by_role('button',name='Ajustar à tela',exact=True)).to_be_in_viewport()
 p.keyboard.press('Control+k')
 assert not p.get_by_role('dialog',name='Busca no aplicativo').count()
 p.keyboard.press('Escape')
 expect(d).not_to_be_visible()
 b.close()
result={'passed':True,'actual_tauri_webview2':False,'legacy_preferences_migrated':True,'new_private_preferences_win_over_legacy':True,'center_controls_visible_at_850x600_and_125_percent_text':True,'center_blocks_background_shortcut':True}
(out/'source-migration-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
