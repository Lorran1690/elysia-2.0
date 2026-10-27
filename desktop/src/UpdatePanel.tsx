import {Download,RefreshCw,ShieldCheck} from 'lucide-react';
import {native} from './native';
import type {Updater} from './updates';

export function UpdatePanel({updater:u,blocked=false}:{updater:Updater;blocked?:boolean}){
 const pending=['checking','downloading','installing'].includes(u.stage),candidate=u.info?.candidate;
 const percent=u.progress?.total?Math.min(100,Math.floor(u.progress.downloaded/u.progress.total*100)):0;
 return <section className="settings-card update-card" aria-label="Atualizações da Elysia">
  <h3><RefreshCw size={18}/>Atualizações do aplicativo</h3>
  <p className="small-note">{u.info?`Versão ${u.info.current_version}${u.info.current_build?` · compilação ${u.info.current_build}`:''}`:'Elysia Desktop 2.2'}. Busque e instale novas versões por aqui.</p>
  {!native?<p className="small-note">A atualização integrada está disponível no aplicativo Windows instalado.</p>:u.info&&!u.info.installed?<p className="small-note">Esta é a edição portátil. Instale a Elysia pelo instalador para usar as atualizações internas.</p>:null}
  <div className="module-actions"><button className="secondary" disabled={!native||pending||u.stage==='verified'} onClick={()=>void u.check()}><RefreshCw size={15}/>{u.stage==='checking'?'Verificando…':'Verificar atualizações'}</button>
   {candidate&&u.info?.installed&&u.stage!=='verified'&&u.stage!=='installing'&&<button className="secondary" disabled={pending} onClick={()=>void u.download()}><Download size={15}/>{u.stage==='downloading'?'Baixando…':'Baixar atualização'}</button>}
   {u.stage==='verified'&&<button className="secondary" disabled={blocked} onClick={()=>void u.install()}><ShieldCheck size={15}/>Fechar Elysia e instalar</button>}
  </div>
  <div aria-live="polite" className="update-status">
   {u.stage==='current'&&u.info?.supported&&<p className="status-success">Você está na versão mais recente disponível.</p>}
   {candidate&&<p>Nova versão: {candidate.version} · compilação {candidate.build} · {(candidate.bytes/1024/1024).toFixed(1)} MB</p>}
   {u.stage==='downloading'&&<><progress aria-label="Progresso da atualização" value={percent} max={100}/><p>{u.progress?`${percent}% · ${(u.progress.downloaded/1024/1024).toFixed(1)} MB recebidos`:'Preparando download…'}</p></>}
   {u.stage==='verified'&&<p className="status-success">Download concluído e SHA-256 verificado. Pronto para instalar.</p>}
   {u.stage==='installing'&&<p>Abrindo o instalador e fechando a Elysia…</p>}
   {u.error&&<p role="alert" className="danger">{u.error}</p>}
  </div>
  <p className="small-note">As versões vêm do repositório oficial da Elysia no GitHub. A instalação mantém suas conversas e preferências. Salve seus arquivos abertos nos editores antes de instalar.{blocked?' Aguarde a resposta em andamento antes de instalar.':''}</p>
 </section>;
}
