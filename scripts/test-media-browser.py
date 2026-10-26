"""Verify actual media downloads and code editor in source or packaged browser UI."""
import argparse
import ast
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import time
import urllib.request
import wave

from playwright.sync_api import sync_playwright

parser=argparse.ArgumentParser()
parser.add_argument('executable',nargs='?')
parser.add_argument('--url')
parser.add_argument('--output',type=Path,default=Path('.'))
args=parser.parse_args()
args.output.mkdir(parents=True,exist_ok=True)
private=tempfile.TemporaryDirectory(prefix='elysia-media-test-')
process=None
url=args.url or 'http://127.0.0.1:8765'
if args.executable:
    process=subprocess.Popen([str(Path(args.executable).resolve()),'--serve-test'],env={**os.environ,'ELYSIA_DATA_DIR':private.name})
try:
    deadline=time.monotonic()+90
    while True:
        try:
            with urllib.request.urlopen(url+'/api/health',timeout=2) as response:
                assert json.load(response)['ready']
            break
        except Exception:
            if process and process.poll() is not None or time.monotonic()>deadline:
                raise RuntimeError('Media test server failed to start')
            time.sleep(.25)
    with sync_playwright() as playwright:
        options={'headless':True,'args':['--disable-gpu']}
        if os.environ.get('ELYSIA_CHROMIUM_PATH'):options['executable_path']=os.environ['ELYSIA_CHROMIUM_PATH']
        browser=playwright.chromium.launch(**options)
        try:
            page=browser.new_page(viewport={'width':1280,'height':1000},accept_downloads=True)
            page.add_init_script("if (window === window.top) sessionStorage.setItem('elysia.introSeen','1')")
            errors=[];external=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('request',lambda request:external.append(request.url) if request.url.startswith(('http:','https:')) and not request.url.startswith(url) else None)
            page.goto(url,wait_until='networkidle')
            page.get_by_role('button',name='Media Studio',exact=True).click()
            page.get_by_label('Título da composição',exact=True).fill('Elysia Studio Test')
            page.get_by_role('button',name='Gerar PNG',exact=True).click()
            page.locator('.studio-output img').wait_for()
            with page.expect_download() as download:page.get_by_role('button',name='Baixar arquivo gerado',exact=True).click()
            download.value.save_as(args.output/'media-sample.png')
            image=(args.output/'media-sample.png').read_bytes()
            assert image[:8]==b'\x89PNG\r\n\x1a\n'
            assert struct.unpack('>II',image[16:24])==(640,360)
            with page.expect_download() as download:page.get_by_role('button',name='Exportar projeto de mídia',exact=True).click()
            project=Path(private.name)/'project.json';download.value.save_as(project)
            assert json.loads(project.read_text(encoding='utf-8'))['format']=='elysia-studio-v1'
            page.get_by_role('tab',name='Áudio',exact=True).click()
            page.get_by_role('button',name='Gerar WAV',exact=True).click()
            page.locator('.studio-output audio').wait_for()
            with page.expect_download() as download:page.get_by_role('button',name='Baixar arquivo gerado',exact=True).click()
            download.value.save_as(args.output/'media-sample.wav')
            with wave.open(str(args.output/'media-sample.wav'),'rb') as audio:
                assert audio.getnchannels()==1 and audio.getsampwidth()==2 and audio.getframerate()==22050
                assert audio.getnframes()==66150
            page.get_by_role('tab',name='Vídeo',exact=True).click()
            page.get_by_label('Duração do vídeo',exact=True).fill('2')
            page.get_by_role('button',name='Gerar vídeo WebM',exact=True).click()
            page.locator('.studio-output video').wait_for(timeout=30000)
            page.wait_for_function("document.querySelector('.studio-output video')?.videoWidth > 0",timeout=30000)
            with page.expect_download() as download:page.get_by_role('button',name='Baixar arquivo gerado',exact=True).click()
            download.value.save_as(args.output/'media-sample.webm')
            video=(args.output/'media-sample.webm').read_bytes()
            assert video[:4]==b'\x1aE\xdf\xa3' and len(video)>1000
            # Verify the high quality path through the actual UI and decoder.
            page.get_by_label('Resolução da mídia',exact=True).select_option('1920x1080')
            page.get_by_label('Quadros por segundo',exact=True).select_option('60')
            page.get_by_role('button',name='Gerar vídeo WebM',exact=True).click()
            page.get_by_role('button',name='Cancelar exportação',exact=True).wait_for(state='hidden',timeout=30000)
            page.wait_for_function("document.querySelector('.studio-output video')?.videoWidth === 1920",timeout=30000)
            assert page.locator('.studio-output video').evaluate('(v)=>v.videoHeight')==1080
            with page.expect_download() as download:page.get_by_role('button',name='Baixar arquivo gerado',exact=True).click()
            download.value.save_as(args.output/'media-fullhd.webm')
            page.get_by_role('button',name='Gerar vídeo WebM',exact=True).click()
            page.get_by_role('button',name='Cancelar exportação',exact=True).click()
            page.get_by_role('alert').filter(has_text='cancelada').wait_for()
            page.get_by_label('Restaurar projeto de mídia',exact=True).set_input_files(project)
            page.get_by_role('tab',name='Imagem',exact=True).click()
            assert page.get_by_label('Título da composição',exact=True).input_value()=='Elysia Studio Test'
            page.get_by_role('button',name='Gerar PNG',exact=True).click()
            page.locator('.studio-output img').wait_for()
            # Exercise the folder bridge without claiming an actual Drive synchronization.
            page.evaluate('''() => {
              window._studioSave={permission:'granted',exists:false,bytes:0,closed:false};
              window.showDirectoryPicker=async()=>({name:'Drive-test-folder',
                requestPermission:async()=>window._studioSave.permission,queryPermission:async()=>window._studioSave.permission,
                getFileHandle:async(name,options)=>{
                  if(!options?.create&&!window._studioSave.exists)throw new DOMException('missing','NotFoundError');
                  return {createWritable:async()=>({write:async(blob)=>{window._studioSave.bytes=blob.size;},close:async()=>{window._studioSave.closed=true;},abort:async()=>{}})};
                }});
            }''')
            page.get_by_role('button',name='Selecionar pasta do Drive',exact=True).click()
            page.get_by_role('button',name='Salvar arquivo na pasta selecionada',exact=True).click()
            page.wait_for_function('window._studioSave.closed')
            assert page.evaluate('window._studioSave.bytes')>1000
            page.evaluate("window._studioSave.exists=true")
            page.get_by_role('button',name='Salvar arquivo na pasta selecionada',exact=True).click()
            page.get_by_role('status').filter(has_text='Já existe').wait_for()
            page.evaluate("window._studioSave.permission='denied'")
            page.get_by_role('button',name='Salvar arquivo na pasta selecionada',exact=True).click()
            page.get_by_role('status').filter(has_text='não concedida').wait_for()
            page.get_by_role('button',name='Código e ferramentas',exact=True).click()
            page.get_by_label('Nome do projeto de código',exact=True).fill('Studio Test')
            page.get_by_role('button',name='Criar modelo inicial',exact=True).click()
            page.get_by_role('button',name='Validar sintaxe',exact=True).click()
            page.get_by_role('status').filter(has_text='Sintaxe Python válida').wait_for()
            with page.expect_download() as download:page.get_by_role('button',name='Baixar código',exact=True).click()
            code=Path(private.name)/'script.py';download.value.save_as(code);ast.parse(code.read_text(encoding='utf-8'))
            page.get_by_label('Linguagem do código',exact=True).select_option('html')
            page.once('dialog',lambda dialog:dialog.accept())
            page.get_by_role('button',name='Criar modelo inicial',exact=True).click()
            page.get_by_role('button',name='Prévia HTML sem scripts',exact=True).click()
            page.frame_locator('iframe').get_by_role('heading',name='Studio Test').wait_for()
            page.get_by_label('Editor de código',exact=True).fill('<meta http-equiv="refresh" content="0;url=https://example.com"><script>parent._unsafe=true</script><h1>Local</h1>')
            page.get_by_role('button',name='Prévia HTML sem scripts',exact=True).click()
            page.frame_locator('iframe').get_by_role('heading',name='Local',exact=True).wait_for()
            assert page.evaluate('window._unsafe === undefined')
            assert not external,external
            assert not errors,errors
            page.get_by_role('button',name='Media Studio',exact=True).click()
            page.screenshot(path=str(args.output/'media-browser.png'))
            report={'passed':True,'packaged_executable':bool(process),'png_640x360_verified':True,
                'wav_pcm_22050_mono_verified':True,'webm_decodes_in_browser':True,'video_cancellation':True,
                'editable_project_roundtrip':True,'folder_write_and_collision_and_permission_mocked':True,
                'google_drive_cloud_sync_tested':False,'code_export_and_syntax_check':True,
                'html_preview_script_and_refresh_blocked':True,'external_requests':external,'javascript_errors':errors,
                'media_ai_model_used':False}
            (args.output/'media-browser.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
            print(json.dumps(report))
        finally:browser.close()
finally:
    if process:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait()
    private.cleanup()
