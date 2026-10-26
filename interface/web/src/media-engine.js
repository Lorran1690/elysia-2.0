/* Offline composition engine. No remote model, microphone or screen capture. */
(function (root) {
  'use strict';
  const SIZES = [[640,360],[1280,720],[720,720]];
  const DEFAULT = {format:'elysia-studio-v1',title:'E.L.Y.S.I.A.',subtitle:'Uma ideia ganha forma',background:'#100d20',accent:'#a78bfa',layout:'orbit',width:640,height:360,duration:3,image:null,
    audio:{mode:'melody',notes:'C4 E4 G4 C5 G4 E4',frequency:440,duration:3,tempo:120,wave:'sine'}};
  const fail = message => { throw new Error(message); };
  const number = (n,min,max) => typeof n==='number' && Number.isFinite(n) && n>=min && n<=max;
  const notes = text => {
    if(typeof text!=='string' || text.length>300)fail('Sequência de notas inválida.');
    const parts=text.trim().split(/\s+/);if(parts.length<1||parts.length>64)fail('Use de 1 a 64 notas.');
    const pitch={C:0,D:2,E:4,F:5,G:7,A:9,B:11};
    return parts.map(part=>{
      if(part==='R')return 0;
      const m=/^([A-G])([#b]?)([2-6])$/.exec(part);if(!m)fail('Use notas como C4, D#4, Bb3 ou R para pausa.');
      const midi=(Number(m[3])+1)*12+pitch[m[1]]+(m[2]==='#'?1:m[2]==='b'?-1:0);
      return 440*Math.pow(2,(midi-69)/12);
    });
  };
  function validate(value) {
    if(!value||value.format!=='elysia-studio-v1')fail('Projeto de mídia inválido.');
    const p={};
    for(const [key,max] of [['title',120],['subtitle',240]]) {
      if(typeof value[key]!=='string'||value[key].length>max)fail('Título ou subtítulo longo demais.');p[key]=value[key];
    }
    for(const key of ['background','accent']){if(!/^#[0-9a-f]{6}$/i.test(value[key]))fail('Cor inválida.');p[key]=value[key];}
    if(!SIZES.some(([w,h])=>w===value.width&&h===value.height))fail('Resolução inválida.');
    if(!['orbit','waves','poster'].includes(value.layout)||!number(value.duration,2,12))fail('Composição ou duração inválida.');
    if(value.image!==null && (typeof value.image!=='string'||value.image.length>2800000||!/^data:image\/(jpeg|png|webp);base64,[a-z0-9+/=]+$/i.test(value.image)))fail('Imagem incorporada inválida ou grande demais.');
    const a=value.audio;
    if(!a||!['tone','melody'].includes(a.mode)||!['sine','triangle','square'].includes(a.wave)||!number(a.frequency,40,2000)||!number(a.duration,1,30)||!number(a.tempo,60,180))fail('Configuração de áudio inválida.');
    notes(a.notes);
    if(a.mode==='melody' && notes(a.notes).length*60/a.tempo>30)fail('A sequência deve durar até 30 segundos.');
    return {...p,format:DEFAULT.format,width:value.width,height:value.height,layout:value.layout,duration:value.duration,image:value.image,
      audio:{mode:a.mode,notes:a.notes,frequency:a.frequency,duration:a.duration,tempo:a.tempo,wave:a.wave}};
  }
  function waveAudio(audio) {
    const p=validate({...DEFAULT,audio});const a=p.audio;const sequence=a.mode==='tone'?[a.frequency]:notes(a.notes);
    const seconds=a.mode==='tone'?a.duration:sequence.length*60/a.tempo;const rate=22050;const count=Math.round(seconds*rate);
    const buffer=new ArrayBuffer(44+count*2);const v=new DataView(buffer);
    const str=(at,s)=>{for(let i=0;i<s.length;i++)v.setUint8(at+i,s.charCodeAt(i));};
    str(0,'RIFF');v.setUint32(4,36+count*2,true);str(8,'WAVE');str(12,'fmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);
    v.setUint32(24,rate,true);v.setUint32(28,rate*2,true);v.setUint16(32,2,true);v.setUint16(34,16,true);str(36,'data');v.setUint32(40,count*2,true);
    const beat=a.mode==='tone'?seconds:60/a.tempo;
    for(let i=0;i<count;i++) {
      const t=i/rate;const index=Math.min(sequence.length-1,Math.floor(t/beat));const local=t-index*beat;const frequency=sequence[index];
      const phase=local*frequency;let sample=0;
      if(frequency)sample=a.wave==='sine'?Math.sin(2*Math.PI*phase):a.wave==='triangle'?2/Math.PI*Math.asin(Math.sin(2*Math.PI*phase)):(Math.sin(2*Math.PI*phase)>=0?1:-1);
      const envelope=Math.max(0,Math.min(1,local/.01,(beat-local)/.03));
      v.setInt16(44+i*2,Math.round(sample*envelope*.2*32767),true);
    }
    return new Blob([buffer],{type:'audio/wav'});
  }
  function wrap(ctx,text,maxWidth) {
    const lines=[];let line='';
    for(const word of text.split(/\s+/)){const next=line?line+' '+word:word;if(line&&ctx.measureText(next).width>maxWidth){lines.push(line);line=word;}else line=next;}
    if(line)lines.push(line);return lines;
  }
  function draw(canvas,project,t=0,image=null) {
    const p=validate(project);canvas.width=p.width;canvas.height=p.height;const ctx=canvas.getContext('2d');if(!ctx)fail('Canvas não disponível.');
    const w=p.width,h=p.height;ctx.fillStyle=p.background;ctx.fillRect(0,0,w,h);
    if(image){const scale=Math.max(w/image.width,h/image.height)*(1+.03*Math.sin(t*Math.PI));const iw=image.width*scale,ih=image.height*scale;ctx.drawImage(image,(w-iw)/2,(h-ih)/2,iw,ih);ctx.fillStyle='#00000099';ctx.fillRect(0,0,w,h);}
    const glow=ctx.createRadialGradient(w*.5,h*.43,2,w*.5,h*.5,w*.6);glow.addColorStop(0,p.accent+'66');glow.addColorStop(1,p.accent+'00');ctx.fillStyle=glow;ctx.fillRect(0,0,w,h);
    ctx.strokeStyle=p.accent;ctx.fillStyle=p.accent;
    if(p.layout==='orbit')for(let i=0;i<90;i++){const angle=i*2.399963+t*Math.PI*2;const radius=Math.sqrt(i/90)*h*.25;ctx.globalAlpha=.25+(i%5)*.13;ctx.beginPath();ctx.arc(w*.5+Math.cos(angle)*radius,h*.35+Math.sin(angle)*radius*.7,1+i%3,0,Math.PI*2);ctx.fill();}
    if(p.layout==='waves')for(let row=0;row<8;row++){ctx.globalAlpha=.16+row*.06;ctx.beginPath();for(let x=0;x<=w;x+=4){const y=h*.25+row*9+Math.sin(x/w*8+t*Math.PI*2+row*.4)*h*.08;if(!x)ctx.moveTo(x,y);else ctx.lineTo(x,y);}ctx.stroke();}
    if(p.layout==='poster'){ctx.globalAlpha=.5;ctx.fillRect(w*.1,h*.18,w*.08,h*.025);ctx.strokeRect(w*.08,h*.12,w*.84,h*.76);}
    ctx.globalAlpha=1;ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillStyle='#ffffff';
    const titleSize=Math.round(h*.095);ctx.font='600 '+titleSize+'px system-ui, sans-serif';
    const title=wrap(ctx,p.title,w*.82).slice(0,3);const center=p.layout==='poster'?h*.4:h*.58;
    title.forEach((line,i)=>ctx.fillText(line,w*.5,center+(i-(title.length-1)/2)*titleSize*1.2,w*.84));
    ctx.font=Math.round(h*.04)+'px system-ui, sans-serif';ctx.fillStyle='#eeeeee';
    wrap(ctx,p.subtitle,w*.8).slice(0,3).forEach((line,i)=>ctx.fillText(line,w*.5,center+titleSize*(title.length*.6+1)+i*h*.055,w*.84));
    return canvas;
  }
  const imageFrom = data => new Promise((resolve,reject)=>{if(!data)return resolve(null);const image=new Image();image.onload=()=>{if(image.width*image.height>16777216)return reject(new Error('Imagem incorporada grande demais.'));resolve(image);};image.onerror=()=>reject(new Error('Não foi possível decodificar a imagem.'));image.src=data;});
  const png = canvas => new Promise((resolve,reject)=>canvas.toBlob(blob=>blob?resolve(blob):reject(new Error('Não foi possível exportar PNG.')),'image/png'));
  function record(canvas,project,image,signal,onProgress) {
    const p=validate(project);
    if(typeof MediaRecorder==='undefined'||!canvas.captureStream)return Promise.reject(new Error('Este navegador não oferece exportação de vídeo. Use Edge ou Chrome atualizado.'));
    const mime=['video/webm;codecs=vp8','video/webm;codecs=vp9','video/webm'].find(type=>MediaRecorder.isTypeSupported(type));
    if(!mime)return Promise.reject(new Error('O navegador não oferece gravação WebM.'));
    return new Promise((resolve,reject)=>{
      let stream,recorder,frame,watchdog,settled=false;const chunks=[];let reason=null;
      const cleanup=()=>{clearInterval(frame);clearTimeout(watchdog);if(stream)stream.getTracks().forEach(track=>track.stop());signal?.removeEventListener('abort',abort);document.removeEventListener('visibilitychange',visibility);};
      const finish=(error,blob)=>{if(settled)return;settled=true;cleanup();error?reject(error):resolve(blob);};
      const abort=()=>{reason=new Error('Exportação cancelada.');if(recorder?.state==='recording')recorder.stop();else finish(reason);};
      const visibility=()=>{if(document.hidden)abort();};
      try {
        if(signal?.aborted)return finish(new Error('Exportação cancelada.'));
        draw(canvas,p,0,image);stream=canvas.captureStream(24);recorder=new MediaRecorder(stream,{mimeType:mime,videoBitsPerSecond:2500000});
        recorder.ondataavailable=event=>{if(event.data.size)chunks.push(event.data);};
        recorder.onerror=()=>finish(new Error('Falha ao codificar vídeo. Tente uma resolução menor.'));
        recorder.onstop=()=>{const blob=new Blob(chunks,{type:'video/webm'});if(reason)return finish(reason);if(!blob.size)return finish(new Error('O navegador gerou um vídeo vazio.'));finish(null,blob);};
        signal?.addEventListener('abort',abort,{once:true});document.addEventListener('visibilitychange',visibility);
        const start=performance.now();recorder.start(200);
        frame=setInterval(()=>{const elapsed=(performance.now()-start)/1000;try{draw(canvas,p,Math.min(elapsed/p.duration,1),image);onProgress?.(Math.min(1,elapsed/p.duration));if(elapsed>=p.duration&&recorder.state==='recording'){clearInterval(frame);recorder.stop();}}catch(error){reason=error;recorder.stop();}},1000/24);
        watchdog=setTimeout(()=>{reason=new Error('Tempo limite ao exportar vídeo.');if(recorder.state==='recording')recorder.stop();else finish(reason);},(p.duration+5)*1000);
      } catch(error){finish(error);}
    });
  }
  root.ElysiaMedia={DEFAULT,SIZES,validate,notes,waveAudio,draw,imageFrom,png,record};
  if(typeof module!=='undefined')module.exports=root.ElysiaMedia;
})(typeof window==='undefined'?globalThis:window);
