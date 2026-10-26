import {createContinuousScene} from './continuous-scene.js';
import {playScore} from './continuous-audio.js';
const canvas=document.querySelector('canvas'),status=document.querySelector('[role=status]');
try {
  window.film=createContinuousScene(canvas);window.film.render(0);window.filmReady=true;
  const offline=new URLSearchParams(location.search).has('offline');
  if(!offline){
    document.querySelectorAll('.controls').forEach(element=>element.hidden=false);
    let animation,context,stopScore,recorder,stream,busy=false,watchdog,exportUrl;
    const setBusy=value=>{busy=value;document.querySelectorAll('[data-start]').forEach(b=>b.disabled=value);document.querySelector('#stop').disabled=!value;};
    const cleanup=()=>{cancelAnimationFrame(animation);clearTimeout(watchdog);stopScore?.();stopScore=null;stream?.getTracks().forEach(t=>t.stop());stream=null;context?.close();context=null;setBusy(false);};
    let cancelled=false;
    const stop=()=>{cancelled=true;if(recorder?.state==='recording')recorder.stop();else cleanup();status.textContent='Reprodução ou exportação interrompida.';};
    async function start(exporting){
      if(busy)return;setBusy(true);cancelled=false;status.textContent=exporting?'Gravando filme com trilha. Mantenha esta janela visível.':'Reproduzindo filme com trilha instrumental.';
      try{
        context=new AudioContext({sampleRate:48000});await context.resume();
        if(exporting){
          const mime=['video/webm;codecs=vp9,opus','video/webm;codecs=vp8,opus','video/webm'].find(m=>MediaRecorder.isTypeSupported(m));
          if(!mime)throw new Error('Este navegador não oferece exportação WebM com áudio.');
          stream=canvas.captureStream(30);const audio=context.createMediaStreamDestination();
          stopScore=playScore(context,audio);stream.addTrack(audio.stream.getAudioTracks()[0]);
          recorder=new MediaRecorder(stream,{mimeType:mime,videoBitsPerSecond:8000000,audioBitsPerSecond:192000});const chunks=[];
          recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
          recorder.onerror=()=>{cancelled=true;cleanup();status.textContent='A gravação falhou. Tente Edge ou Chrome atualizado.';};
          recorder.onstop=()=>{const blob=new Blob(chunks,{type:'video/webm'});cleanup();if(cancelled)return;
            if(exportUrl)URL.revokeObjectURL(exportUrl);exportUrl=URL.createObjectURL(blob);const link=document.querySelector('#download');link.href=exportUrl;link.download='Elysia-filme-3D-60s-720p.webm';link.hidden=false;status.textContent='Filme gerado com trilha. Baixe para preservar o arquivo.';};
          recorder.start(500);
        }else stopScore=playScore(context);
        const began=performance.now();
        const tick=now=>{if(!busy)return;const seconds=Math.min(60,(now-began)/1000);window.film.render(seconds);document.querySelector('#time').textContent=Math.floor(seconds)+' / 60 s';
          if(seconds<60)animation=requestAnimationFrame(tick);else if(exporting&&recorder.state==='recording')recorder.stop();else{cleanup();status.textContent='Reprodução concluída.';}};
        animation=requestAnimationFrame(tick);watchdog=setTimeout(stop,65000);
      }catch(error){cleanup();status.textContent=error.message;}
    }
    document.querySelector('#play').onclick=()=>start(false);document.querySelector('#export').onclick=()=>start(true);document.querySelector('#stop').onclick=stop;
    document.addEventListener('visibilitychange',()=>{if(document.hidden&&busy)stop();});
    window.addEventListener('pagehide',()=>{stop();window.film.dispose();if(exportUrl)URL.revokeObjectURL(exportUrl);});
  }
}catch(error){status.textContent='Não foi possível iniciar o filme 3D: '+error.message;window.filmError=error.message;}
