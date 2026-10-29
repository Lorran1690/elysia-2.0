"""Responsive Android frontend checks with actual local IndexedDB APIs.

Start Vite in android mode first. No Python core, network API or mock neural
response is used. The browser matrix emulates screen sizes, not physical phones.
"""
import argparse
import contextlib
import json
import os
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright, expect
from mobile_ui_checks import (
    assert_phone_layout, capture_failure, check_center, check_mobile_api,
    check_music_and_png, check_phone_navigation, check_vault_and_tools,
    navigate, settings, wait_js,
)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url', default='http://127.0.0.1:1420')
parser.add_argument('--output', type=Path, default=Path('reports/android-browser'))
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
browser = page = None
errors = []
requests = []
sizes = [(320, 568), (360, 800), (390, 844), (430, 932), (844, 390)]
# CI starts Vite as a background process. Wait for this owned app URL instead
# of making success depend on shell/process startup timing.
deadline = time.monotonic() + 45
while True:
    try:
        with urllib.request.urlopen(args.url, timeout=2) as response:
            if response.status == 200:
                break
    except Exception:
        if time.monotonic() >= deadline:
            raise RuntimeError('The Android frontend server did not start: ' + args.url)
    time.sleep(.2)
@contextlib.contextmanager
def diagnostics():
    try:
        yield
    except BaseException as failure:
        capture_failure(page, args.output, failure)
        raise

try:
    with sync_playwright() as pw, diagnostics():
        options = {'headless': True, 'args': ['--enable-unsafe-swiftshader']}
        if os.environ.get('ELYSIA_CHROMIUM_PATH'):
            options['executable_path'] = os.environ['ELYSIA_CHROMIUM_PATH']
        browser = pw.chromium.launch(**options)
        for width, height in sizes:
            context = browser.new_context(viewport={'width': width, 'height': height}, is_mobile=True, has_touch=True, device_scale_factor=1, accept_downloads=True)
            page = context.new_page()
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('request', lambda r: requests.append(r.url) if '/api/' in r.url else None)
            page.goto(args.url)
            page.get_by_role('navigation', name='Navegação do telefone', exact=True).wait_for()
            check_mobile_api(page)
            check_phone_navigation(page)
            assert_phone_layout(page, f'{width}x{height}:chat')
            page.screenshot(path=str(args.output / f'phone-{width}x{height}.png'))
            check_center(page, args.output / f'center-{width}x{height}.png')
            settings(page, 'appearance')
            page.get_by_label('Tamanho do texto', exact=True).evaluate("e=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,'125');e.dispatchEvent(new Event('input',{bubbles:true}));}")
            for category in ['appearance', 'general', 'conversation', 'audio', 'accessibility', 'data', 'system', 'about']:
                page.get_by_label('Categoria de configurações', exact=True).select_option(category)
                assert_phone_layout(page, f'{width}x{height}:settings:{category}:125%')
            for label in ['Biblioteca', 'Desenvolvimento', 'Criação']:
                navigate(page, label)
                assert_phone_layout(page, f'{width}x{height}:{label}:125%')
            context.close()
        context = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, accept_downloads=True)
        page = context.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('request', lambda r: requests.append(r.url) if '/api/' in r.url else None)
        page.goto(args.url)
        page.get_by_role('navigation', name='Navegação do telefone', exact=True).wait_for()
        results = check_vault_and_tools(page, args.output)
        results.update(check_music_and_png(page, args.output))
        settings(page, 'appearance')
        page.get_by_label('Forma da presença', exact=True).select_option('avatar')
        page.get_by_label('Modelo do avatar', exact=True).select_option('body')
        page.get_by_role('button', name='Paleta Gelo', exact=True).click()
        page.wait_for_timeout(650)
        page.reload()
        page.get_by_role('navigation', name='Navegação do telefone', exact=True).wait_for()
        settings(page, 'appearance')
        assert page.get_by_label('Forma da presença', exact=True).input_value() == 'avatar'
        assert page.get_by_label('Modelo do avatar', exact=True).input_value() == 'body'
        expect(page.get_by_role('button', name='Paleta Gelo', exact=True)).to_have_attribute('aria-pressed', 'true')
        navigate(page, 'Biblioteca')
        field = page.get_by_label('Buscar na biblioteca', exact=True)
        field.focus()
        page.evaluate("""()=>{Object.defineProperty(visualViewport,'height',{configurable:true,get:()=>450});visualViewport.dispatchEvent(new Event('resize'));}""")
        expect(page.locator('.desktop')).to_have_attribute('data-keyboard-open', 'true')
        expect(page.get_by_role('navigation', name='Navegação do telefone', exact=True)).not_to_be_visible()
        page.evaluate("""()=>{delete visualViewport.height;visualViewport.dispatchEvent(new Event('resize'));}""")
        expect(page.locator('.desktop')).to_have_attribute('data-keyboard-open', 'false')
        # A focused field does not imply an IME. Rotating the viewport alone
        # must not hide navigation as if a keyboard had consumed the height.
        assert page.evaluate("document.activeElement?.tagName") == 'INPUT'
        page.set_viewport_size({'width': 844, 'height': 390})
        wait_js(page, 'innerWidth > innerHeight')
        expect(page.locator('.desktop')).to_have_attribute('data-keyboard-open', 'false')
        expect(page.get_by_role('navigation', name='Navegação do telefone', exact=True)).to_be_visible()
        assert_phone_layout(page, 'focused landscape without keyboard')
        assert not requests, ('API requests escaped the local adapter', requests)
        assert not errors, errors
        report = {'passed': True, 'actual_android_apk': False, 'browser_touch_viewports': sizes, 'font_125_percent_all_settings': True, 'drawer_and_touch_navigation': True, 'centered_original_presence_single_renderer': True, 'mobile_neural_unavailable_is_explicit': True, 'appearance_persistence': True, 'keyboard_resize_simulated': True, 'focused_rotation_without_ime_preserves_navigation': True, 'physical_keyboard_evaluated': False, 'api_requests_reached_server': requests, 'javascript_errors': errors, **results}
        (args.output / 'ui-verification.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report))
        browser.close()
except BaseException as failure:
    capture_failure(page, args.output, failure)
    raise
