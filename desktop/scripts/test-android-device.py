"""Exercise an Elysia APK on an already-running, disposable Android emulator.

Debug mode uses the actual app WebView through CDP. --release-smoke never
enables debugging: it uses Android's accessibility tree and screenshots, creates
a synthetic private note, reinstalls the same signed APK and checks persistence.
No owner phone, owner data, model fixture or external inference API is used.
"""
import argparse
import hashlib
import json
import re
import subprocess
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from playwright.sync_api import sync_playwright, expect, TimeoutError as PlaywrightTimeout
from mobile_ui_checks import (
    assert_phone_layout, capture_failure, check_center, check_mobile_api,
    check_music_and_png, check_phone_navigation, check_vault_and_tools,
    navigate, settings, wait_js, set_navigation_hook, set_screenshot_hook,
)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--apk', required=True, type=Path)
parser.add_argument('--app-id', default='org.elysia.mobile')
parser.add_argument('--output', type=Path, default=Path('reports/android-device'))
parser.add_argument('--adb', default='adb')
parser.add_argument('--release-smoke', action='store_true')
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
if not re.fullmatch(r'[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+', args.app_id):
    raise SystemExit('Invalid Android application ID')
if not args.apk.is_file():
    raise SystemExit('APK not found: ' + str(args.apk))


def adb(*command, timeout=40, binary=False, check=True):
    result = subprocess.run([args.adb, *map(str, command)], check=check, capture_output=True, timeout=timeout)
    return result.stdout if binary else result.stdout.decode('utf-8', errors='replace').strip()


def resumed_activities():
    activities = adb('shell', 'dumpsys', 'activity', 'activities')
    top = [line for line in activities.splitlines() if re.search(r'\btopResumedActivity\s*[=:]', line)]
    return top or [line for line in activities.splitlines() if re.search(r'\b(?:mResumedActivity|ResumedActivity)\s*[=:]', line)]


def app_is_foreground():
    return any(args.app_id + '/' in line for line in resumed_activities())


def assert_app_foreground(timeout=8):
    deadline = time.monotonic() + timeout
    while not app_is_foreground():
        if time.monotonic() >= deadline:
            raise AssertionError('Elysia left the foreground; the test never relaunches it to mask navigation errors')
        time.sleep(.2)


def wait_share_chooser(timeout=30):
    # Writing a PNG precedes opening Android's Sharesheet. A physical Back is
    # justified only once the real chooser, rather than Elysia, is foreground.
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        windows = adb('shell', 'dumpsys', 'window', 'windows')
        if 'Application Not Responding:' in windows:
            raise AssertionError('Android reported an Application Not Responding dialog before share cancellation; no dialog is dismissed by the driver')
        resumed = resumed_activities()
        if any(('com.android.intentresolver/' in line or 'android/' in line) and 'ChooserActivity' in line for line in resumed):
            return
        time.sleep(.2)
    raise AssertionError('Native share chooser did not enter the foreground; no Back was sent')


def screen(name):
    (args.output / name).write_bytes(adb('exec-out', 'screencap', '-p', binary=True))


def native_screenshot(path):
    assert_app_foreground()
    path.write_bytes(adb('exec-out', 'screencap', '-p', binary=True))


def launch():
    adb('shell', 'am', 'start', '-W', '-n', args.app_id + '/.MainActivity')


def rotate(landscape):
    adb('shell', 'settings', 'put', 'system', 'accelerometer_rotation', '0')
    adb('shell', 'settings', 'put', 'system', 'user_rotation', '1' if landscape else '0')


def ui_tree():
    adb('shell', 'uiautomator', 'dump', '/sdcard/elysia-test-window.xml', timeout=30)
    return ET.fromstring(adb('exec-out', 'cat', '/sdcard/elysia-test-window.xml', binary=True))


def node_point(node):
    match = re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', node.attrib.get('bounds', ''))
    if not match:
        raise AssertionError('No bounds for accessibility node: ' + str(node.attrib))
    left, top, right, bottom = map(int, match.groups())
    return (left + right) // 2, (top + bottom) // 2


def find_node(label, tree=None):
    tree = tree if tree is not None else ui_tree()
    return next((n for n in tree.iter('node') if label in [n.attrib.get('text'), n.attrib.get('content-desc')]), None)


