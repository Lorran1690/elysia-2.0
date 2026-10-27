/** Original v11 visual parameters and an explicit form selection. */
export type Appearance={palette:string;custom:{from:string;to:string};size:number;speed:number;morph:boolean;avatar:'bust'|'body';orbCount:number;holoCount:number;holoScale:number;greet:boolean;mode:'auto'|'orb'|'avatar'};
export const appearanceDefaults:Appearance={palette:'original',custom:{from:'#8b5cf6',to:'#d946ef'},size:212,speed:1,morph:true,avatar:'bust',orbCount:720,holoCount:12000,holoScale:.86,greet:true,mode:'auto'};
export const paletteKeys=['original','white','gold','silver','ice','ocean','aurora','emerald','mint','sunset','fire','ruby','rose','roseGold','lavender','cosmic'] as const;
const hex=/^#[0-9a-f]{6}$/i;
const number=(raw:unknown,min:number,max:number,fallback:number)=>typeof raw==='number'&&Number.isFinite(raw)?Math.min(max,Math.max(min,raw)):fallback;
export function normalizeAppearance(raw:unknown):Appearance{
 const r=raw&&typeof raw==='object'?raw as Record<string,unknown>:{};const c=r.custom&&typeof r.custom==='object'?r.custom as Record<string,unknown>:{};
 return {palette:r.palette==='custom'||paletteKeys.includes(r.palette as typeof paletteKeys[number])?String(r.palette):'original',custom:{from:typeof c.from==='string'&&hex.test(c.from)?c.from.toLowerCase():appearanceDefaults.custom.from,to:typeof c.to==='string'&&hex.test(c.to)?c.to.toLowerCase():appearanceDefaults.custom.to},size:Math.round(number(r.size,120,640,212)),speed:number(r.speed,0,2,1),morph:r.morph!==false,avatar:r.avatar==='body'?'body':'bust',orbCount:Math.round(number(r.orbCount,360,6000,720)),holoCount:Math.round(number(r.holoCount,3000,30000,12000)),holoScale:number(r.holoScale,.45,1,.86),greet:r.greet!==false,mode:r.mode==='orb'||r.mode==='avatar'?r.mode:'auto'};
}
export function loadLegacyAppearance():Appearance{try{return normalizeAppearance(JSON.parse(localStorage.getItem('elysia.appearance.v1')||'null'))}catch{return normalizeAppearance(null)}}
export function fitAppearance(appearance:Appearance,width:number,height:number):Appearance{return {...appearance,size:Math.round(Math.min(640,Math.max(120,Math.min(width,height)*.6))/4)*4,holoScale:.9}}
