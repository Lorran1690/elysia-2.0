import {registerPlugin} from '@capacitor/core';
import {App as AndroidApp} from '@capacitor/app';
import {Directory,Filesystem} from '@capacitor/filesystem';
import {Share} from '@capacitor/share';
import {androidNative} from './platform';
import type {UpdateInfo,UpdateProgress} from './updates';
import type {PluginListenerHandle} from '@capacitor/core';
interface AndroidUpdates {
 info():Promise<UpdateInfo>;
 check():Promise<UpdateInfo>;
 download():Promise<{verified:boolean;version:string;build:number;bytes:number;sha256:string}>;
 install():Promise<void>;
 addListener(event:'progress',callback:(value:UpdateProgress)=>void):Promise<PluginListenerHandle>;
}
export const androidUpdates=registerPlugin<AndroidUpdates>('ElysiaUpdates');
let sharing=false;
export async function shareAndroidBlob(blob:Blob,name:string){
 if(sharing)throw Error('Conclua o compartilhamento anterior antes de exportar outro arquivo.');
 if(blob.size>100*1024*1024)throw Error('No Android, exporte arquivos de até 100 MB.');
 if(!name||name.length>180||/[\\/\x00-\x1f]/.test(name)||name==='.'||name==='..')throw Error('Nome do arquivo inválido.');
 sharing=true;let path='';
 try{
  // Each exported file has a unique private directory. No owner file is replaced.
  path='exports/'+crypto.randomUUID()+'/'+name;
  const data=await new Promise<string>((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(Error('Não foi possível preparar o arquivo.'));reader.readAsDataURL(blob)});
  const result=await Filesystem.writeFile({path,directory:Directory.Cache,data,recursive:true});
  try{await Share.share({title:'Exportar '+name,files:[result.uri],dialogTitle:'Salvar ou compartilhar arquivo da Elysia'});}catch(error){
   if((error as {message?:string})?.message!=='Share canceled')throw error;
   window.dispatchEvent(new CustomEvent('elysia-notice',{detail:'Compartilhamento cancelado.'}));
  }
 }finally{sharing=false;}
}
export function setupAndroidShell(){
 if(!androidNative)return;
 void AndroidApp.addListener('backButton',()=>window.dispatchEvent(new Event('elysia-android-back')));
}
export const minimizeAndroid=()=>AndroidApp.minimizeApp();
