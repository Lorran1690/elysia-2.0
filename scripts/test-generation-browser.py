"""Exercise the actual app's AI adapter with a SIMULATED ComfyUI, not model quality."""
import argparse
from functools import partial
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import zlib
from playwright.sync_api import sync_playwright
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from interface.server import Handler
from memory.vault import Vault
from actions.media_generation import MediaService


def png():
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\x00\x60\x80\xb0'))+chunk(b'IEND',b'')

parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('executable',nargs='?');parser.add_argument('--output',type=Path,default=Path('.'));args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
private=tempfile.TemporaryDirectory(prefix='elysia-generation-browser-');state={'hold':False,'graphs':[],'cancelled':[]};pixel=png()
class Motor(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def respond(self,data):
        body=json.dumps(data).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):
        if self.path=='/system_stats':return self.respond({'devices':[{'name':'SIMULATED GPU','type':'cuda','vram_total':8*1024**3}]})
        if self.path.startswith('/object_info/'):
            name=self.path.rsplit('/',1)[-1];keys={'CheckpointLoaderSimple':'ckpt_name','UNETLoader':'unet_name','CLIPLoader':'clip_name','VAELoader':'vae_name'}
            return self.respond({name:{'input':{'required':{keys[name]:[['fixture.safetensors']]} if name in keys else {}}}})
        if self.path.startswith('/history/'):
            identifier=self.path.rsplit('/',1)[-1]
            return self.respond({} if state['hold'] else {identifier:{'status':{'completed':True,'status_str':'success'},'outputs':{'7':{'images':[{'filename':'fixture.png','subfolder':'','type':'output'}]}}}})
        if self.path.startswith('/view?'):
            self.send_response(200);self.end_headers();self.wfile.write(pixel);return
        self.respond({})
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))))
        if self.path=='/prompt':state['graphs'].append(body['prompt']);return self.respond({'prompt_id':'fixture-'+str(len(state['graphs']))})
        if self.path.startswith('/api/jobs/'):state['cancelled'].append(self.path)
        self.respond({'cancelled':True})
motor=ThreadingHTTPServer(('127.0.0.1',0),Motor);mt=threading.Thread(target=motor.serve_forever,daemon=True);mt.start();process=None;server=None
try:
    if args.executable:
        base='http://127.0.0.1:8765';process=subprocess.Popen([str(Path(args.executable).resolve()),'--serve-test'],env={**os.environ,'ELYSIA_DATA_DIR':private.name})
    else:
        class Core:
            def respond(self,messages):return 'Synthetic adapter test; neural quality not evaluated.'
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,core=Core(),vault=Vault(Path(private.name)/'vault.sqlite3')))
        server.media_ai=MediaService(Path(private.name)/'media-ai');threading.Thread(target=server.serve_forever,daemon=True).start();base='http://127.0.0.1:'+str(server.server_port)
    deadline=time.monotonic()+90
    while True:
        try:
            with urllib.request.urlopen(base+'/api/health',timeout=2) as response:assert json.load(response)['ready']
            break
        except Exception:
            if time.monotonic()>deadline or process and process.poll() is not None:raise RuntimeError('App failed to start')
            time.sleep(.25)
    with sync_playwright() as pw:
        options={'headless':True}
        if os.environ.get('ELYSIA_CHROMIUM_PATH'):options['executable_path']=os.environ['ELYSIA_CHROMIUM_PATH']
        browser=pw.chromium.launch(**options)
        try:
            page=browser.new_page(accept_downloads=True,viewport={'width':1280,'height':1000});errors=[];external=[]
            page.add_init_script("sessionStorage.setItem('elysia.introSeen','1')")
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('request',lambda r:external.append(r.url) if r.url.startswith('http') and not r.url.startswith(base+'/') else None)
            page.goto(base,wait_until='networkidle')
            with page.expect_response(lambda response:response.url.endswith('/api/generation/status')):page.get_by_role('button',name='Imagens e vídeos por IA',exact=True).click()
            page.get_by_label('Porta do motor de mídia').fill(str(motor.server_port));page.get_by_role('button',name='Diagnosticar motor e modelos',exact=True).click()
            page.get_by_role('status').filter(has_text='Motor conectado').wait_for()
            page.get_by_role('tab',name='Vídeo por IA',exact=True).click()
            assert page.get_by_label('Resolução por IA').input_value()=='384x256'
            assert page.get_by_label('Quadros do vídeo por IA').input_value()=='17'
            assert 'dolly shot' in page.get_by_label('Descrição da cena por IA').input_value()
            page.get_by_role('tab',name='Imagem por IA',exact=True).click()
            page.get_by_label('Checkpoint de imagem').select_option('fixture.safetensors')
            page.get_by_role('button',name='Gerar com modelo de IA',exact=True).click()
            page.get_by_role('button',name='Abrir resultado',exact=True).wait_for(timeout=30000)
            page.get_by_role('button',name='Abrir resultado',exact=True).click()
            page.wait_for_function("document.querySelector('img[alt=\"Resultado do modelo de imagem\"]')?.naturalWidth === 1")
            with page.expect_download() as download:page.get_by_role('button',name='Baixar resultado da IA',exact=True).click()
            output=Path(private.name)/'download.png';download.value.save_as(output);assert output.read_bytes()==pixel
            with page.expect_download() as download:page.get_by_role('button',name='Exportar metadados',exact=True).click()
            metadata=Path(private.name)/'metadata.json';download.value.save_as(metadata);assert json.loads(metadata.read_text(encoding='utf-8'))['params']['seed']==1650
            page.get_by_role('button',name='Gerar com modelo de IA',exact=True).click()
            page.get_by_role('status').filter(has_text='trabalho anterior reutilizado').wait_for();assert len(state['graphs'])==1
            state['hold']=True
            page.get_by_text('Seed e parâmetros',exact=True).click();page.get_by_label('Seed da geração',exact=True).fill('1651')
            page.get_by_role('button',name='Gerar com modelo de IA',exact=True).click()
            page.get_by_role('button',name='Cancelar este trabalho',exact=True).wait_for(timeout=30000)
            page.get_by_role('button',name='Cancelar este trabalho',exact=True).click()
            page.get_by_text('Imagem · cancelado',exact=True).wait_for(timeout=30000)
            assert state['cancelled'] and all('/api/jobs/' in path for path in state['cancelled'])
            assert state['graphs'][0]['5']['inputs']['seed']==1650
            assert not errors and not external,(errors,external)
            report={'passed':True,'packaged_executable':bool(process),'engine_simulated':True,'realistic_quality_evaluated':False,'connection_model_selection_generation_download':True,'local_low_memory_video_profile':True,'metadata_export_seed':True,'same_seed_reuses_result':True,'targeted_cancellation':True,'javascript_errors':errors,'external_requests':external}
            (args.output/'generation-browser.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))
        finally:browser.close()
finally:
    if process:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait()
    if server:server.shutdown();server.server_close()
    motor.shutdown();motor.server_close();mt.join();private.cleanup()
