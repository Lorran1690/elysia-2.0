/** Private, offline Android modules. This adapter never contacts a server.
 * The Windows model and specialized generation engines are not mobile runtimes.
 */
import {runMobileTool,inspectMobileFile,compareMobileSources} from './mobile-tools.ts';

export type VaultItem={id:string;kind:'note'|'document'|'source';title:string;content:string;url:string;updated:string};
const MAX_ITEMS=500,MAX_CONTENT=20000,DB_NAME='elysia.mobile.v1';
const kinds=new Set(['note','document','source']);
const fields=['id','kind','title','content','url','updated'];
const neuralReason='O Neural Core próprio ainda não foi integrado ao Android. Nenhuma resposta de conversa é simulada; os módulos locais continuam disponíveis.';
const generationReason='Os modelos de imagem e vídeo e o ComfyUI não estão incluídos no Android. Use Composição e áudio ou Cinema 3D para criar mídia local com as ferramentas disponíveis.';
const unicodeLength=(value:string)=>Array.from(value).length;
function record(value:unknown):Record<string,unknown>{if(!value||typeof value!=='object'||Array.isArray(value))throw Error('Solicitação inválida.');return value as Record<string,unknown>}
function validUnicode(value:string){for(let i=0;i<value.length;i++){const c=value.charCodeAt(i);if(c>=0xd800&&c<=0xdbff){const next=value.charCodeAt(++i);if(!(next>=0xdc00&&next<=0xdfff))return false}else if(c>=0xdc00&&c<=0xdfff)return false;}return true;}
function id(value:unknown):string{if(typeof value!=='string'||!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(value))throw Error('Identificador inválido.');return value;}
function validateItem(raw:unknown,requireId=false):Omit<VaultItem,'id'|'updated'>&{id?:string}{
 const v=record(raw),out:Record<string,string>={};
 for(const [key,max] of [['title',160],['content',MAX_CONTENT],['url',2048]] as const){const text=v[key]===undefined?'':v[key];if(typeof text!=='string'||unicodeLength(text)>max||text.includes('\0')||!validUnicode(text))throw Error(`Campo ${key} inválido ou longo demais.`);out[key]=text.trim();}
 if(!out.title||!out.content)throw Error('Preencha título e conteúdo.');
 const kind=v.kind===undefined?'note':v.kind;if(typeof kind!=='string'||!kinds.has(kind))throw Error('Tipo de registro inválido.');
 if(out.url){let address:URL;try{address=new URL(out.url)}catch{throw Error('Use uma URL HTTP ou HTTPS sem credenciais.')}if(!['http:','https:'].includes(address.protocol)||!address.hostname||address.username||address.password)throw Error('Use uma URL HTTP ou HTTPS sem credenciais.');}
 return {title:out.title,content:out.content,url:out.url,kind:kind as VaultItem['kind'],...(requireId||v.id!==undefined?{id:id(v.id)}:{})};
}
function validateStored(raw:unknown):VaultItem{
 const r=record(raw),item=validateItem(raw,true);
 if(typeof r.updated!=='string'||r.updated.length>80||!Number.isFinite(Date.parse(r.updated)))throw Error('Data inválida no registro.');
 return {...item,id:item.id!,updated:r.updated};
}
function storageError(error:unknown){return error instanceof Error&&error.name==='QuotaExceededError'?Error('O armazenamento do telefone está cheio. Exporte um backup privado e libere espaço.'):Error('Não foi possível acessar a biblioteca privada. Reabra a Elysia sem limpar seus dados.');}
function database():Promise<IDBDatabase>{return new Promise((resolve,reject)=>{
 if(typeof indexedDB==='undefined'){reject(Error('O armazenamento privado não está disponível neste dispositivo.'));return;}
 let settled=false;const request=indexedDB.open(DB_NAME,1);
 request.onupgradeneeded=()=>{const db=request.result;if(!db.objectStoreNames.contains('entries'))db.createObjectStore('entries',{keyPath:'id'});if(!db.objectStoreNames.contains('private'))db.createObjectStore('private');};
 request.onerror=()=>{settled=true;reject(storageError(request.error))};
 request.onblocked=()=>{settled=true;reject(Error('Feche outras janelas da Elysia antes de abrir a biblioteca.'))};
 request.onsuccess=()=>{if(settled){request.result.close();return;}settled=true;request.result.onversionchange=()=>request.result.close();resolve(request.result)};
 });}
