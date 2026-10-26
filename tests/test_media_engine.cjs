const {test}=require('node:test');const assert=require('node:assert/strict');
const engine=require('../interface/web/src/media-engine.js');
const project=()=>JSON.parse(JSON.stringify(engine.DEFAULT));
test('rejects malformed projects, external images and excessive budgets',()=>{
 assert.equal(engine.validate(project()).width,640);
 for(const patch of [{duration:99},{width:10000},{image:'https://example.org/pic.png'},{image:'data:image/svg+xml;base64,YQ=='},{accent:'url(x)'}])assert.throws(()=>engine.validate({...project(),...patch}));
 assert.throws(()=>engine.validate({...project(),audio:{...project().audio,notes:'C4 '.repeat(64),tempo:60}}));
});
test('notes respect octaves, sharps and rests',()=>{assert.equal(engine.notes('A4 R')[0],440);assert.equal(engine.notes('A4 R')[1],0);assert.throws(()=>engine.notes('C99'));assert.throws(()=>engine.notes(''));});
test('WAV output has correct PCM headers, length and bounded samples',async()=>{
 const audio={...project().audio,mode:'tone',duration:1,frequency:440};
 const blob=engine.waveAudio(audio);const buffer=await blob.arrayBuffer();const view=new DataView(buffer);
 assert.equal(blob.type,'audio/wav');assert.equal(blob.size,44+22050*2);assert.equal(new TextDecoder().decode(buffer.slice(0,4)),'RIFF');assert.equal(view.getUint32(24,true),22050);
 let peak=0;for(let i=44;i<buffer.byteLength;i+=2)peak=Math.max(peak,Math.abs(view.getInt16(i,true)));assert.ok(peak>1000&&peak<=6554);assert.equal(view.getInt16(44,true),0);
});