def tap_label(label, scroll=False, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        tree = ui_tree()
        node = find_node(label, tree)
        if node is not None:
            adb('shell', 'input', 'tap', *node_point(node))
            return
        if scroll:
            match = re.search(r'(\d+)x(\d+)', adb('shell', 'wm', 'size'))
            width, height = map(int, match.groups())
            adb('shell', 'input', 'swipe', width // 2, int(height * .74), width // 2, int(height * .33), '280')
        time.sleep(.25)
    raise AssertionError('Android accessibility label not found: ' + label)


def webview_height():
    for node in ui_tree().iter('node'):
        if node.attrib.get('class') == 'android.webkit.WebView':
            match = re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', node.attrib.get('bounds', ''))
            if match:
                left, top, right, bottom = map(int, match.groups())
                if right > left and bottom > top:
                    return bottom - top
    raise AssertionError('Visible Android WebView bounds unavailable')


def hide_keyboard(full_height):
    # Release tests cannot read DOM state. A physically reduced WebView proves
    # that the IME is actually visible; mInputShown alone can remain stale after
    # navigation and must never justify sending Back to the application.
    if webview_height() < full_height - 90:
        adb('shell', 'input', 'keyevent', '4')
        assert_app_foreground()
        time.sleep(.25)


def dismiss_dom_keyboard(page):
    assert_app_foreground()
    page.evaluate("document.activeElement?.blur()")
    # A blur can race Android's pending IME animation. Wait for the actual
    # WebView dimensions to settle before computing the next touch target.
    deadline = time.monotonic() + 15
    previous_height = None
    stable_samples = 0
    while stable_samples < 4:
        state = page.evaluate("""()=>({height:visualViewport.height,
          keyboard:document.querySelector('.desktop')?.dataset.keyboardOpen,
          editing:['INPUT','TEXTAREA'].includes(document.activeElement?.tagName)})""")
        settled = state['keyboard'] == 'false' and not state['editing']
        stable_samples = stable_samples + 1 if settled and state['height'] == previous_height else 0
        previous_height = state['height']
        if time.monotonic() >= deadline:
            raise AssertionError('Native keyboard did not settle after input blur: ' + str(state))
        page.wait_for_timeout(100)
    expect(page.get_by_role('navigation', name='Navegação do telefone', exact=True)).to_be_visible(timeout=15000)
    assert_app_foreground()


def wait_accessibility(label, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        tree = ui_tree()
        if find_node(label, tree) is not None:
            return tree
        time.sleep(.3)
    raise AssertionError('Android UI did not expose: ' + label)


def physical_size():
    sizes = re.findall(r'(\d+)x(\d+)', adb('shell', 'wm', 'size'))
    return tuple(map(int, sizes[-1]))


def tap_web_element(page, locator):
    locator.scroll_into_view_if_needed()
    box = locator.bounding_box()
    assert box
    tree = ui_tree()
    webview = next((n for n in tree.iter('node') if n.attrib.get('class') == 'android.webkit.WebView'), None)
    if webview is None:
        raise AssertionError('Android WebView bounds unavailable for touch verification')
    match = re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', webview.attrib['bounds'])
    left, top, right, bottom = map(int, match.groups())
    scale = (right - left) / page.evaluate('innerWidth')
    adb('shell', 'input', 'tap', int(left + (box['x'] + box['width'] / 2) * scale), int(top + (box['y'] + box['height'] / 2) * scale))


def app_page(browser):
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        for context in browser.contexts:
            if not context.pages:
                try:
                    context.wait_for_event('page', timeout=1000)
                except PlaywrightTimeout:
                    pass
            for page in context.pages:
                try:
                    page.wait_for_url('https://localhost/**', wait_until='domcontentloaded', timeout=1500)
                    return page
                except PlaywrightTimeout:
                    pass
        time.sleep(.1)
    raise AssertionError('The bundled mobile app did not load in its Android WebView')


def release_smoke(package_info):
    assert not re.search(r'(?:pkgFlags|flags)=\[[^\]]*\bDEBUGGABLE\b', package_info), 'Production APK is debuggable'
    pid = adb('shell', 'pidof', args.app_id).split()[0]
    sockets = adb('shell', 'cat', '/proc/net/unix')
    assert 'webview_devtools_remote_' + pid not in sockets, 'Production WebView exposes debugging'
    wait_accessibility('Biblioteca')
    screen('release-portrait.png')
    tap_label('Centralizar orbe ou avatar')
    wait_accessibility('Fechar visualização central')
    screen('release-presence.png')
    tap_label('Fechar visualização central')
    tap_label('Biblioteca')
    full_height = webview_height()
    canary = 'AndroidReleasePrivateCanary'
    tap_label('Título do registro', scroll=True)
    adb('shell', 'input', 'text', canary)
    hide_keyboard(full_height)
    tap_label('Conteúdo do registro', scroll=True)
    adb('shell', 'input', 'text', 'SyntheticPrivateCanaryData')
    hide_keyboard(full_height)
    tap_label('Salvar registro', scroll=True)
    # The save notice is above the form and can be outside Android's visible
    # accessibility tree. Finding this newly saved canary below verifies the write.
    tap_label('Conversas')
    tap_label('Biblioteca')
    tap_label(canary, scroll=True)
    adb('shell', 'am', 'force-stop', args.app_id)
    adb('install', '-r', args.apk, timeout=120)
    launch()
    wait_accessibility('Biblioteca')
    tap_label('Biblioteca')
    tap_label(canary, scroll=True)
    screen('release-reinstalled-library.png')
    rotate(True)
    time.sleep(1)
    wait_accessibility('Biblioteca')
    screen('release-landscape.png')
    return {'production_apk_not_debuggable': True, 'production_webview_debug_socket_absent': True, 'native_accessibility_ui': True, 'original_presence_opens': True, 'reinstall_preserves_private_vault_note': True, 'portrait_landscape_captured': True, 'cdp_used': False}


def debug_ui():
    browser = page = None
    errors = []
    try:
        pid = adb('shell', 'pidof', args.app_id).split()[0]
        adb('forward', 'tcp:9224', 'localabstract:webview_devtools_remote_' + pid)
        deadline = time.monotonic() + 60
        while True:
            try:
                with urllib.request.urlopen('http://127.0.0.1:9224/json/version', timeout=2) as response:
                    version = json.load(response)
                # Android WebViews expose the browser endpoint at this stable
                # path, including versions that omit it from /json/version.
                endpoint = 'ws://127.0.0.1:9224/devtools/browser'
                advertised = version.get('webSocketDebuggerUrl')
                if advertised:
                    from urllib.parse import urlsplit
                    parts = urlsplit(advertised)
                    endpoint = 'ws://127.0.0.1:9224' + parts.path
                    if parts.query:
                        endpoint += '?' + parts.query
                break
            except Exception:
                if time.monotonic() > deadline:
                    raise AssertionError('Debug-only Android WebView CDP did not open')
                time.sleep(.25)
        with sync_playwright() as pw:
            # Android WebView has no browser-context download management. Preserve
            # its native settings rather than sending desktop Chromium overrides.
            browser = pw.chromium.connect_over_cdp(endpoint, no_defaults=True)
            set_navigation_hook(lambda: dismiss_dom_keyboard(page))
            # Capture the physical display, including Android's IME and system
            # bars, without relying on CDP compositor screenshot timing.
            set_screenshot_hook(native_screenshot)
            page = app_page(browser)
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.get_by_role('navigation', name='Navegação do telefone', exact=True).wait_for(timeout=60000)
            assert page.evaluate("!!window.Capacitor?.isNativePlatform?.()"), 'Expected actual Capacitor Android runtime'
            assert_app_foreground()
            check_mobile_api(page)
            check_phone_navigation(page)
            assert_phone_layout(page, 'Android portrait')
            screen('android-portrait.png')
            check_center(page, args.output / 'android-presence-webview.png')
            results = check_vault_and_tools(page, args.output, native_android=True)
            results.update(check_music_and_png(page, args.output, native_android=True))
            page.get_by_role('button', name='Baixar arquivo gerado', exact=True).click()
            deadline = time.monotonic() + 25
            generated = None
            while time.monotonic() < deadline:
                paths = adb('shell', 'run-as', args.app_id, 'find', 'cache', '-type', 'f').splitlines()
                for path in paths:
                    if path.endswith('.png') and 'elysia' in path.lower():
                        data = adb('exec-out', 'run-as', args.app_id, 'cat', path, binary=True)
                        if data.startswith(b'\x89PNG\r\n\x1a\n'):
                            generated = {'path': path, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                            break
                if generated:
                    break
                time.sleep(.3)
            assert generated, 'Generated PNG was not written by the native export bridge'
            wait_share_chooser()
            screen('android-share-sheet.png')
            adb('shell', 'input', 'keyevent', '4')
            assert_app_foreground(timeout=15)
            navigate(page, 'Biblioteca')
            field = page.get_by_label('Título do registro', exact=True)
            before = page.evaluate('visualViewport.height')
            adb('shell', 'settings', 'put', 'secure', 'show_ime_with_hard_keyboard', '1')
            tap_web_element(page, field)
            wait_js(page, 'document.activeElement?.tagName === "INPUT" && visualViewport.height < ' + str(before - 90), timeout=20000)
            after = page.evaluate('visualViewport.height')
            expect(page.locator('.desktop')).to_have_attribute('data-keyboard-open', 'true')
            expect(page.get_by_role('navigation', name='Navegação do telefone', exact=True)).not_to_be_visible()
            screen('android-keyboard.png')
            adb('shell', 'input', 'keyevent', '4')
            page.wait_for_timeout(500)
            assert_app_foreground()
            expect(page.locator('.desktop')).to_have_attribute('data-view', 'vault')
            expect(page.get_by_role('navigation', name='Navegação do telefone', exact=True)).to_be_visible(timeout=15000)
            rotate(True)
            wait_js(page, 'innerWidth > innerHeight', timeout=20000)
            assert_phone_layout(page, 'Android landscape')
            check_phone_navigation(page)
            screen('android-landscape.png')
            check_center(page, args.output / 'android-landscape-presence.png')
            assert not errors, errors
            results.update({'actual_capacitor_android_webview': True, 'cdp_used': True, 'portrait_landscape_captured': True, 'actual_soft_keyboard_resize': {'before': before, 'after': after}, 'native_png_export': generated, 'javascript_errors': errors})
            browser.close()
            return results
    except BaseException as failure:
        (args.output / 'debug-failure.json').write_text(json.dumps({'exception': str(failure), 'javascript_errors': errors}, ensure_ascii=False, indent=2) + '\n')
        capture_failure(page, args.output, failure)
        raise
    finally:
        set_navigation_hook(None)
        set_screenshot_hook(None)
        adb('forward', '--remove', 'tcp:9224', check=False)


try:
    assert adb('get-state') == 'device'
    adb('wait-for-device')
    adb('install', '-r', args.apk, timeout=120)
    adb('logcat', '-c')
    adb('shell', 'settings', 'put', 'secure', 'show_ime_with_hard_keyboard', '1')
    rotate(False)
    adb('shell', 'svc', 'wifi', 'disable')
    adb('shell', 'svc', 'data', 'disable')
    launch()
    package_info = adb('shell', 'dumpsys', 'package', args.app_id)
    checks = release_smoke(package_info) if args.release_smoke else debug_ui()
    report = {'passed': True, 'actual_android_apk': True, 'release_signed_apk_smoke': args.release_smoke, 'apk_bytes': args.apk.stat().st_size, 'apk_sha256': hashlib.file_digest(args.apk.open('rb'), 'sha256').hexdigest(), 'app_id': args.app_id, 'android_api': adb('shell', 'getprop', 'ro.build.version.sdk'), 'network_disabled_commands': ['svc wifi disable', 'svc data disable'], 'neural_generation_evaluated': False, 'realistic_ai_video_evaluated': False, **checks}
    (args.output / 'device-verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
except BaseException as failure:
    try:
        screen('failure-device.png')
        (args.output / 'failure-ui.xml').write_bytes(ET.tostring(ui_tree(), encoding='utf-8'))
        (args.output / 'failure-logcat.txt').write_text(adb('logcat', '-d', '-t', '1000'))
        (args.output / 'failure-activity.txt').write_text(adb('shell', 'dumpsys', 'activity', 'activities'))
        (args.output / 'failure-window.txt').write_text(adb('shell', 'dumpsys', 'window', 'windows'))
        (args.output / 'failure-input-method.txt').write_text(adb('shell', 'dumpsys', 'input_method'))
        pid = adb('shell', 'pidof', args.app_id).split()
        if pid:
            (args.output / 'failure-app-logcat.txt').write_text(adb('logcat', '-d', '--pid=' + pid[0]))
        (args.output / 'failure.json').write_text(json.dumps({'exception': str(failure)}, indent=2) + '\n')
    except Exception:
        pass
    raise
finally:
    try:
        rotate(False)
        adb('shell', 'svc', 'wifi', 'enable', check=False)
        adb('shell', 'svc', 'data', 'enable', check=False)
    except Exception:
        pass
