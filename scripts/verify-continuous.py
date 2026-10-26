"""Check actual encoded film duration, streams, motion, freeze and audio levels."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('video',type=Path)
parser.add_argument('--report',type=Path,required=True)
args=parser.parse_args()
def run(command):
    return subprocess.run(command,capture_output=True,text=True,check=True)
probe=json.loads(run(['ffprobe','-v','error','-count_frames','-show_entries','stream=codec_type,codec_name,width,height,r_frame_rate,nb_read_frames,duration,sample_rate,channels:format=duration,size','-of','json',str(args.video)]).stdout)
video=next(s for s in probe['streams'] if s['codec_type']=='video')
audio=next(s for s in probe['streams'] if s['codec_type']=='audio')
assert video['width']>=1280 and video['height']>=720
assert abs(float(probe['format']['duration'])-60)<.1
assert int(video['nb_read_frames'])==1800 and video['r_frame_rate']=='30/1'
assert int(audio['channels'])==2 and int(audio['sample_rate'])==48000
assert float(audio['duration'])>=59.9
# A slideshow with held shots would fail this freeze check even if encoded at 30 fps.
visual=run(['ffmpeg','-hide_banner','-i',str(args.video),'-an','-vf','freezedetect=n=-50dB:d=0.5,blackdetect=d=0.5:pix_th=0.02','-f','null','-']).stderr
assert 'freeze_start:' not in visual, 'Frozen interval detected'
assert 'black_start:' not in visual, 'Black interval detected'
levels=run(['ffmpeg','-hide_banner','-i',str(args.video),'-vn','-af','volumedetect','-f','null','-']).stderr
mean=float(re.findall(r'mean_volume: ([-\d.]+) dB',levels)[-1])
peak=float(re.findall(r'max_volume: ([-\d.]+) dB',levels)[-1])
assert mean>-40 and peak<0, (mean,peak)
report={'passed':True,'probe':probe,'frozen_intervals_at_least_half_second':0,'black_intervals_at_least_half_second':0,'audio_mean_dbfs':mean,'audio_peak_dbfs':peak,'sha256':hashlib.sha256(args.video.read_bytes()).hexdigest(),'limitation':'Encoded motion and audio verified; source audit establishes geometric 3D without image inputs. No independent human audiovisual review.'}
args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
