"""Render the actual packaged executable, instead of only checking its HTTP API."""
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright

process = subprocess.Popen([str(Path(sys.argv[1]).resolve()), '--serve-test'])
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
            page.screenshot(path='desktop-browser.png')
            Path('desktop-browser.json').write_text(json.dumps({
                'passed': True, 'packaged_executable': True, 'browser': 'Chromium',
                'first_launch_intro': True, 'visible_chat': True,
                'actual_checkpoint_response_visible': True, 'javascript_errors': errors,
                'quality_claim': False}, indent=2) + '\n', encoding='utf-8')
        finally:
            browser.close()
finally:
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
