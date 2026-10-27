import {useEffect,useRef,useState} from 'react';
import {invoke} from '@tauri-apps/api/core';
import {listen} from '@tauri-apps/api/event';
import {native} from './native';

export type UpdateCandidate={version:string;build:number;source_sha:string;tag:string;bytes:number;sha256:string;release_url:string};
export type UpdateInfo={supported:boolean;installed:boolean;current_version:string;current_build:number;current_source:string;status:'unsupported'|'up-to-date'|'available';candidate:UpdateCandidate|null};
export type UpdateProgress={stage:'downloading'|'verified';downloaded:number;total:number};
export function useUpdater(beforeInstall:()=>Promise<void>){
 const [info,setInfo]=useState<UpdateInfo|null>(null),[stage,setStage]=useState<'idle'|'checking'|'available'|'current'|'downloading'|'verified'|'installing'|'error'>('idle'),[error,setError]=useState(''),[progress,setProgress]=useState<UpdateProgress|null>(null);
 const working=useRef(false),mounted=useRef(true),save=useRef(beforeInstall);save.current=beforeInstall;
 useEffect(()=>{
  mounted.current=true;let dispose:(()=>void)|undefined;
  if(native){void invoke<UpdateInfo>('updater_info').then(v=>{if(mounted.current)setInfo(v)}).catch(e=>{if(mounted.current)setError(String(e))});void listen<UpdateProgress>('elysia-update-progress',e=>{if(mounted.current)setProgress(e.payload)}).then(f=>{if(mounted.current)dispose=f;else f()}).catch(()=>{});}
  return()=>{mounted.current=false;dispose?.()};
 },[]);
 const run=async(action:'check'|'download'|'install')=>{
  if(working.current||!native)return;working.current=true;setError('');
  try{
   if(action==='check'){setStage('checking');setProgress(null);const value=await invoke<UpdateInfo>('check_update');if(mounted.current){setInfo(value);setStage(value.candidate?'available':'current')}}
   else if(action==='download'){setStage('downloading');setProgress(null);await invoke('download_update');if(mounted.current)setStage('verified')}
   else {setStage('installing');await save.current();await invoke('install_update');}
  }catch(e){if(mounted.current){setError(String(e));setStage('error')}}finally{working.current=false}
 };
 return {info,stage,error,progress,check:()=>run('check'),download:()=>run('download'),install:()=>run('install')};
}
export type Updater=ReturnType<typeof useUpdater>;
