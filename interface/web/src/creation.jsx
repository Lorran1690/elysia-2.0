// Media creation, project backups, a code editor and an explicit local Drive-folder bridge.
const {useState:useStateC,useEffect:useEffectC,useRef:useRefC} = React;
const downloadBlob = (blob,name) => {const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
const stamp = () => new Date().toISOString().replace(/[:.]/g,'-');
const openDirectoryDB = () => new Promise((resolve,reject)=>{
  const request=indexedDB.open('elysia-private-files',1);
  request.onupgradeneeded=()=>request.result.createObjectStore('settings');request.onerror=()=>reject(request.error);request.onsuccess=()=>resolve(request.result);
});
const directorySetting = async (write,value) => {
  const db=await openDirectoryDB();try{return await new Promise((resolve,reject)=>{
    const tx=db.transaction('settings',write?'readwrite':'readonly');const store=tx.objectStore('settings');
    const request=write?store.put(value,'drive-folder'):store.get('drive-folder');let result;
    request.onsuccess=()=>{result=request.result;};tx.oncomplete=()=>resolve(result);tx.onerror=()=>reject(tx.error);
  });}finally{db.close();}
};
const DriveDestination = ({file}) => {
  const [directory,setDirectory]=useStateC(null),[message,setMessage]=useStateC(''),[busy,setBusy]=useStateC(false),[automatic,setAutomatic]=useStateC(false);
  useEffectC(()=>{let live=true;directorySetting(false).then(value=>{if(live&&value)setDirectory(value);}).catch(()=>{});return()=>{live=false;};},[]);
  const choose=async()=>{setMessage('');try{
    if(!window.showDirectoryPicker)throw new Error('Use Edge ou Chrome para escolher uma pasta. Você também pode baixar e enviar o arquivo pelo site do Drive.');
    const handle=await window.showDirectoryPicker({id:'elysia-drive',mode:'readwrite'});setDirectory(handle);
    try{await directorySetting(true,handle);}catch{setMessage('Pasta escolhida nesta sessão; não foi possível lembrar a seleção.');}
  }catch(error){if(error.name!=='AbortError')setMessage(error.message);}};
  const save=async(auto=false)=>{if(!file||!directory)return;setBusy(true);setMessage('');try{
    if(auto && await directory.queryPermission({mode:'readwrite'})!=='granted')throw new Error('Clique em Salvar para autorizar a pasta antes da gravação automática.');
    if(await directory.requestPermission({mode:'readwrite'})!=='granted')throw new Error('Permissão de escrita não concedida.');
    const name=file.name.replace(/[^a-zA-Z0-9._-]/g,'_');
    let exists=false;try{await directory.getFileHandle(name);exists=true;}catch(error){if(error.name!=='NotFoundError')throw error;}
    if(exists)throw new Error('Já existe um arquivo com esse nome. Gere uma nova exportação para preservar o anterior.');
    const handle=await directory.getFileHandle(name,{create:true});const writer=await handle.createWritable();
    try{await writer.write(file.blob);await writer.close();}catch(error){try{await writer.abort();}catch{}throw error;}
    setMessage('Arquivo gravado na pasta selecionada. Confirme a sincronização no Google Drive para computador; o aplicativo não verifica o envio à nuvem.');
  }catch(error){setMessage(error.message);}finally{setBusy(false);}};
  useEffectC(()=>{if(automatic&&file&&directory)save(true);},[automatic,file,directory]);
  return <section className="studio-drive"><h3>Destino no Google Drive</h3>
    <p className="muted">Para salvar pela pasta sincronizada, selecione uma pasta do Google Drive para computador. A seleção de uma pasta comum salva apenas localmente.</p>
    <button className="pill-btn ghost" onClick={choose} disabled={busy}>Selecionar pasta do Drive</button>
    {directory&&<p className="muted">Pasta selecionada: {directory.name}</p>}
    <button className="pill-btn" onClick={()=>save(false)} disabled={!file||!directory||busy}>Salvar arquivo na pasta selecionada</button>
    <label className="studio-auto"><input type="checkbox" disabled={!directory||busy} checked={automatic} onChange={e=>setAutomatic(e.target.checked)}/>Gravar este e os próximos arquivos automaticamente nesta pasta</label>
    {message&&<p role="status" className="module-notice">{message}</p>}
    <p className="muted">Sem Drive para computador, baixe o arquivo e envie-o para sua pasta no site do Google Drive. Não há upload direto por API nesta versão.</p>
  </section>;
};

const MediaStudioPanel = ({onClose,studioOnly=false}) => {
  const engine=window.ElysiaMedia;
  const [view,setView]=useStateC('Imagem'),[project,setProject]=useStateC(()=>JSON.parse(JSON.stringify(engine.DEFAULT)));
  const [output,setOutput]=useStateC(null),[error,setError]=useStateC(''),[busy,setBusy]=useStateC(false),[progress,setProgress]=useStateC(0);
  const canvas=useRefC(null),image=useRefC(null),controller=useRefC(null),live=useRefC(true),previewVersion=useRefC(0);
  useEffectC(()=>{live.current=true;return()=>{live.current=false;controller.current?.abort();};},[]);
  useEffectC(()=>{let active=true;const version=++previewVersion.current;
    engine.imageFrom(project.image).then(bitmap=>{if(active&&version===previewVersion.current){image.current=bitmap;if(canvas.current)engine.draw(canvas.current,project,0,bitmap);}}).catch(err=>{if(active)setError(err.message);});
    return()=>{active=false;};
  },[project,view]);
  useEffectC(()=>()=>{if(output?.url)URL.revokeObjectURL(output.url);},[output]);
  const set=(key,value)=>{setError('');setProject(p=>({...p,[key]:value}));};
  const setAudio=(key,value)=>setProject(p=>({...p,audio:{...p.audio,[key]:value}}));
  const render=async()=>{
    if(busy)return;setBusy(true);setError('');setProgress(0);controller.current=new AbortController();
    try{
      const p=engine.validate(project);const bitmap=await engine.imageFrom(p.image);let blob,extension;
      if(view==='Áudio'){blob=engine.waveAudio(p.audio);extension='wav';}
      else if(view==='Imagem'){engine.draw(canvas.current,p,0,bitmap);blob=await engine.png(canvas.current);extension='png';}
      else{blob=await engine.record(canvas.current,p,bitmap,controller.current.signal,n=>{if(live.current)setProgress(n);});extension='webm';}
      if(live.current)setOutput({blob,name:'elysia-'+stamp()+'.'+extension,url:URL.createObjectURL(blob),type:extension});
    }catch(err){if(live.current)setError(err.message);}finally{if(live.current)setBusy(false);}
  };
  const importImage=async file=>{if(!file)return;setError('');try{
    if(!['image/png','image/jpeg','image/webp'].includes(file.type)||file.size>8*1024*1024)throw new Error('Escolha PNG, JPEG ou WebP de até 8 MB.');
    const bitmap=await createImageBitmap(file);
    try{const c=document.createElement('canvas');const scale=Math.min(1,1280/bitmap.width,1280/bitmap.height);c.width=Math.max(1,Math.round(bitmap.width*scale));c.height=Math.max(1,Math.round(bitmap.height*scale));if(bitmap.width*bitmap.height>16777216)throw new Error('Imagem com dimensões grandes demais.');c.getContext('2d').drawImage(bitmap,0,0,c.width,c.height);set('image',c.toDataURL('image/jpeg',.85));}finally{bitmap.close();}
  }catch(err){setError(err.message);}};
  const restore=async file=>{if(!file)return;try{if(file.size>3*1024*1024)throw new Error('Projeto grande demais.');const p=engine.validate(JSON.parse(await file.text()));setProject(p);setOutput(null);setError('');}catch(err){setError(err.message);}};
  const visual=view==='Imagem'||view==='Vídeo';
  return <><PanelHead title="Media Studio" kicker="Criação e exportação local" onClose={onClose}/>
    <div className="seg studio-tabs" role="tablist" aria-label="Área de mídia">{(studioOnly?['Imagem','Áudio','Vídeo']:['Imagem','Áudio','Vídeo','Abrir arquivo']).map(v=><button key={v} role="tab" aria-selected={view===v} disabled={busy} onClick={()=>{setView(v);setError('');}}>{v}</button>)}</div>
    {view==='Abrir arquivo'?<LocalMediaPanel embedded onClose={onClose}/>:<div className="module-scroll">
      <p className="note-block">Para gerar cenas com modelos de IA, use a área de geração por IA. Este painel oferece composição local, sem modelo de IA de mídia: crie artes, sons e animações a partir dos controles. Os arquivos só saem do computador ao serem enviados ou sincronizados por você.</p>
      {visual&&<><canvas className="studio-canvas" ref={canvas} aria-label="Prévia da composição"/>
        <div className="module-form"><label>Título<input aria-label="Título da composição" maxLength={120} disabled={busy} value={project.title} onChange={e=>set('title',e.target.value)}/></label>
        <label>Subtítulo<textarea aria-label="Subtítulo da composição" maxLength={240} rows={2} disabled={busy} value={project.subtitle} onChange={e=>set('subtitle',e.target.value)}/></label>
        <label>Composição<select aria-label="Composição" disabled={busy} value={project.layout} onChange={e=>set('layout',e.target.value)}><option value="orbit">Orbe de partículas</option><option value="waves">Ondas</option><option value="poster">Cartaz</option><option value="presentation">Apresentação da Elysia · 6 cenas</option></select></label>
        <label>Resolução<select aria-label="Resolução da mídia" disabled={busy} value={project.width+'x'+project.height} onChange={e=>{const [width,height]=e.target.value.split('x').map(Number);setProject(p=>({...p,width,height}));}}>{engine.SIZES.map(([w,h])=><option key={w+'x'+h}>{w+'x'+h}</option>)}</select></label>
        <div className="studio-colors"><label>Fundo<input aria-label="Cor de fundo" type="color" disabled={busy} value={project.background} onChange={e=>set('background',e.target.value)}/></label><label>Destaque<input aria-label="Cor de destaque" type="color" disabled={busy} value={project.accent} onChange={e=>set('accent',e.target.value)}/></label></div>
        <label className="module-file">Imagem de fundo opcional<input aria-label="Imagem da composição" type="file" accept=".png,.jpg,.jpeg,.webp" disabled={busy} onChange={e=>{importImage(e.target.files?.[0]);e.target.value='';}}/></label>
        {project.image&&<button className="pill-btn ghost" disabled={busy} onClick={()=>set('image',null)}>Remover imagem de fundo</button>}
        {view==='Vídeo'&&<><a className="pill-btn" href="/src/continuous-render.html" target="_blank" rel="noopener">Cinema 3D · cena contínua com trilha</a><button className="pill-btn" disabled={busy} onClick={()=>setProject(p=>({...p,layout:'presentation',width:1280,height:720,duration:60,fps:30}))}>Apresentação da Elysia · 1 minuto · 720p</button><label>Duração em segundos<input aria-label="Duração do vídeo" type="number" min={2} max={60} disabled={busy} value={project.duration} onChange={e=>set('duration',Number(e.target.value))}/></label><label>Fluidez<select aria-label="Quadros por segundo" disabled={busy} value={project.fps||30} onChange={e=>set('fps',Number(e.target.value))}>{[24,30,60].map(n=><option key={n} value={n}>{n} quadros/s</option>)}</select></label><p className="muted">WebM com preferência por VP9 e qualidade ajustada à resolução. Até Full HD horizontal ou vertical, 60 quadros/s e 60 segundos, sem áudio. Para começar, use 1280x720 a 30 quadros/s. A fluidez real depende do computador. Mantenha a janela visível durante a exportação.</p></>}
        </div></>}
      {view==='Áudio'&&<div className="module-form"><label>Tipo<select aria-label="Tipo de áudio" disabled={busy} value={project.audio.mode} onChange={e=>setAudio('mode',e.target.value)}><option value="melody">Sequência de notas</option><option value="tone">Tom contínuo</option></select></label>
        <label>Forma de onda<select aria-label="Forma de onda" disabled={busy} value={project.audio.wave} onChange={e=>setAudio('wave',e.target.value)}><option value="sine">Senoidal</option><option value="triangle">Triangular</option><option value="square">Quadrada</option></select></label>
        {project.audio.mode==='melody'?<><label>Notas<textarea aria-label="Notas musicais" disabled={busy} maxLength={300} value={project.audio.notes} onChange={e=>setAudio('notes',e.target.value)}/></label><p className="muted">Exemplo: C4 E4 G4 C5. R é uma pausa; até 64 notas e 30 segundos.</p><label>Tempo (BPM)<input aria-label="Tempo musical" type="number" min={60} max={180} disabled={busy} value={project.audio.tempo} onChange={e=>setAudio('tempo',Number(e.target.value))}/></label></>:<><label>Frequência (Hz)<input aria-label="Frequência do áudio" type="number" min={40} max={2000} disabled={busy} value={project.audio.frequency} onChange={e=>setAudio('frequency',Number(e.target.value))}/></label><label>Duração (segundos)<input aria-label="Duração do áudio" type="number" min={1} max={30} disabled={busy} value={project.audio.duration} onChange={e=>setAudio('duration',Number(e.target.value))}/></label></>}
        <p className="muted">Síntese musical em WAV mono. Não é voz, clonagem de voz ou texto falado.</p></div>}
      <button className="pill-btn" disabled={busy} onClick={render}>{view==='Imagem'?'Gerar PNG':view==='Áudio'?'Gerar WAV':'Gerar vídeo WebM'}</button>
      {busy&&<><p role="status">Exportando… {Math.round(progress*100)}%</p><button className="pill-btn ghost" onClick={()=>controller.current?.abort()}>Cancelar exportação</button></>}
      {error&&<p role="alert" className="note-block">{error}</p>}
      {output&&<section className="studio-output"><h3>Arquivo gerado</h3>{output.type==='wav'?<audio controls src={output.url}/>:output.type==='webm'?<video controls src={output.url}/>:<img src={output.url} alt="Arte gerada"/>}<p className="muted">{output.name} · {(output.blob.size/1024).toFixed(1)} KB</p><button className="pill-btn" onClick={()=>downloadBlob(output.blob,output.name)}>Baixar arquivo gerado</button></section>}
      <div className="module-actions"><button className="pill-btn ghost" disabled={busy} onClick={()=>{try{saveModuleFile(engine.validate(project),'elysia-studio-'+stamp()+'.json');}catch(err){setError(err.message);}}}>Exportar projeto de mídia</button><label className="module-file">Restaurar projeto<input aria-label="Restaurar projeto de mídia" type="file" accept=".json" disabled={busy} onChange={e=>{restore(e.target.files?.[0]);e.target.value='';}}/></label></div>
      <p className="muted">O projeto exportado inclui a imagem de fundo reduzida. Guarde-o em backup privado; os arquivos gerados devem ser salvos antes de fechar o painel.</p>
      <DriveDestination file={output}/>
    </div>}
  </>;
};

const CodeStudioPanel = ({onClose,editorOnly=false}) => {
  const [view,setView]=useStateC('Editor'),[language,setLanguage]=useStateC('python'),[title,setTitle]=useStateC('Meu projeto'),[code,setCode]=useStateC(''),[message,setMessage]=useStateC(''),[busy,setBusy]=useStateC(false);
  const [preview,setPreview]=useStateC(false);
  useEffectC(()=>{try{const saved=JSON.parse(localStorage.getItem('elysia.code.draft.v1')||'null');if(saved&&['python','javascript','html','css','json'].includes(saved.language)&&typeof saved.code==='string'&&saved.code.length<=20000){setLanguage(saved.language);setCode(saved.code);}}catch{}},[]);
  const changeCode=value=>{setCode(value);setPreview(false);try{localStorage.setItem('elysia.code.draft.v1',JSON.stringify({language,code:value}));}catch{setMessage('Não foi possível salvar o rascunho. Baixe o arquivo para preservá-lo.');}};
  const template=async()=>{if(code.trim()&&!window.confirm('Substituir o código atual pelo modelo inicial? Baixe o arquivo atual antes se precisar preservá-lo.'))return;setBusy(true);setMessage('');try{const result=await moduleRequest('/api/tools',{tool:'code_scaffold',language,text:title});changeCode(result.code);setMessage(result.origin);}catch(err){setMessage(err.message);}finally{setBusy(false);}};
  const validate=async()=>{setBusy(true);try{const result=await moduleRequest('/api/tools',{tool:language==='python'?'python_validate':'json_validate',text:code});setMessage(result.result);}catch(err){setMessage(err.message);}finally{setBusy(false);}};
  const ext={python:'py',javascript:'js',html:'html',css:'css',json:'json'};
  let safeHTML='<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src data:; form-action \'none\'; base-uri \'none\'">'+code;
  if(preview && language==='html') {
    const document=new DOMParser().parseFromString(code,'text/html');
    document.querySelectorAll('script,meta,base,link,iframe,frame,object,embed,form,svg,portal,fencedframe').forEach(node=>node.remove());
    document.querySelectorAll('*').forEach(node=>Array.from(node.attributes).forEach(attribute=>{
      if(/^on/i.test(attribute.name)||['href','target','action','formaction','srcdoc'].includes(attribute.name)||/href$/i.test(attribute.name)||(attribute.name==='src'&&!attribute.value.startsWith('data:image/')))node.removeAttribute(attribute.name);
    }));
    safeHTML=safeHTML.slice(0,safeHTML.length-code.length)+document.documentElement.outerHTML;
  }
  return <><PanelHead title="Código e ferramentas" kicker="Editor local" onClose={onClose}/>{!editorOnly&&<div className="seg" role="tablist" aria-label="Área de código">{['Editor','Ferramentas'].map(v=><button role="tab" key={v} aria-selected={view===v} onClick={()=>setView(v)}>{v}</button>)}</div>}
    {view==='Ferramentas'?<WorkspacePanel embedded onClose={onClose}/>:<div className="module-scroll"><p className="note-block">Edite, valide e baixe arquivos. Os modelos iniciais são estruturas prontas, sem geração por IA e sem execução de programas.</p>
      <div className="module-form"><label>Linguagem<select aria-label="Linguagem do código" value={language} disabled={busy} onChange={e=>{const next=e.target.value;setLanguage(next);setPreview(false);setMessage('');try{localStorage.setItem('elysia.code.draft.v1',JSON.stringify({language:next,code}));}catch{setMessage('Baixe o arquivo para preservar seu código.');}}}>{Object.keys(ext).map(v=><option key={v}>{v}</option>)}</select></label>
      <label>Nome do projeto<input aria-label="Nome do projeto de código" value={title} maxLength={80} disabled={busy} onChange={e=>setTitle(e.target.value)}/></label>
      <button className="pill-btn" disabled={busy} onClick={template}>Criar modelo inicial</button>
      <label>Código<textarea className="code-editor" aria-label="Editor de código" spellCheck={false} rows={15} maxLength={20000} value={code} disabled={busy} onChange={e=>changeCode(e.target.value)}/></label></div>
      <p className="muted">{code.split('\n').length} linhas · {code.length} caracteres. O rascunho fica neste navegador; baixe para fazer backup privado.</p>
      <div className="module-actions"><button className="pill-btn" disabled={!code||busy} onClick={()=>downloadBlob(new Blob([code],{type:'text/plain;charset=utf-8'}),'elysia-codigo-'+stamp()+'.'+ext[language])}>Baixar código</button>
      {['python','json'].includes(language)&&<button className="pill-btn ghost" disabled={busy||!code} onClick={validate}>Validar sintaxe</button>}
      {language==='html'&&<button className="pill-btn ghost" onClick={()=>setPreview(!preview)}>Prévia HTML sem scripts</button>}</div>
      {message&&<p role="status" className="module-notice">{message}</p>}
      {preview&&language==='html'&&<iframe className="code-preview" title="Prévia HTML isolada" sandbox="" srcDoc={safeHTML}/>}
      <p className="muted">HTML é exibido em uma prévia isolada, sem JavaScript, navegação externa ou envio de formulários. CSS e JavaScript podem ser editados e baixados, mas não são executados aqui.</p>
    </div>}</>;
};
Object.assign(window,{MediaStudioPanel,CodeStudioPanel});