async function transaction<T>(name:'entries'|'private',mode:IDBTransactionMode,work:(store:IDBObjectStore,set:(value:T)=>void,fail:(error:unknown)=>void)=>void):Promise<T>{
 const db=await database();
 try{return await new Promise<T>((resolve,reject)=>{
  const tx=db.transaction(name,mode);let result:T,error:unknown;
  const fail=(e:unknown)=>{error=e;try{tx.abort()}catch{reject(e)}};
  tx.oncomplete=()=>resolve(result);tx.onabort=()=>reject(error||storageError(tx.error));tx.onerror=()=>{};
  try{work(tx.objectStore(name),v=>{result=v},fail)}catch(e){fail(e)}
 })}finally{db.close()}
}
export async function readMobileStore():Promise<string|null>{return transaction('private','readonly',(store,set,fail)=>{const req=store.get('interface-v2');req.onsuccess=()=>{if(req.result===undefined)set(null);else if(typeof req.result==='string')set(req.result);else fail(Error('Não foi possível ler os dados privados da interface.'))};});}
export async function writeMobileStore(value:string):Promise<void>{
 if(typeof value!=='string'||value.length>8*1024*1024)throw Error('Backup da interface grande demais.');
 const data=JSON.parse(value);if(data?.format!=='elysia-interface-v2')throw Error('Formato inválido da interface.');
 await transaction<void>('private','readwrite',(store,set)=>{store.put(value,'interface-v2');set(undefined)});
}
async function allItems():Promise<VaultItem[]>{return transaction('entries','readonly',(store,set,fail)=>{const req=store.getAll(undefined,MAX_ITEMS+1);req.onsuccess=()=>{try{if(req.result.length>MAX_ITEMS)throw Error('A biblioteca excede o limite de 500 registros. Nenhum dado foi alterado.');set(req.result.map(validateStored))}catch(e){fail(e)}};});}
function codepointOrder(a:string,b:string){const x=Array.from(a),y=Array.from(b);for(let i=0;i<Math.min(x.length,y.length);i++){const d=x[i].codePointAt(0)!-y[i].codePointAt(0)!;if(d)return d;}return x.length-y.length;}
function canonical(value:unknown):string{
 if(value===null||typeof value!=='object'){const text=JSON.stringify(value);if(text===undefined)throw Error('Valor inválido no backup.');return text;}
 if(Array.isArray(value))return '['+value.map(canonical).join(',')+']';
 const r=value as Record<string,unknown>;return '{'+Object.keys(r).sort(codepointOrder).map(k=>JSON.stringify(k)+':'+canonical(r[k])).join(',')+'}';
}
export async function digestVaultItems(items:unknown[]):Promise<string>{const bytes=new TextEncoder().encode(canonical(items));return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');}
function normalizeSearch(value:string){return value.normalize('NFD').replace(/\p{M}/gu,'').toLocaleLowerCase('pt-BR');}
async function listItems(query:string,kind:string){
 if(unicodeLength(query)>300||(kind&&!kinds.has(kind)))throw Error('Busca inválida.');
 const tokens=(normalizeSearch(query).match(/[\p{L}\p{N}_]+/gu)||[]).slice(0,10);
 const rows=await allItems();
 return rows.filter(item=>{if(kind&&item.kind!==kind)return false;if(!query.trim())return true;if(!tokens.length)return false;const words=normalizeSearch(item.title+' '+item.content).match(/[\p{L}\p{N}_]+/gu)||[];return tokens.every(t=>words.some(w=>w.startsWith(t)));}).sort((a,b)=>b.updated.localeCompare(a.updated)||codepointOrder(a.id,b.id));
}
async function saveItem(raw:unknown):Promise<VaultItem>{
 const clean=validateItem(raw),item:VaultItem={...clean,id:clean.id||crypto.randomUUID(),updated:new Date().toISOString()};
 return transaction('entries','readwrite',(store,set,fail)=>{const request=clean.id?store.get(clean.id):store.count();request.onsuccess=()=>{try{if(clean.id&&!request.result)throw Error('Registro não encontrado.');if(!clean.id&&Number(request.result)>=MAX_ITEMS)throw Error('Limite de 500 registros atingido. Exporte um backup.');store.put(item);set(item)}catch(e){fail(e)}};});
}
async function deleteItem(identifier:unknown){const key=id(identifier);await transaction<void>('entries','readwrite',(store,set)=>{store.delete(key);set(undefined)});}
async function backupVault(){const items=(await allItems()).sort((a,b)=>codepointOrder(a.id,b.id));return {format:'elysia-vault-v1',items,sha256:await digestVaultItems(items)};}
async function restoreVault(raw:unknown){
 const data=record(raw);if(data.format!=='elysia-vault-v1'||!Array.isArray(data.items)||data.items.length>MAX_ITEMS||typeof data.sha256!=='string'||!/^[0-9a-f]{64}$/.test(data.sha256))throw Error('Backup inválido, alterado ou grande demais.');
 // Validate and bound every value before canonicalizing untrusted import data.
 const rows=data.items.map((r:unknown)=>{const obj=record(r);if(Object.keys(obj).some(k=>!fields.includes(k))||fields.some(k=>typeof obj[k]!=='string'))throw Error('Registro inválido no backup.');return validateStored(obj)});
 if(new Set(rows.map((r:VaultItem)=>r.id)).size!==rows.length)throw Error('Backup contém identificadores duplicados.');
 if(data.sha256!==await digestVaultItems(data.items))throw Error('Backup inválido, alterado ou grande demais.');
 return transaction<number>('entries','readwrite',(store,set,fail)=>{const request=store.getAll(undefined,MAX_ITEMS+1);request.onsuccess=()=>{try{
  const current=request.result.map(validateStored);if(current.length>MAX_ITEMS)throw Error('A biblioteca excede o limite permitido. Nenhum dado foi alterado.');
  const existing=new Map(current.map((r:VaultItem)=>[r.id,r]));const added:VaultItem[]=[];
  for(const row of rows){const old=existing.get(row.id);if(old){if((['title','content','kind','url'] as const).some(k=>old[k]!==row[k]))throw Error('Há registros com o mesmo identificador e conteúdo diferente. Nada foi importado.');}else added.push(row);}
  if(current.length+added.length>MAX_ITEMS)throw Error('A importação ultrapassaria 500 registros. Nada foi importado.');
  for(const row of added)store.add(row);set(added.length);
 }catch(e){fail(e)}};});
}
const capabilityRows=[
 ['neural','Neural Core','planejada',neuralReason,'chat',false],
 ['vault','Biblioteca privada','implementada','Notas, TXT/Markdown, fontes, busca por prefixos e backups privados compatíveis com o desktop.','library',true],
 ['code','Código e ferramentas','parcial','Editor, modelos iniciais, SHA-256, JSON, estatísticas e calculadora local. Não executa código.','code',true],
 ['workbench','Bancada de análise','parcial','Metadados de arquivos, hashes, strings e revisão de texto. Análise AST Python indisponível no telefone.','workbench',true],
 ['image','Geração por modelos de IA','planejada',generationReason,null,false],
 ['media','Composição de mídia','parcial','Composições PNG, áudio WAV e animações quando o Android suporta o formato escolhido. Sem modelo de geração por IA.','media',true],
 ['avatar','Orbes e avatares','implementada','Identidade original, controles de aparência e visualização central adaptada à tela.','capabilities',true],
 ['audio','Música de fundo','implementada','Três faixas originais incluídas, seleção, volume e pausa.','media',true],
 ['voice','Voice Core','pausada','Voz e microfone permanecem pausados.',null,false],
 ['drive','Backup privado','parcial','Exporte e compartilhe arquivos com um destino escolhido. Não existe sincronização automática com o Drive.','library',true],
 ] as const;
function capabilities(){return {format:'elysia-capabilities-v1',platform:'android',reference_date:'2026-10-28',neural_weights_changed:false,voice_core_paused:true,capabilities:capabilityRows.map(([identifier,name,status,description,panel,offline])=>({id:identifier,name,status,description,panel,offline,limitations:description,requirements:'Elysia Android e Android System WebView atualizado.',permissions:'Operações locais explícitas. Documentos e conversas não são enviados a servidores.',license:'Implementação própria; dependências mantêm suas licenças.',origin:'Elysia Android; recursos offline descritos neste catálogo.'}))};}
function response(status:number,value:unknown){return new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});}
export async function mobileRequest(path:string,method='GET',body?:string|null):Promise<Response>{
 try{
  if(typeof path!=='string'||!path.startsWith('/api/')||path.length>4096||path.includes('\\')||path.includes('#')||path.includes('..')||!['GET','POST'].includes(method))return response(404,{error:'Rota local não encontrada.'});
  const url=new URL(path,'https://elysia.invalid');let payload:Record<string,unknown>={};
  if(method==='POST'){if(typeof body!=='string'||body.length>64*1024*1024)throw Error('Entrada inválida ou grande demais.');payload=record(JSON.parse(body));}
  if(method==='GET'){
   if(url.pathname==='/api/health')return response(200,{ready:false,platform:'android',model:'Neural Core próprio ainda não integrado ao Android',reason:neuralReason,voice:false,modules:{vault:true,tools:true,media:true}});
   if(url.pathname==='/api/capabilities')return response(200,capabilities());
   if(url.pathname==='/api/vault')return response(200,{items:await listItems(url.searchParams.get('q')||'',url.searchParams.get('kind')||''),search_engine:'Busca local por prefixos; sem ranking FTS5.'});
   if(url.pathname==='/api/vault/backup')return response(200,await backupVault());
   if(url.pathname==='/api/generation/status')return response(200,{platform:'android',available:false,reason:generationReason,port:8188,jobs:[]});
  }else{
   if(url.pathname==='/api/chat')return response(503,{error:neuralReason});
   if(url.pathname==='/api/vault/save')return response(200,{item:await saveItem(payload)});
   if(url.pathname==='/api/vault/delete'){await deleteItem(payload.id);return response(200,{deleted:true});}
   if(url.pathname==='/api/vault/restore')return response(200,{imported:await restoreVault(payload)});
   if(url.pathname==='/api/tools')return response(200,await runMobileTool(payload));
   if(url.pathname==='/api/workbench/inspect')return response(200,await inspectMobileFile(payload));
   if(url.pathname==='/api/workbench/diff')return response(200,await compareMobileSources(payload.before,payload.after));
   if(url.pathname==='/api/workbench/source')return response(503,{error:'A análise de estrutura Python depende do runtime do computador e ainda não está integrada ao Android. O editor e a revisão de texto funcionam localmente.'});
   if(url.pathname.startsWith('/api/generation/'))return response(503,{error:generationReason});
  }
  return response(404,{error:'Rota local não encontrada.'});
 }catch(error){return response(400,{error:error instanceof Error?error.message:'Não foi possível concluir a operação local. Seus dados anteriores foram preservados.'});}
}
