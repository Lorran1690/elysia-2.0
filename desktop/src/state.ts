import {appearanceDefaults,normalizeAppearance,type Appearance} from './appearance.ts';
export type View='chat'|'vault'|'create'|'develop'|'settings';
export type Message={role:'user'|'assistant';content:string};
export type Chat={id:string;title:string;messages:Message[];archived:boolean;updated:number};
export type Preferences={appearance:Appearance;theme:'dark'|'light'|'system';accent:'violet'|'ocean'|'rose';density:'comfortable'|'compact';fontSize:number;reduceMotion:boolean;sidebar:boolean;presence:boolean;enterToSend:boolean;timestamps:boolean;rememberChats:boolean;confirmDelete:boolean;musicVolume:number;musicTrack:string;pauseHidden:boolean;duckMusic:boolean;highContrast:boolean};
export const defaults:Preferences={appearance:{...appearanceDefaults,custom:{...appearanceDefaults.custom}},theme:'dark',accent:'violet',density:'comfortable',fontSize:100,reduceMotion:false,sidebar:true,presence:true,enterToSend:true,timestamps:false,rememberChats:true,confirmDelete:true,musicVolume:18,musicTrack:'aurora',pauseHidden:true,duckMusic:true,highContrast:false};
export type Store={format:'elysia-interface-v2';prefs:Preferences;chats:Chat[];active:string};
export const fresh=():Chat=>({id:crypto.randomUUID(),title:'Nova conversa',messages:[],archived:false,updated:Date.now()});
export function normalizePrefs(raw:unknown):Preferences {
 const p={...defaults,appearance:normalizeAppearance(null)};if(!raw||typeof raw!=='object')return p;const r=raw as Record<string,unknown>;
 p.appearance=normalizeAppearance(r.appearance);
 for(const k of Object.keys(p) as (keyof Preferences)[]){if(typeof p[k]==='boolean'&&typeof r[k]==='boolean')(p as any)[k]=r[k];}
 for(const [key,allowed] of Object.entries({theme:['dark','light','system'],accent:['violet','ocean','rose'],density:['comfortable','compact']}))if(allowed.includes(String(r[key])))(p as any)[key]=r[key];
 if(typeof r.fontSize==='number'&&Number.isFinite(r.fontSize))p.fontSize=Math.max(90,Math.min(125,r.fontSize));
 if(typeof r.musicVolume==='number'&&Number.isFinite(r.musicVolume))p.musicVolume=Math.max(0,Math.min(100,r.musicVolume));
 if(['aurora','orbita','foco'].includes(String(r.musicTrack)))p.musicTrack=String(r.musicTrack);
 return p;
}
export function validateMessages(raw:unknown):Message[]{
 if(!Array.isArray(raw)||raw.length>32||raw.length%2!==0)throw Error('Histórico inválido: até 16 pares de mensagens.');
 return raw.map((v,i)=>{if(!v||v.role!==(i%2?'assistant':'user')||typeof v.content!=='string'||!v.content.trim()||v.content.length>4000)throw Error('Mensagem inválida no backup.');return {role:v.role,content:v.content};});
}
export function validateStore(raw:unknown):Store {
 const r=raw as Store;if(!r||r.format!=='elysia-interface-v2'||!Array.isArray(r.chats)||r.chats.length>40)throw Error('Backup da interface inválido.');
 const ids=new Set<string>();const chats=r.chats.map(c=>{if(!c||typeof c.id!=='string'||c.id.length>80||ids.has(c.id)||typeof c.title!=='string'||c.title.length>100)throw Error('Conversa inválida.');ids.add(c.id);return {id:c.id,title:c.title,messages:validateMessages(c.messages),archived:c.archived===true,updated:Number.isFinite(c.updated)?c.updated:Date.now()};});
 if(!chats.length)chats.push(fresh());
 return {format:'elysia-interface-v2',prefs:normalizePrefs(r.prefs),chats,active:ids.has(r.active)?r.active:chats[0]?.id||''};
}
export const initialStore=():Store=>{const c=fresh();return {format:'elysia-interface-v2',prefs:{...defaults},chats:[c],active:c.id};};
