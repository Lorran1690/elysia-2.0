// Independent local modules. User documents never become neural training examples.
const { useState: useStateM, useEffect: useEffectM, useRef: useRefM } = React;
const moduleRequest = async (path, payload) => {
  const response = await fetch(path, payload === undefined ? {} : {
    method: 'POST', headers: {'Content-Type':'application/json'}, body:JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Não foi possível concluir.');
  return data;
};
const saveModuleFile = (data, name) => {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
  const link = document.createElement('a'); link.href=url; link.download=name; link.click();
  setTimeout(() => URL.revokeObjectURL(url),1000);
};
const EMPTY_ENTRY = {title:'',content:'',url:'',kind:'note'};

const VaultPanel = ({onClose}) => {
  const [kind,setKind] = useStateM('');
  const [query,setQuery] = useStateM('');
  const [items,setItems] = useStateM([]);
  const [draft,setDraft] = useStateM({...EMPTY_ENTRY});
  const [busy,setBusy] = useStateM(false);
  const [notice,setNotice] = useStateM('');
  const [error,setError] = useStateM('');
  const revision = useRefM(0);
  const refresh = async (search=query, category=kind) => {
    const version = ++revision.current;
    try {
      const result = await moduleRequest('/api/vault?q='+encodeURIComponent(search)+'&kind='+category);
      if (version === revision.current) setItems(result.items);
    } catch (err) { if (version === revision.current) setError(err.message); }
  };
  useEffectM(() => { refresh(query,kind); return () => { revision.current++; }; },[kind]);
  const action = async (work) => {
    setBusy(true); setError(''); setNotice('');
    try { await work(); } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };
  const save = (event) => {
    event.preventDefault();
    action(async () => { await moduleRequest('/api/vault/save',draft); setDraft({...EMPTY_ENTRY});
      setNotice('Registro salvo na biblioteca local.'); await refresh(); });
  };
  const remove = (item) => {
    if (!window.confirm('Excluir “'+item.title+'”? Exporte um backup antes se quiser preservar este registro.')) return;
    action(async () => { await moduleRequest('/api/vault/delete',{id:item.id});
      if (draft.id===item.id) setDraft({...EMPTY_ENTRY}); setNotice('Registro excluído.'); await refresh(); });
  };
  const exportBackup = () => action(async () => {
    const backup = await moduleRequest('/api/vault/backup');
    saveModuleFile(backup,'elysia-vault-backup-'+new Date().toISOString().replace(/[:.]/g,'-')+'.json');
    setNotice('Backup exportado. Guarde-o em armazenamento privado fora do computador.');
  });
  const restore = (file) => action(async () => {
    if (!file) return;
    if (file.size>64*1024*1024) throw new Error('Backup grande demais.');
    const data = JSON.parse(await file.text());
    const result = await moduleRequest('/api/vault/restore',data);
    setNotice(result.imported+' registros importados. Os registros existentes foram preservados.'); await refresh();
  });
  const importText = (file) => action(async () => {
    if (!file) return;
    if (!/\.(txt|md)$/i.test(file.name) || file.size>80000) throw new Error('Escolha um TXT ou Markdown de até 80 KB.');
    let text;
    try { text = new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer()); }
    catch { throw new Error('Salve o arquivo como UTF-8 antes de importar.'); }
    if (!text.trim() || text.length>20000 || text.includes('\u0000')) throw new Error('Texto vazio, inválido ou maior que 20.000 caracteres.');
    setDraft({kind:'document',title:file.name.slice(0,160),content:text,url:''});
    setNotice('Arquivo lido. Revise e clique em Salvar registro para importá-lo.');
  });
  return <>
    <PanelHead title="Knowledge Vault" kicker="Biblioteca privada" onClose={onClose}/>
    <div className="module-scroll">
      <p className="note-block">Documentos, notas e fontes ficam neste computador. A busca usa o texto salvo; o chat ainda não consulta esta biblioteca. Exporte um backup privado para proteger seus registros.</p>
      <div className="module-actions">
        <button className="pill-btn" disabled={busy} onClick={exportBackup}>Exportar biblioteca</button>
        <label className="module-file">Restaurar biblioteca<input aria-label="Restaurar biblioteca" type="file" accept=".json" disabled={busy} onChange={e=>{restore(e.target.files?.[0]);e.target.value='';}}/></label>
      </div>
      <div className="seg" role="tablist" aria-label="Coleções">
        {[['','Todos'],['document','Documentos'],['note','Notas'],['source','Fontes']].map(([id,label])=><button key={id} role="tab" aria-selected={kind===id} onClick={()=>setKind(id)}>{label}</button>)}
      </div>
      <form className="module-search" onSubmit={e=>{e.preventDefault();refresh();}}>
        <input aria-label="Buscar na biblioteca" placeholder="Buscar no título e conteúdo" value={query} onChange={e=>setQuery(e.target.value)} maxLength={300}/>
        <button className="pill-btn" type="submit">Buscar</button>
      </form>
      {error && <p role="alert" className="note-block">{error}</p>}
      {notice && <p role="status" className="module-notice">{notice}</p>}
      <p className="muted">{items.length} registros encontrados</p>
      <ul className="vault-list">{items.map(item=><li key={item.id}>
        <strong>{item.title}</strong><small>{({document:'Documento',note:'Nota',source:'Fonte'})[item.kind]}</small>
        <p>{item.content.slice(0,240)}{item.content.length>240?'…':''}</p>
        {item.url && <a href={item.url} target="_blank" rel="noopener noreferrer">Abrir fonte externa</a>}
        <div className="module-actions"><button disabled={busy} onClick={()=>setDraft({id:item.id,title:item.title,kind:item.kind,content:item.content,url:item.url})}>Abrir / editar</button>
        <button disabled={busy} onClick={()=>remove(item)}>Excluir</button></div>
      </li>)}</ul>
      <form className="module-form" onSubmit={save}>
        <h3>{draft.id?'Editar registro':'Novo registro'}</h3>
        <label>Tipo<select aria-label="Tipo de registro" value={draft.kind} disabled={busy} onChange={e=>setDraft({...draft,kind:e.target.value})}>
          <option value="note">Nota</option><option value="document">Documento</option><option value="source">Fonte</option>
        </select></label>
        <label>Título<input aria-label="Título do registro" required maxLength={160} value={draft.title} disabled={busy} onChange={e=>setDraft({...draft,title:e.target.value})}/></label>
        <label>Conteúdo<textarea aria-label="Conteúdo do registro" required maxLength={20000} rows={6} value={draft.content} disabled={busy} onChange={e=>setDraft({...draft,content:e.target.value})}/></label>
        <label>URL da fonte (opcional)<input aria-label="URL da fonte" type="url" maxLength={2048} value={draft.url} disabled={busy} onChange={e=>setDraft({...draft,url:e.target.value})}/></label>
        <div className="module-actions"><button className="pill-btn" disabled={busy} type="submit">Salvar registro</button>
        <button className="pill-btn ghost" disabled={busy} type="button" onClick={()=>setDraft({...EMPTY_ENTRY})}>Limpar formulário</button></div>
        <label className="module-file">Importar texto (.txt ou .md)<input aria-label="Importar texto" type="file" accept=".txt,.md" disabled={busy} onChange={e=>{importText(e.target.files?.[0]);e.target.value='';}}/></label>
      </form>
    </div>
  </>;
};

const WorkspacePanel = ({onClose,embedded=false}) => {
  const [tool,setTool] = useStateM('calculator'); const [text,setText] = useStateM('');
  const [result,setResult] = useStateM('');const [error,setError] = useStateM('');const [busy,setBusy] = useStateM(false);
  const run = async e => {e.preventDefault();setBusy(true);setError('');setResult('');
    try { const data=await moduleRequest('/api/tools',{tool,text});setResult(typeof data.result==='string'?data.result:JSON.stringify(data.result,null,2)); }
    catch(err){setError(err.message);} finally{setBusy(false);}
  };
  return <>{!embedded && <PanelHead title="Código e ferramentas" kicker="Ferramentas locais" onClose={onClose}/>}
    <div className="module-scroll"><p className="note-block">Resultados calculados diretamente por ferramentas locais. O texto não é executado como código nem enviado a serviços externos.</p>
      <form className="module-form" onSubmit={run}><label>Ferramenta<select aria-label="Ferramenta" value={tool} onChange={e=>{setTool(e.target.value);setResult('');setError('');}} disabled={busy}>
        <option value="calculator">Calculadora</option><option value="json_validate">Validar JSON</option>
        <option value="text_stats">Estatísticas de texto</option><option value="sha256">SHA-256 de texto</option>
      </select></label><label>Entrada<textarea aria-label="Entrada da ferramenta" rows={8} maxLength={20000} value={text} onChange={e=>setText(e.target.value)} disabled={busy}/></label>
      {tool==='calculator' && <p className="muted">Use números, ponto decimal, parênteses e + − * / // % **. Expoentes limitados a ±12.</p>}
      <button className="pill-btn" disabled={busy} type="submit">Executar ferramenta</button></form>
      {error && <p role="alert" className="note-block">{error}</p>}
      {result && <pre aria-label="Resultado da ferramenta" className="module-result">{result}</pre>}
      <p className="note-block">Terminal, execução de scripts e automações do sistema continuam indisponíveis. Estas ferramentas ainda não são acionadas pelo modelo de conversa.</p>
    </div></>;
};

const LocalMediaPanel = ({onClose,embedded=false}) => {
  const [tab,setTab] = useStateM('Imagem');const [media,setMedia] = useStateM(null);const [error,setError] = useStateM('');
  useEffectM(()=>()=>{if(media?.url)URL.revokeObjectURL(media.url);},[media]);
  const select = file => {
    setError(''); if(!file)return;
    const allowed={Imagem:['image/png','image/jpeg','image/webp','image/gif'],Áudio:['audio/mpeg','audio/wav','audio/x-wav','audio/ogg','audio/mp4','audio/x-m4a','audio/mp3'],Vídeo:['video/mp4','video/webm']};
    if (!allowed[tab].includes(file.type) || file.size>100*1024*1024) {setError('Formato não compatível ou arquivo maior que 100 MB.');return;}
    setMedia({url:URL.createObjectURL(file),name:file.name,size:file.size,type:tab});
  };
  return <>{!embedded && <PanelHead title="Media Studio" kicker="Visualização local" onClose={onClose}/>}
    <div className="module-scroll"><p className="note-block">Abra imagens, áudios e vídeos do seu computador. A visualização é temporária: o arquivo não é enviado ao núcleo, salvo na biblioteca ou publicado no GitHub.</p>
      <div className="seg" role="tablist" aria-label="Tipo de mídia">{['Imagem','Áudio','Vídeo'].map(t=><button key={t} role="tab" aria-selected={tab===t} onClick={()=>{setTab(t);setMedia(null);setError('');}}>{t}</button>)}</div>
      <label className="module-file">Escolher {tab.toLowerCase()}<input key={tab} aria-label="Abrir mídia local" type="file" accept={tab==='Imagem'?'.png,.jpg,.jpeg,.webp,.gif':tab==='Áudio'?'.mp3,.wav,.ogg,.m4a':'.mp4,.webm'} onChange={e=>select(e.target.files?.[0])}/></label>
      {error && <p role="alert" className="note-block">{error}</p>}
      {media && <figure className="media-preview">
        {media.type==='Imagem'?<img src={media.url} alt={media.name}/>:media.type==='Áudio'?<audio src={media.url} controls/>:<video src={media.url} controls/>}
        <figcaption>{media.name} · {(media.size/1024).toFixed(1)} KB</figcaption>
        <button className="pill-btn ghost" onClick={()=>setMedia(null)}>Fechar arquivo</button>
      </figure>}
      <p className="note-block">Geração, edição e reconhecimento de mídia ainda não estão conectados. O microfone permanece desligado.</p>
    </div></>;
};

Object.assign(window, { VaultPanel, WorkspacePanel, LocalMediaPanel });
