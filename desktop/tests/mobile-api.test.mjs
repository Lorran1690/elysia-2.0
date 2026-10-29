import 'fake-indexeddb/auto';
import test,{beforeEach} from 'node:test';
import assert from 'node:assert/strict';
import {mobileRequest,digestVaultItems,readMobileStore,writeMobileStore} from '../src/mobile-api.ts';

const firstId='11111111-1111-4111-8111-111111111111';
const row=(number=1)=>({id:number.toString(16).padStart(8,'0')+'-1111-4111-8111-111111111111',kind:'note',title:'Nota '+number,content:'Texto privado de teste '+number,url:'',updated:'2026-10-28T12:00:00.000Z'});
const backup=async items=>({format:'elysia-vault-v1',items,sha256:await digestVaultItems(items)});
const call=async(path,body)=>{const response=await mobileRequest(path,body===undefined?'GET':'POST',body===undefined?undefined:JSON.stringify(body));return {status:response.status,data:await response.json()};};
beforeEach(async()=>{await new Promise((resolve,reject)=>{const request=indexedDB.deleteDatabase('elysia.mobile.v1');request.onsuccess=resolve;request.onerror=()=>reject(request.error);request.onblocked=()=>reject(Error('Test database left open'));});});

test('backup digest matches Python desktop for Unicode and preserves original timestamp',async()=>{
 const item={id:firstId,kind:'note',title:'Café e 🌸',content:'Linha um\nObservação, Unicode \u2028 e \u2029.',url:'https://example.org/fonte',updated:'2026-10-28T12:00:00.000Z'};
 assert.equal(await digestVaultItems([item]),'b423682a9d2d46665ef18c6b4d980f1e238fac6cf501e1f574dc92e012a9d56a');
 assert.equal((await call('/api/vault/restore',await backup([item]))).data.imported,1);
 const exported=(await call('/api/vault/backup')).data;
 assert.deepEqual(exported,await backup([item]));
 assert.equal((await call('/api/vault/restore',exported)).data.imported,0);
});
test('local health never claims conversation or media-model inference',async()=>{
 const health=await call('/api/health');assert.equal(health.status,200);assert.equal(health.data.ready,false);assert.equal(health.data.platform,'android');assert.equal(health.data.modules.vault,true);
 assert.equal((await call('/api/chat',{messages:[{role:'user',content:'Olá'}]})).status,503);
 assert.equal((await call('/api/generation/probe',{port:8188})).status,503);
 assert.deepEqual((await call('/api/generation/status')).data.jobs,[]);
 for(const path of ['https://attacker.invalid/api/vault','//attacker.invalid/api/vault','/api/../vault','/api/shell'])assert.equal((await call(path)).status,404);
});
test('private interface store awaits committed writes and rejects invalid replacement',async()=>{
 assert.equal(await readMobileStore(),null);
 const initial=JSON.stringify({format:'elysia-interface-v2',prefs:{},chats:[],active:''});
 await writeMobileStore(initial);assert.equal(await readMobileStore(),initial);
 await assert.rejects(writeMobileStore('invalid'));
 await assert.rejects(writeMobileStore('{"format":"untrusted"}'));
 assert.equal(await readMobileStore(),initial);
});
test('vault create update prefix search accents categories and delete work without a server',async()=>{
 const saved=await call('/api/vault/save',{kind:'note',title:'  Café de pesquisa  ',content:'Primeira observação local',url:''});assert.equal(saved.status,200);
 const item=saved.data.item;assert.equal(item.title,'Café de pesquisa');assert.ok(item.id);
 assert.equal((await call('/api/vault?q=caf&kind=note')).data.items.length,1);
 assert.equal((await call('/api/vault?q=afe&kind=note')).data.items.length,0);
 assert.equal((await call('/api/vault?q=cafe%20pesq&kind=document')).data.items.length,0);
 const updated=await call('/api/vault/save',{...item,content:'Nova revisão'});assert.equal(updated.data.item.content,'Nova revisão');
 assert.equal((await call('/api/vault/delete',{id:item.id})).data.deleted,true);
 assert.equal((await call('/api/vault')).data.items.length,0);
 assert.equal((await call('/api/vault/save',{...item,content:'Não recriar ID apagado'})).status,400);
});
test('restore conflict is atomic even when new entries precede conflicting record',async()=>{
 const original=row(1);await call('/api/vault/restore',await backup([original]));
 const before=(await call('/api/vault/backup')).data;
 const response=await call('/api/vault/restore',await backup([row(2),{...original,content:'Conteúdo conflitante'}]));
 assert.equal(response.status,400);assert.match(response.data.error,/Nada foi importado/);
 assert.deepEqual((await call('/api/vault/backup')).data,before);
});
test('restore validates tampering duplicates invalid text and URLs before any write',async()=>{
 const original=row(1);await call('/api/vault/restore',await backup([original]));
 const before=(await call('/api/vault/backup')).data;
 const corruptions=[{...(await backup([row(2)])),sha256:'0'.repeat(64)},await backup([row(2),row(2)]),await backup([{...row(3),url:'javascript:alert(1)'}]),await backup([{...row(4),content:'Bad\ud800'}])];
 for(const input of corruptions){assert.equal((await call('/api/vault/restore',input)).status,400);assert.deepEqual((await call('/api/vault/backup')).data,before);}
});
test('500 entry limit applies to concurrent saves and entire restores atomically',async()=>{
 const rows=Array.from({length:500},(_,i)=>row(i+1));
 const restored=await call('/api/vault/restore',await backup(rows));assert.equal(restored.data.imported,500);
 const attempts=await Promise.all([call('/api/vault/save',{title:'Extra 1',content:'Não deve entrar'}),call('/api/vault/save',{title:'Extra 2',content:'Não deve entrar'})]);
 assert.ok(attempts.every(r=>r.status===400));
 assert.equal((await call('/api/vault')).data.items.length,500);
 assert.equal((await call('/api/vault/restore',await backup([row(501)]))).status,400);
 assert.equal((await call('/api/vault')).data.items.length,500);
});
