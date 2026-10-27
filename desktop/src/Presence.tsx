import {memo,useEffect,useRef,useState} from 'react';
import {Maximize2,Minimize2,Move,Hand,X} from 'lucide-react';
import {ElysiaPresence,PALETTES} from 'virtual:elysia-modules';
import {fitAppearance,type Appearance} from './appearance';
import './appearance.css';
let greetedThisSession=false;
export type PresenceProps={appearance:Appearance;state:string;onCenter?:()=>void;variant?:'side'|'preview'|'center';demoState?:string;level?:number;waveKey?:number};
export const Presence=memo(function Presence({appearance:p,state,onCenter,variant='side',demoState,level=-1,waveKey=0}:PresenceProps){
 const box=useRef<HTMLDivElement>(null),levelRef=useRef(level);levelRef.current=level;
 const [size,setSize]=useState({w:0,h:0}),[form,setForm]=useState(0),[wave,setWave]=useState(0),[waving,setWaving]=useState(false);
 useEffect(()=>{const r=new ResizeObserver(([e])=>setSize({w:Math.floor(e.contentRect.width),h:Math.floor(e.contentRect.height)}));if(box.current)r.observe(box.current);return()=>r.disconnect()},[]);
 useEffect(()=>{if(!waveKey)return;setWaving(true);setWave(v=>v+1)},[waveKey]);
 useEffect(()=>{if(variant!=='side'||greetedThisSession)return;greetedThisSession=true;if(p.greet&&p.mode!=='orb'){setWaving(true);setWave(v=>v+1)}},[]);
 useEffect(()=>{if(!waving)return;const timer=setTimeout(()=>setWaving(false),9000);return()=>clearTimeout(timer)},[waving,wave]);
 const actualState=demoState||state;const c=p.palette==='custom'?p.custom:PALETTES[p.palette]||PALETTES.original;
 const target=p.mode==='avatar'||(p.mode==='auto'&&(waving||(p.morph&&actualState==='speaking')))?1:0;
 const renderSize=Math.max(60,Math.min(p.size,Math.floor(size.w*.88),Math.floor(size.h*.88)));
 return <aside className={'presence-pane presence-'+variant} data-presence-mode={p.mode} data-avatar={p.avatar} data-palette={p.palette} data-orb-count={p.orbCount} data-holo-count={p.holoCount} data-orb-speed={p.speed}>
 <div className="presence-heading"><span className="live-dot"/> {variant==='side'?'PRESENÇA ELYSIA':'ORBE E AVATAR'}{onCenter&&<button className="icon-btn presence-expand" aria-label="Centralizar orbe e avatar" title="Ver no centro da tela" onClick={onCenter}><Maximize2 size={15}/></button>}</div>
 <div ref={box} className="presence-canvas">{size.w>0&&size.h>0&&<ElysiaPresence state={actualState} size={renderSize} speed={p.speed} colorFrom={c.from} colorTo={c.to} levelRef={levelRef} form={target} onForm={setForm} avatar={p.avatar} orbCount={p.orbCount} holoCount={p.holoCount} holoScale={p.holoScale} waveKey={wave} onWaveEnd={()=>setWaving(false)} width={size.w} height={size.h} label={'Presença da Elysia · '+(p.mode==='avatar'?'avatar':p.mode==='orb'?'orbe':form>.5?'avatar':'orbe')}/>}</div>
 <div className="presence-caption"><span className="live-dot"/>{demoState?'Prévia de movimento':actualState==='thinking'?'Elaborando resposta':actualState==='speaking'?'Apresentando resposta':'Aqui com você'}<small>{p.mode==='auto'?'Forma automática':p.mode==='avatar'?'Avatar fixo':'Orbe fixo'} · {form>.5?(p.avatar==='body'?'Cintura para cima':'Busto'):'Orbe de partículas'}</small></div></aside>
});
export function CenteredPresence({appearance,onChange,state,onClose}:{appearance:Appearance;onChange:(p:Appearance)=>void;state:string;onClose:()=>void}){
 const modal=useRef<HTMLElement>(null),close=useRef(onClose),[wave,setWave]=useState(0);close.current=onClose;
 useEffect(()=>{const previous=document.activeElement as HTMLElement|null;modal.current?.querySelector<HTMLButtonElement>('button')?.focus();const key=(e:KeyboardEvent)=>{if(e.key==='Escape'){e.preventDefault();e.stopImmediatePropagation();close.current()}if(e.key==='Tab'){const nodes=modal.current?.querySelectorAll<HTMLButtonElement>('button:not([disabled])');if(!nodes?.length)return;const first=nodes[0],last=nodes[nodes.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus()}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus()}}};window.addEventListener('keydown',key,true);return()=>{window.removeEventListener('keydown',key,true);previous?.focus()}},[]);
 return <section className="presence-focus" role="dialog" aria-modal="true" aria-labelledby="presence-focus-heading" ref={modal}>
 <header><div><span className="eyebrow">PRESENÇA ELYSIA</span><h2 id="presence-focus-heading">No centro do seu espaço</h2></div><button className="secondary" onClick={onClose} aria-label="Fechar visualização central"><Minimize2 size={16}/>Voltar <kbd>Esc</kbd></button></header>
 <div className="presence-focus-stage"><Presence appearance={appearance} state={state} variant="center" waveKey={wave}/></div>
 <footer><div className="presence-modes" role="group" aria-label="Forma da presença central">{[['auto','Automático'],['orb','Orbe'],['avatar','Avatar']].map(([id,label])=><button key={id} aria-pressed={appearance.mode===id} onClick={()=>onChange({...appearance,mode:id as Appearance['mode']})}>{label}</button>)}</div><div className="presence-focus-actions"><button className="secondary" onClick={()=>onChange(fitAppearance(appearance,window.innerWidth-80,window.innerHeight-220))}><Move size={15}/>Ajustar à tela</button><button className="secondary" onClick={()=>{onChange({...appearance,mode:'avatar'});setWave(v=>v+1)}}><Hand size={15}/>Acenar</button><button className="icon-btn" aria-label="Fechar presença central" onClick={onClose}><X size={19}/></button></div></footer>
 <p className="presence-focus-note">Escolha Orbe ou Avatar para manter a forma visível. As alterações ficam salvas em Aparência.</p>
 </section>
}
