"""Browser check for continuous 3D geometry, score playback and AV cancellation."""
import argparse
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url',required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
with sync_playwright() as pw:
    options={'headless':True,'args':['--enable-unsafe-swiftshader','--use-gl=angle','--use-angle=swiftshader']}
    if os.environ.get('ELYSIA_CHROMIUM_PATH'):options['executable_path']=os.environ['ELYSIA_CHROMIUM_PATH']
    browser=pw.chromium.launch(**options)
    try:
        page=browser.new_page();errors=[];external=[];images=[]
        page.add_init_script('''const NativeRecorder=MediaRecorder;window.MediaRecorder=class extends NativeRecorder {
          constructor(stream,options){super(stream,options);window.recordingTracks=stream.getTracks();window.recordingKinds=stream.getTracks().map(t=>t.kind);}
        };''')
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:external.append(r.url) if r.url.startswith('http') and not r.url.startswith(args.url.rstrip('/')+'/') else None)
        page.on('request',lambda r:images.append(r.url) if r.resource_type=='image' else None)
        page.goto(args.url.rstrip('/')+'/src/continuous-render.html')
        page.wait_for_function('window.filmReady===true',timeout=60000)
        states=[page.evaluate('t=>film.render(t)',t) for t in [0,1/30,15,30,45,59.9]]
        assert len({tuple(s['camera']) for s in states})==6
        assert max(abs(a-b) for a,b in zip(states[0]['camera'],states[1]['camera']))<.1
        assert all(s['triangles']>10000 for s in states)
        before=page.locator('canvas').screenshot()
        page.get_by_role('button',name='Reproduzir com trilha',exact=True).click()
        page.wait_for_function("document.querySelector('#time').textContent !== '0 / 60 s'",timeout=30000)
        assert page.locator('canvas').screenshot()!=before
        page.get_by_role('button',name='Interromper',exact=True).click()
        page.get_by_role('button',name='Gerar vídeo 3D com áudio',exact=True).click()
        page.wait_for_function("window.recordingKinds?.includes('audio') && window.recordingKinds?.includes('video')",timeout=30000)
        page.get_by_role('button',name='Interromper',exact=True).click()
        page.wait_for_function("window.recordingTracks.every(t=>t.readyState==='ended')",timeout=10000)
        assert page.locator('#download').is_hidden()
        assert not errors and not external and not images, (errors,external,images)
        report={'passed':True,'geometric_3d_camera_motion':True,'continuous_adjacent_camera_step':True,'audio_video_stream_tracks':True,'cancel_releases_tracks':True,'no_input_image_requests':True,'external_requests':external,'javascript_errors':errors,'full_browser_realtime_export_tested':False}
        (args.output/'browser.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
    finally:browser.close()
