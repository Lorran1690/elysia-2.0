"""Install, upgrade, launch and uninstall the actual package on a Windows runner.
Uses an isolated Unicode destination; never deletes the user's private directory.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid
import winreg

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('installer', type=Path)
parser.add_argument('--native', action='store_true')
parser.add_argument('--output', type=Path, default=Path('installer-verification.json'))
args = parser.parse_args()
if sys.platform != 'win32': raise SystemExit('Windows is required for a real installer test.')
installer = args.installer.resolve()
key_name = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\{620794CC-B5EE-48C0-998D-045C155A2F87}_is1'

def run(command, timeout=240, **kwargs):
    subprocess.run([str(p) for p in command], check=True, timeout=timeout, **kwargs)

def registration():
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_name, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
        return {name:winreg.QueryValueEx(key, name)[0] for name in ['DisplayName', 'InstallLocation', 'UninstallString']}

# Refuse to touch an existing installation when this test is run outside CI.
try: registration()
except FileNotFoundError: pass
else: raise SystemExit('Existing Elysia installation detected. Test refused to modify it.')

with tempfile.TemporaryDirectory(prefix='elysia-installer-') as tmp:
    root = Path(tmp)
    destination = root/'Elysia instalação com espaços'
    private = root/'private-data'; private.mkdir()
    canary = private/'owner-data.txt'; canary.write_text('Private data must survive upgrade and uninstall.', encoding='utf-8')
    default_private = Path(os.environ['LOCALAPPDATA'])/'Elysia'
    default_private.mkdir(parents=True, exist_ok=True)
    default_canary = default_private/('installer-canary-'+uuid.uuid4().hex+'.txt')
    default_canary.write_bytes(canary.read_bytes())
    shortcuts = Path(os.environ['APPDATA'])/'Microsoft/Windows/Start Menu/Programs/Elysia'
    executable = destination/'Elysia.exe'
    env = {**os.environ, 'ELYSIA_DATA_DIR':str(private)}
    installed = False
    try:
        command = [installer, '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', '/DIR='+str(destination)]
        installed = True
        run([*command, '/LOG='+str(root/'install.log')])
        core_dir = destination/'core' if args.native else destination
        assert executable.is_file() and (core_dir/'_internal/interface/web/src/avatar-rig.js').is_file()
        assert (core_dir/'_internal/interface/web/assets/avatar-body.png').is_file()
        assert (shortcuts/'Elysia.lnk').is_file()
        reg = registration(); assert Path(reg['InstallLocation']) == destination
        report_file = root/'installed-smoke.json'
        run([core_dir/'Elysia.exe', '--smoke-test', report_file], env=env)
        if args.native:
            run([sys.executable, 'desktop/scripts/test-ui.py', '--native', executable, '--output', Path('native-ui-verification')], timeout=300)
        smoke = json.loads(report_file.read_text(encoding='utf-8'))
        assert smoke['passed'] and smoke['frozen']
        # Reinstall into the same directory, retaining owner files and registration.
        run([*command, '/LOG='+str(root/'upgrade.log')])
        assert canary.read_bytes() == default_canary.read_bytes()
        assert executable.is_file() and Path(registration()['InstallLocation']) == destination
        uninstaller = destination/'unins000.exe'
        assert uninstaller.is_file()
        run([uninstaller, '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/LOG='+str(root/'uninstall.log')])
        assert not executable.exists() and not (shortcuts/'Elysia.lnk').exists()
        assert canary.read_text(encoding='utf-8') == 'Private data must survive upgrade and uninstall.'
        assert default_canary.read_bytes() == canary.read_bytes()
        try: registration()
        except FileNotFoundError: pass
        else: raise AssertionError('Uninstall registration was not removed')
        installed = False
        report = {'passed':True,'installer_executed':True,'unicode_install_directory':True,'start_menu_shortcut_created':True,'current_user_uninstall_registration':True,'installed_executable_real_model_smoke':smoke['passed'],'reinstall_preserves_private_data':True,'uninstall_removes_app_and_shortcut':True,'uninstall_preserves_private_data':True,'neural_quality_evaluated':False,'actual_tauri_webview2':args.native}
        args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(report))
    finally:
        if installed and (destination/'unins000.exe').is_file():
            run([destination/'unins000.exe','/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART'])
        default_canary.unlink(missing_ok=True)
        # Inno's temporary uninstaller helper can outlive its parent briefly,
        # holding the log after the product and registration are already gone.
        # Wait for this owned log to close before TemporaryDirectory removes it.
        deadline = time.monotonic() + 30
        while True:
            try:
                (root/'uninstall.log').unlink(missing_ok=True)
                break
            except PermissionError:
                if time.monotonic() >= deadline: raise
                time.sleep(.2)
