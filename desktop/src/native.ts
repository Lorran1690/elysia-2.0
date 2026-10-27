import {invoke,isTauri} from '@tauri-apps/api/core';
import {getCurrentWindow} from '@tauri-apps/api/window';
export const native=isTauri();
const originalFetch=window.fetch.bind(window);
export async function request(path:string,payload?:unknown):Promise<any>{const r=await fetch(path,payload===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const d=await r.json();if(!r.ok)throw Error(d.error||'Não foi possível concluir.');return d;}
async function saveBlobUrl(url:string,name:string){
 const data=await (await originalFetch(url)).arrayBuffer();
 return invoke('save_export',{name,bytes:Array.from(new Uint8Array(data))});
}
function wireDownloadClicks(doc:Document){doc.addEventListener('click',event=>{
 const anchor=(event.target as Element|null)?.closest<HTMLAnchorElement>('a[download]');
 if(anchor?.href.startsWith('blob:')){event.preventDefault();void saveBlobUrl(anchor.href,anchor.download||'elysia-export.webm').catch(e=>window.dispatchEvent(new CustomEvent('elysia-notice',{detail:String(e)})));}
},true);}
export function wireWorkspaceFrame(frame:HTMLIFrameElement){
 // The trusted bundled cinema keeps global navigation shortcuts available.
 frame.contentWindow?.addEventListener('keydown',event=>{
  if(((event.ctrlKey||event.metaKey)&&['k',','].includes(event.key.toLowerCase()))||event.key==='Escape'){
   event.preventDefault();window.dispatchEvent(new KeyboardEvent('keydown',{key:event.key,ctrlKey:event.ctrlKey,metaKey:event.metaKey,shiftKey:event.shiftKey,altKey:event.altKey}));
  }
 });
 if(native&&frame.contentDocument)wireDownloadClicks(frame.contentDocument);
}
export function setupNativeBridge(){if(!native)return;
 wireDownloadClicks(document);
 window.fetch=async(input,init)=>{
  if(typeof input==='string'&&input.startsWith('/api/')){
   const response=await invoke<{status:number;body:number[];mime:string}>('core_request',{path:input,method:init?.method||'GET',body:typeof init?.body==='string'?init.body:null});
   return new Response(new Uint8Array(response.body),{status:response.status,headers:{'Content-Type':response.mime}});
  }
  return originalFetch(input,init);
 };
 // A folder handle exists only after the native picker grants access this session.
 (window as any).showDirectoryPicker=async()=>{
  const folder=await invoke<{token:string;label:string}|null>('pick_export_folder');
  if(!folder)throw new DOMException('Seleção cancelada','AbortError');
  return {name:folder.label,queryPermission:async()=> 'granted',requestPermission:async()=> 'granted',
   getFileHandle:async(name:string,options?:{create?:boolean})=>{
    if(!options?.create&&!await invoke<boolean>('export_exists',{token:folder.token,name}))throw new DOMException('Arquivo não existe','NotFoundError');
    return {createWritable:async()=>{let bytes:number[]=[];return {write:async(blob:Blob)=>{bytes=Array.from(new Uint8Array(await blob.arrayBuffer()))},close:async()=>invoke('write_selected_export',{token:folder.token,name,bytes}),abort:async()=>{bytes=[]}}}};
   }};
 };
 const click=HTMLAnchorElement.prototype.click;
 HTMLAnchorElement.prototype.click=function(){if(this.download&&this.href.startsWith('blob:')){const name=this.download;saveBlobUrl(this.href,name).catch(e=>window.dispatchEvent(new CustomEvent('elysia-notice',{detail:String(e)})));return;}click.call(this);};
}
export async function readPrivateStore(){if(native)return invoke<string|null>('read_interface_store');return localStorage.getItem('elysia.interface.v2');}
export async function writePrivateStore(value:string){if(native)return invoke('write_interface_store',{value});localStorage.setItem('elysia.interface.v2',value);}
export function downloadJson(value:unknown,name:string){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),5000);}
export const diagnostics=()=>native?invoke<Record<string,unknown>>('diagnostics'):Promise.resolve({window:'Prévia no navegador',platform:navigator.platform,storage:'Armazenamento deste navegador',version:'2.2.0'});

export async function setNativeTheme(theme:'dark'|'light'|'system'){if(native)await getCurrentWindow().setTheme(theme==='system'?null:theme);}
