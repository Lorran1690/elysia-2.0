import test from 'node:test';
import assert from 'node:assert/strict';
import {calculateMobile,runMobileTool,inspectMobileFile,compareMobileSources,parseStrictMobileJson} from '../src/mobile-tools.ts';

test('arithmetic respects Python power precedence, floor division and signed remainder',()=>{
 for(const [expression,result] of [['17*3','51'],['-2**2','-4'],['(-2)**2','4'],['2**-2','0.25'],['-7//3','-3'],['-7%3','2'],['7%-3','-2'],['2**3**2','512'],['9007199254740993+2','9007199254740995']])assert.equal(String(calculateMobile(expression)),result,expression);
 for(const expression of ['globalThis.process.exit()','1/0','0**-1','2**13','(-1)**.5','1e101','1+'+'('.repeat(50)+'1'+')'.repeat(50)])assert.throws(()=>calculateMobile(expression),expression);
});
test('JSON validation rejects duplicate escaped keys, overflow and excessive nesting',async()=>{
 assert.throws(()=>parseStrictMobileJson('{"x":1,"\\u0078":2}'),/duplicada/);
 for(const value of ['{"a":1,}','[1,]','NaN','1e400','"unterminated','['.repeat(65)+'0'+']'.repeat(65)])assert.throws(()=>parseStrictMobileJson(value));
 assert.equal(parseStrictMobileJson('{"__proto__":{"x":1}}').__proto__.x,1);
 assert.equal({}.x,undefined);
 assert.match((await runMobileTool({tool:'json_validate',text:'{"nome":"Elysia","itens":[1,true,null]}'})).result,/JSON válido/);
});
test('hash and Unicode text statistics are calculated locally',async()=>{
 assert.equal((await runMobileTool({tool:'sha256',text:'abc'})).result,'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
 assert.deepEqual((await runMobileTool({tool:'text_stats',text:'Olá 🌙\r\nElysia'})).result,{characters:13,words:2,lines:2,utf8_bytes:17});
 await assert.rejects(()=>runMobileTool({tool:'python_validate',text:'x=1'}),/não está disponível no Android/);
});
test('scaffolds escape titles and remain deterministic templates',async()=>{
 const html=await runMobileTool({tool:'code_scaffold',language:'html',text:'<img src=x onerror="boom"> & título'});
 assert.ok(html.code.includes('&lt;img src=x onerror=&quot;boom&quot;&gt; &amp; título'));
 assert.ok(!html.code.includes('<img src=x'));
 const js=await runMobileTool({tool:'code_scaffold',language:'javascript',text:'Projeto "Elysia"\nlinhas'});
 assert.ok(js.code.includes('return "Projeto \\"Elysia\\"\\nlinhas";'));
 await assert.rejects(()=>runMobileTool({tool:'code_scaffold',language:'constructor',text:'x'}));
});
test('inspection hashes bytes and refuses malformed bounds without executing',async()=>{
 const data=Buffer.from('six printable chars\0another string\0');
 const report=await inspectMobileFile({name:'C:\\input\\note.bin',base64:data.toString('base64')});
 assert.equal(report.name,'note.bin');assert.equal(report.executed,false);assert.equal(report.size,data.length);assert.ok(report.strings.includes('another string'));assert.equal(report.format,'Desconhecido');
 for(const payload of [{name:'x',base64:'%%%='},{name:'x',base64:''},{name:'bad\0name',base64:'YQ=='},{name:'bad.exe',base64:Buffer.from('MZ').toString('base64')},{name:'bad.zip',base64:Buffer.from('PK\x03\x04').toString('base64')}])await assert.rejects(()=>inspectMobileFile(payload));
 const elf=Buffer.alloc(64);elf.set([0x7f,69,76,70,2,1]);elf.writeUInt16LE(183,18);elf.writeBigUInt64LE(0xffffffffffffffffn,24);
 const metadata=await inspectMobileFile({name:'binary',base64:elf.toString('base64')});assert.equal(metadata.format,'ELF');assert.equal(metadata.details.architecture,'ARM64');assert.equal(metadata.details.entry_address,'0xffffffffffffffff');
});
test('line comparison preserves hashes and never applies a change',async()=>{
 const diff=await compareMobileSources('def f():\n    return 1\n','def f():\n    return 2\n');
 assert.equal(diff.changed,true);assert.equal(diff.applied,false);assert.ok(diff.diff.includes('-    return 1'));assert.ok(diff.diff.includes('+    return 2'));assert.notEqual(diff.before_sha256,diff.after_sha256);
 assert.equal((await compareMobileSources('same','same')).changed,false);
 await assert.rejects(()=>compareMobileSources('x\n'.repeat(2001),''));
});
test('inspection accepts a bounded full-size file and reads ZIP directory without extraction',async()=>{
 const full=Buffer.alloc(4*1024*1024),metadata=await inspectMobileFile({name:'large.bin',base64:full.toString('base64')});
 assert.equal(metadata.size,full.length);assert.equal(metadata.entropy_bits_per_byte,0);
 const name=Buffer.from('AndroidManifest.xml'),local=Buffer.alloc(30),central=Buffer.alloc(46+name.length),end=Buffer.alloc(22);
 local.writeUInt32LE(0x04034b50);central.writeUInt32LE(0x02014b50);central.writeUInt16LE(name.length,28);name.copy(central,46);
 end.writeUInt32LE(0x06054b50);end.writeUInt16LE(1,8);end.writeUInt16LE(1,10);end.writeUInt32LE(central.length,12);end.writeUInt32LE(local.length,16);
 const zip=Buffer.concat([local,central,end]);
 const report=await inspectMobileFile({name:'sample.apk',base64:zip.toString('base64')});
 assert.equal(report.format,'APK/ZIP');assert.equal(report.details.entry_count,1);assert.equal(report.details.extracted,false);assert.equal(report.executed,false);
 end.writeUInt32LE(0xfffffff0,16);await assert.rejects(()=>inspectMobileFile({name:'truncated.zip',base64:Buffer.concat([local,central,end]).toString('base64')}));
});
