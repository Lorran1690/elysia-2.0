export const tracks=[{id:'aurora',title:'Aurora violeta',mood:'Ambient · acolhedora',src:'/music/aurora.mp3'},{id:'orbita',title:'Órbita tranquila',mood:'Eletrônica · contemplativa',src:'/music/orbita.mp3'},{id:'foco',title:'Entre pensamentos',mood:'Minimalista · concentração',src:'/music/foco.mp3'}];
class MusicPlayer {
 audio=new Audio();context:AudioContext|null=null;analyser:AnalyserNode|null=null;playing=false;volume=.18;duck=false;listeners=new Set<()=>void>();current='aurora';error='';
 constructor(){this.audio.hidden=true;this.audio.dataset.owner='elysia-background';document.body.append(this.audio);this.audio.loop=true;this.audio.preload='none';this.audio.src=tracks[0].src;this.audio.addEventListener('error',()=>{this.error='Não foi possível abrir esta faixa.';this.playing=false;this.emit();});}
 emit(){this.listeners.forEach(f=>f());}
 async play(){try{if(!this.context){this.context=new AudioContext();const source=this.context.createMediaElementSource(this.audio);this.analyser=this.context.createAnalyser();this.analyser.fftSize=64;source.connect(this.analyser);this.analyser.connect(this.context.destination);}await this.context.resume();await this.audio.play();this.playing=true;this.error='';}catch{this.error='Clique em Reproduzir para autorizar o áudio.';this.playing=false;}this.emit();}
 pause(){this.audio.pause();this.playing=false;this.emit();}
 setTrack(id:string,src?:string){if(this.current===id)return;const resume=this.playing;this.audio.pause();this.current=id;this.audio.src=src||tracks.find(t=>t.id===id)?.src||tracks[0].src;if(resume)void this.play();this.emit();}
 setVolume(v:number,duck=false){this.volume=v/100;this.duck=duck;this.audio.volume=Math.max(0,Math.min(1,this.volume*(duck?.25:1)));}
}
export const music=new MusicPlayer();
