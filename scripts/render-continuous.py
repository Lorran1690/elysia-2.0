"""Original continuous 3D Elysia film and instrumental score; no input images.
Requires Playwright Chromium, NumPy and ffmpeg/ffprobe. All media stays local.
"""
import argparse
import base64
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import wave
import numpy as np
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]

def music(path, seconds=60, rate=48000):
    """Original 80 BPM D minor ambient arrangement; stereo PCM, no voice."""
    count=seconds*rate
    output=np.zeros((count,2),dtype=np.float64)
    rng=np.random.default_rng(1650)
    def note(start,length,midi,volume,pan=0,pad=False):
        begin=round(start*rate);n=min(round(length*rate),count-begin)
        if n<=0:return
        t=np.arange(n)/rate;hz=440*2**((midi-69)/12)
        attack=.4 if pad else .012;release=.7 if pad else .2
        env=np.minimum(1,t/attack)*np.minimum(1,(n/rate-t)/release)
        if not pad:env*=np.exp(-t*2.3)
        tone=(np.sin(2*np.pi*hz*t)+.22*np.sin(2*np.pi*hz*2*t)+.07*np.sin(2*np.pi*hz*3*t))*env*volume
        output[begin:begin+n,0]+=tone*math.sqrt((1-pan)/2)
        output[begin:begin+n,1]+=tone*math.sqrt((1+pan)/2)
    chords=[[50,57,62,65],[46,53,58,62],[48,55,60,64],[45,52,57,60]]
    beat=.75
    for bar in range(20):
        chord=chords[bar%4];start=bar*4*beat
        for i,midi in enumerate(chord):note(start,3.8,midi,.055,(i-1.5)*.35,True)
        for k in range(8):note(start+k*beat/2,.7,chord[k%4]+12,.045,math.sin(k)*.55)
        for k in range(4):
            at=start+k*beat
            note(at,.45,chord[0]-12,.12)
            begin=round(at*rate);n=min(int(.22*rate),count-begin);t=np.arange(n)/rate
            kick=np.sin(2*np.pi*(45*t+40*(1-np.exp(-t*24))/24))*np.exp(-t*25)*.11
            output[begin:begin+n]+=kick[:,None]
            for off in [0,.375]:
                begin=round((at+off)*rate);n=min(int(.07*rate),count-begin);t=np.arange(n)/rate
                noise=rng.uniform(-1,1,n);noise=np.diff(noise,prepend=0)*np.exp(-t*70)*.012
                output[begin:begin+n]+=noise[:,None]
    # Gentle stereo echo and safe final level, with a musical fade in/out.
    delay=int(.375*rate);output[delay:]+=output[:-delay,::-1]*.17
    t=np.arange(count)/rate;output*=np.minimum(1,t/2)[:,None]*np.minimum(1,(seconds-t)/3)[:,None]
    peak=float(np.max(np.abs(output)));output*=.78/max(peak,1e-9)
    with wave.open(str(path),'wb') as wav:
        wav.setnchannels(2);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes((output*32767).astype('<i2').tobytes())
    return {'sample_rate':rate,'channels':2,'seconds':seconds,'peak':.78,'original_synthetic_instrumental':True}

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--preview',action='store_true',help='Render four inspection frames and exit.')
    args=parser.parse_args();args.output.parent.mkdir(parents=True,exist_ok=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT/'interface/web')))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix='elysia-continuous-') as tmp, sync_playwright() as pw:
            options={'headless':True,'args':['--enable-unsafe-swiftshader','--use-gl=angle','--use-angle=swiftshader']}
            if os.environ.get('ELYSIA_CHROMIUM_PATH'):options['executable_path']=os.environ['ELYSIA_CHROMIUM_PATH']
            browser=pw.chromium.launch(**options)
            try:
                page=browser.new_page(viewport={'width':1280,'height':720});errors=[];external=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                base=f'http://127.0.0.1:{server.server_port}'
                page.on('request',lambda req:external.append(req.url) if req.url.startswith('http') and not req.url.startswith(base+'/') else None)
                page.goto(base+'/src/continuous-render.html?offline=1')
                page.wait_for_function('window.filmReady===true',timeout=60000)
                states=[]
                for i,t in enumerate([0,15,30,45]):
                    states.append(page.evaluate('t=>window.film.render(t)',t))
                    page.locator('canvas').screenshot(path=str(args.output.parent/f'continuous-{i}.png'))
                if args.preview:
                    print(json.dumps({'states':states,'errors':errors}));return
                wav=Path(tmp)/'score.wav';audio=music(wav)
                target=args.output.with_name(args.output.stem+'.partial.mp4')
                cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','image2pipe','-vcodec','mjpeg','-framerate','30','-i','pipe:0','-i',str(wav),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-t','60','-movflags','+faststart',str(target)]
                process=subprocess.Popen(cmd,stdin=subprocess.PIPE)
                try:
                    for i in range(1800):
                        image=page.evaluate("t=>{window.film.render(t);return document.querySelector('canvas').toDataURL('image/jpeg',.97).split(',')[1]}",i/30)
                        process.stdin.write(base64.b64decode(image))
                        if i%150==0:print(f'{i//30}/60 seconds rendered',flush=True)
                    process.stdin.close()
                    if process.wait()!=0:raise RuntimeError('Video encoding failed')
                    if errors or external:raise RuntimeError(f'Browser errors/network requests: {errors}, {external}')
                    target.replace(args.output)
                except BaseException:
                    process.kill();process.wait();target.unlink(missing_ok=True);raise
                report={'renderer':'Three.js 0.160.1 geometric 3D','single_continuous_take':True,'input_images':0,'input_videos':0,'seconds':60,'width':1280,'height':720,'fps':30,'frames':1800,'music':audio,'camera_states':states,'javascript_errors':errors,'external_requests':external}
                args.output.with_suffix('.render.json').write_text(json.dumps(report,indent=2)+'\n')
                print(json.dumps(report))
            finally:browser.close()
    finally:server.shutdown();server.server_close();thread.join()

if __name__=='__main__':main()
