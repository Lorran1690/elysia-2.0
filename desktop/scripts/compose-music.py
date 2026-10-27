"""Reproduce three original instrumental loops. No samples, voices or copyrighted songs."""
import hashlib,json,subprocess,tempfile,wave
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'public/music'; OUT.mkdir(parents=True,exist_ok=True)
sr=24000; duration=48; t=np.arange(sr*duration)/sr
specs={'aurora':{'chords':[[50,57,62,66],[47,54,59,62],[43,50,55,59],[45,52,57,61]],'bpm':80},'orbita':{'chords':[[45,52,57,60],[41,48,53,57],[48,55,60,64],[43,50,55,59]],'bpm':80},'foco':{'chords':[[48,55,60,64],[45,52,57,60],[41,48,53,57],[43,50,55,59]],'bpm':80}}
report={'original_synthetic_instrumentals':True,'license':'CC0-1.0','no_external_samples':True,'tracks':{}}
for index,(name,spec) in enumerate(specs.items()):
 y=np.zeros((len(t),2));beat=60/spec['bpm'];bar=beat*4
 for bar_i in range(16):
  start=bar_i*bar;local=t-start;end=min(duration,start+bar+2);mask=(local>=0)&(t<end);lt=local[mask];chord=spec['chords'][bar_i%4]
  env=np.minimum(1,lt/1.2)*np.minimum(1,np.maximum(0,(bar+2-lt)/2))
  for j,note in enumerate(chord):
   hz=440*2**((note-69)/12);phase=2*np.pi*hz*lt
   pad=(np.sin(phase)+.18*np.sin(phase*2+.15*np.sin(lt))+.05*np.sin(phase*3))*.017*env
   pan=(j-1.5)*.15;y[mask,0]+=pad*(.7-pan);y[mask,1]+=pad*(.7+pan)
  for tick in range(8):
   pos=start+tick*beat/2;offset=int(pos*sr);length=min(int(2.2*sr),len(t)-offset)
   if length<=0:continue
   lt=np.arange(length)/sr;note=chord[(tick+index)%4]+(12 if index!=2 else 24);hz=440*2**((note-69)/12)
   pluck=np.sin(2*np.pi*hz*lt)*np.exp(-lt*(3.5 if index==2 else 2.3))*np.minimum(1,lt/.015)*(.013 if index==2 else .019)
   for channel in range(2):
    delay=int((.17+.06*channel)*sr);y[offset:offset+length,channel]+=pluck*(.9 if channel==tick%2 else .45)
    n=min(length,len(t)-offset-delay)
    if n>0:y[offset+delay:offset+delay+n,channel]+=pluck[:n]*.18
 fade=np.minimum(1,t/1.5)*np.minimum(1,(duration-t)/1.5);y*=fade[:,None];y*=.75
 y*=10**((-24-20*np.log10(np.sqrt(np.mean(y*y))))/20)
 peak=float(np.max(np.abs(y)));rms=float(np.sqrt(np.mean(y*y)));pcm=(np.clip(y,-1,1)*32767).astype('<i2')
 with tempfile.TemporaryDirectory() as tmp:
  wav=Path(tmp)/'loop.wav'
  with wave.open(str(wav),'wb') as f:f.setnchannels(2);f.setsampwidth(2);f.setframerate(sr);f.writeframes(pcm.tobytes())
  file=OUT/(name+'.mp3');subprocess.run(['ffmpeg','-v','error','-y','-i',str(wav),'-codec:a','libmp3lame','-b:a','128k',str(file)],check=True)
 report['tracks'][name]={'duration_seconds':duration,'sample_rate':sr,'channels':2,'peak_dbfs':round(20*np.log10(peak),2),'rms_dbfs':round(20*np.log10(rms),2),'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'bytes':file.stat().st_size,**spec}
(OUT/'composition.json').write_text(json.dumps(report,indent=2)+'\n')
(OUT/'LICENSE.txt').write_text('Elysia original synthetic instrumental music. CC0 1.0 Universal. No external samples or voice recordings. Reproduce with desktop/scripts/compose-music.py.\n')
print(json.dumps(report))
