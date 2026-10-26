"""Browser check for continuous 3D geometry, score playback and AV cancellation."""
import argparse
import json
import os
import subprocess
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url',required=True)
parser.add_argument('--full-export',action='store_true')
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
        if args.full_export:
            page.get_by_role('button',name='Gerar vídeo 3D com áudio',exact=True).click()
            page.locator('#download').wait_for(state='visible',timeout=120000)
            with page.expect_download() as download:page.locator('#download').click()
            target=args.output/'browser-film.webm';download.value.save_as(target)
            probe=json.loads(subprocess.run(['ffprobe','-v','error','-show_streams','-of','json',str(target)],capture_output=True,text=True,check=True).stdout)
            video=next(s for s in probe['streams'] if s['codec_type']=='video')
            audio=next(s for s in probe['streams'] if s['codec_type']=='audio')
            assert (video['width'],video['height'])==(1280,720)
            assert int(audio['channels'])==2
            packets=json.loads(subprocess.run(['ffprobe','-v','error','-show_entries','packet=pts_time','-of','json',str(target)],capture_output=True,text=True,check=True).stdout)
            assert max(float(p['pts_time']) for p in packets['packets'])>59
            levels=subprocess.run(['ffmpeg','-hide_banner','-i',str(target),'-vn','-af','volumedetect','-f','null','-'],capture_output=True,text=True,check=True).stderr
            assert float(re.findall(r'mean_volume: ([-\d.]+) dB',levels)[-1])>-40
        assert not errors and not external and not images, (errors,external,images)
        report={'passed':True,'geometric_3d_camera_motion':True,'continuous_adjacent_camera_step':True,'audio_video_stream_tracks':True,'cancel_releases_tracks':True,'no_input_image_requests':True,'external_requests':external,'javascript_errors':errors,'full_browser_realtime_export_tested':args.full_export}
        (args.output/'browser.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
    finally:browser.close()
