"""Render a deterministic 60-second presentation without real-time dropped frames.
Requires Playwright Chromium and ffmpeg on PATH. No neural model or voice is used.
"""
import argparse
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--height', type=int, choices=[720, 1080], default=720)
args = parser.parse_args()
if not shutil.which('ffmpeg'):
    parser.error('Install ffmpeg first.')
args.output.parent.mkdir(parents=True, exist_ok=True)
width, height, fps, seconds = args.height*16//9, args.height, 30, 60
with sync_playwright() as pw:
    options = {'headless': True}
    if os.environ.get('ELYSIA_CHROMIUM_PATH'):
        options['executable_path'] = os.environ['ELYSIA_CHROMIUM_PATH']
    browser = pw.chromium.launch(**options)
    try:
        page = browser.new_page()
        page.set_content('<canvas id="frame"></canvas>')
        page.add_script_tag(path=str(Path(__file__).resolve().parents[1]/'interface/web/src/media-engine.js'))
        page.evaluate('''([width,height])=>{window.project={...ElysiaMedia.DEFAULT,layout:'presentation',width,height,duration:60,fps:30};}''', [width,height])
        command = ['ffmpeg','-hide_banner','-loglevel','error','-y','-f','image2pipe','-vcodec','mjpeg','-framerate',str(fps),'-i','pipe:0','-an','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(args.output)]
        process = subprocess.Popen(command, stdin=subprocess.PIPE)
        try:
            for i in range(fps*seconds):
                data = page.evaluate('''t=>{ElysiaMedia.draw(document.querySelector('canvas'),project,t);return document.querySelector('canvas').toDataURL('image/jpeg',.97).split(',')[1];}''', i/(fps*seconds))
                process.stdin.write(base64.b64decode(data))
                if i%300==0:
                    print(f'{i//fps}/{seconds} seconds rendered', flush=True)
            process.stdin.close()
            if process.wait()!=0:
                raise RuntimeError('ffmpeg export failed')
        except BaseException:
            process.kill()
            process.wait()
            args.output.unlink(missing_ok=True)
            raise
    finally:
        browser.close()
print(json.dumps({'path':str(args.output),'width':width,'height':height,'fps':fps,'frames':fps*seconds,'seconds':seconds,'audio':False}))
