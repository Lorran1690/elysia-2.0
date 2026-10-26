"""Render the actual packaged executable, instead of only checking its HTTP API."""
import json
import os
import tempfile
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright

private = tempfile.TemporaryDirectory(prefix='elysia-modules-test-')
process = subprocess.Popen([str(Path(sys.argv[1]).resolve()), '--serve-test'],
    env={**os.environ, 'ELYSIA_DATA_DIR':private.name})
try:
    deadline = time.monotonic() + 90
    while True:
        try:
            with urllib.request.urlopen('http://127.0.0.1:8765/api/health', timeout=2) as response:
                assert json.load(response)['ready']
            break
        except Exception:
            if process.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError('Packaged server failed to start')
            time.sleep(.25)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(args=['--disable-gpu'])
        try:
            page = browser.new_page(viewport={'width': 1280, 'height': 900})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
            page.goto('http://127.0.0.1:8765', wait_until='domcontentloaded')
            page.get_by_role('button', name='Pular', exact=True).click(timeout=30000)
            page.get_by_role('button', name='Conversa por texto', exact=True).click()
            page.get_by_label('Mensagem', exact=True).fill('Olá')
            page.get_by_role('button', name='Enviar', exact=True).click()
            page.locator('.msg-elysia').wait_for(timeout=60000)
            page.wait_for_function("!document.querySelector('.pill-btn.ghost').disabled", timeout=60000)
            assert page.locator('.msg-elysia p').inner_text().strip()
            assert page.locator('#startup').count() == 0
            assert not errors, errors
            page.get_by_role('button', name='Biblioteca · Knowledge Vault', exact=True).click()
            page.get_by_label('Título do registro', exact=True).fill('Nota de teste')
            page.get_by_label('Conteúdo do registro', exact=True).fill('Café e informações de teste.')
            page.get_by_role('button', name='Salvar registro', exact=True).click()
            page.locator('.vault-list li').wait_for()
            page.get_by_label('Buscar na biblioteca', exact=True).fill('cafe')
            page.get_by_role('button', name='Buscar', exact=True).click()
            assert page.locator('.vault-list li').inner_text().startswith('Nota de teste')
            with page.expect_download() as download:
                page.get_by_role('button', name='Exportar biblioteca', exact=True).click()
            backup = Path(private.name)/'export.json'
            download.value.save_as(backup)
            page.reload(wait_until='domcontentloaded')
            page.get_by_role('button', name='Biblioteca · Knowledge Vault', exact=True).click()
            page.locator('.vault-list li').wait_for()
            page.once('dialog', lambda dialog: dialog.accept())
            page.get_by_role('button', name='Excluir', exact=True).click()
            page.wait_for_function("document.querySelectorAll('.vault-list li').length === 0")
            page.get_by_label('Restaurar biblioteca', exact=True).set_input_files(backup)
            page.locator('.vault-list li').wait_for()
            page.get_by_role('button', name='Código e ferramentas', exact=True).click()
            page.get_by_label('Entrada da ferramenta', exact=True).fill('6*3')
            page.get_by_role('button', name='Executar ferramenta', exact=True).click()
            assert page.get_by_label('Resultado da ferramenta', exact=True).inner_text() == '18'
            page.get_by_role('button', name='Media Studio', exact=True).click()
            page.get_by_label('Abrir mídia local', exact=True).set_input_files('interface/web/assets/avatar-ref.png')
            page.wait_for_function("document.querySelector('.media-preview img')?.naturalWidth > 0")
            assert not errors, errors
            page.get_by_role('button', name='Biblioteca · Knowledge Vault', exact=True).click()
            page.locator('.vault-list li').wait_for()
            page.screenshot(path='desktop-browser.png')
            Path('desktop-browser.json').write_text(json.dumps({
                'passed': True, 'packaged_executable': True, 'browser': 'Chromium',
                'first_launch_intro': True, 'visible_chat': True,
                'actual_checkpoint_response_visible': True, 'javascript_errors': errors,
                'vault_save_search_reload': True, 'private_backup_roundtrip': True,
                'calculator': True, 'local_image_preview': True, 'quality_claim': False}, indent=2) + '\n', encoding='utf-8')
        finally:
            browser.close()
finally:
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    private.cleanup()
