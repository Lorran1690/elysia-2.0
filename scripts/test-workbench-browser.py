"""Verify Workbench and capability inventory in source or the real Windows EXE."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import time
import urllib.request
from playwright.sync_api import sync_playwright

parser=argparse.ArgumentParser();parser.add_argument('executable',nargs='?');parser.add_argument('--url');parser.add_argument('--output',type=Path,default=Path('.'))
args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
private=tempfile.TemporaryDirectory(prefix='elysia-workbench-test-');process=None;url=args.url or 'http://127.0.0.1:8765'
if args.executable:process=subprocess.Popen([str(Path(args.executable).resolve()),'--serve-test'],env={**os.environ,'ELYSIA_DATA_DIR':private.name})
try:
    deadline=time.monotonic()+90
    while True:
        try:
            with urllib.request.urlopen(url+'/api/health',timeout=2) as response:assert json.load(response)['ready']
            break
        except Exception:
            if time.monotonic()>deadline or process and process.poll() is not None:raise RuntimeError('App failed to start')
            time.sleep(.25)
    with sync_playwright() as pw:
        options={'headless':True}
        if os.environ.get('ELYSIA_CHROMIUM_PATH'):options['executable_path']=os.environ['ELYSIA_CHROMIUM_PATH']
        browser=pw.chromium.launch(**options)
        try:
            page=browser.new_page(viewport={'width':1280,'height':1000},accept_downloads=True);errors=[];external=[]
            page.add_init_script("sessionStorage.setItem('elysia.introSeen','1')")
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('request',lambda r:external.append(r.url) if r.url.startswith('http') and not r.url.startswith(url+'/') else None)
            page.goto(url,wait_until='networkidle');page.get_by_role('button',name='Bancada de análise',exact=True).click()
            original='import math\n\ndef twice(value):\n    return abs(value) * 2\n'
            proposal=original.replace('* 2','* 3')
            page.get_by_label('Código Python para análise',exact=True).fill(original)
            page.get_by_role('button',name='Extrair estrutura Python',exact=True).click()
            page.get_by_role('img',name='Grafo de chamadas sintáticas Python').wait_for()
            page.get_by_role('button',name='Selecionar twice',exact=True).click()
            assert 'def twice' in page.get_by_label('Código Python para análise').evaluate('(e)=>e.value.slice(e.selectionStart,e.selectionEnd)')
            page.get_by_role('tab',name='Revisão',exact=True).click()
            page.get_by_label('Proposta de código',exact=True).fill(proposal)
            page.get_by_role('button',name='Comparar versões',exact=True).click()
            page.get_by_label('Diferenças de código').filter(has_text='+    return abs(value) * 3').wait_for()
            page.get_by_role('button',name='Aceitar proposta no editor',exact=True).click()
            page.get_by_role('tab',name='Código Python',exact=True).click()
            assert page.get_by_label('Código Python para análise').input_value()==proposal
            page.get_by_role('tab',name='Revisão',exact=True).click();page.get_by_role('button',name='Desfazer aceitação',exact=True).click()
            page.get_by_role('tab',name='Código Python',exact=True).click()
            assert page.get_by_label('Código Python para análise').input_value()==original
            page.get_by_role('tab',name='Arquivo',exact=True).click()
            data=bytearray(1024);data[:2]=b'MZ';struct.pack_into('<I',data,60,128);data[128:132]=b'PE\0\0';struct.pack_into('<HHIIIHH',data,132,0x8664,1,0,0,0,0,0)
            struct.pack_into('<8sIIII',data,152,b'.test\0\0\0',512,0x1000,512,512)
            fixture=Path(private.name)/'synthetic-pe.bin';fixture.write_bytes(data);digest=hashlib.sha256(data).hexdigest()
            page.get_by_label('Arquivo para inspeção estática').set_input_files(fixture)
            page.get_by_label('Metadados do arquivo').filter(has_text='x64').wait_for()
            assert digest in page.locator('.workbench-hash').inner_text() and fixture.read_bytes()==data
            page.get_by_role('tab',name='Anotações',exact=True).click()
            note='Workbench synthetic private note '+Path(private.name).name
            page.get_by_label('Anotações da análise').fill(note)
            page.get_by_role('button',name='Salvar anotação no Vault',exact=True).click()
            page.get_by_role('status').filter(has_text='Anotação preservada').wait_for()
            with page.expect_download() as download:page.get_by_role('button',name='Exportar projeto de análise',exact=True).click()
            project=Path(private.name)/'project.json';download.value.save_as(project)
            assert json.loads(project.read_text(encoding='utf-8'))['notes']==note
            page.get_by_label('Anotações da análise').fill('changed')
            page.get_by_label('Restaurar projeto de análise').set_input_files(project)
            page.get_by_role('status').filter(has_text='Projeto restaurado.').wait_for()
            assert page.get_by_label('Anotações da análise').input_value()==note
            bad=json.loads(project.read_text(encoding='utf-8'));bad['fileReport']['name']={'unsafe':'invalid shape'}
            broken=Path(private.name)/'bad.json';broken.write_text(json.dumps(bad),encoding='utf-8')
            page.get_by_label('Restaurar projeto de análise').set_input_files(broken)
            page.get_by_role('alert').filter(has_text='Texto inválido no relatório').wait_for()
            page.get_by_role('button',name='Biblioteca · Knowledge Vault',exact=True).click()
            page.get_by_label('Buscar na biblioteca').fill('Workbench synthetic');page.get_by_role('button',name='Buscar',exact=True).click()
            page.locator('.vault-list li').filter(has_text=note).wait_for()
            page.get_by_role('button',name='Habilidades e evolução',exact=True).click()
            page.get_by_label('Buscar habilidade').fill('Voice Core')
            page.locator('.capability-status').filter(has_text='pausada').wait_for()
            with page.expect_download() as download:page.get_by_role('button',name='Exportar catálogo de habilidades',exact=True).click()
            cat=Path(private.name)/'catalog.json';download.value.save_as(cat)
            assert json.loads(cat.read_text(encoding='utf-8'))['voice_core_paused'] is True
            page.get_by_label('Buscar habilidade').fill('Bancada')
            page.locator('.capability-list article').filter(has=page.get_by_role('heading',name='Bancada de análise · referência Eleven',exact=True)).get_by_role('button',name='Abrir módulo',exact=True).click()
            page.get_by_role('heading',name='Bancada de análise',exact=True).wait_for()
            assert not errors and not external,(errors,external)
            page.screenshot(path=str(args.output/'workbench-browser.png'))
            report={'passed':True,'packaged_executable':bool(process),'python_structure_and_source_navigation':True,'review_accept_and_undo_in_editor':True,'pe_inspection_preserves_original':True,'project_export_restore_and_bad_shape_rejection':True,'vault_note_save_and_search':True,'capability_inventory_and_export':True,'selected_file_execution':False,'external_requests':external,'javascript_errors':errors}
            (args.output/'workbench-browser.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))
        finally:browser.close()
finally:
    if process:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait()
    private.cleanup()
