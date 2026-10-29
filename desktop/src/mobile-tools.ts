/** Bounded offline tools. User text and selected files are never executed. */
const MAX_TEXT=20000,MAX_FILE=4*1024*1024,BIG_BOUND=10n**100n;
type Numeric=number|bigint;
const fail=(message:string):never=>{throw Error(message)};
const textLength=(text:string)=>Array.from(text).length;
function textInput(raw:unknown,max=MAX_TEXT):string{return typeof raw==='string'&&textLength(raw)<=max?raw:fail('Entrada inválida ou longa demais.')}
function bounded(value:Numeric):Numeric{
 if(typeof value==='bigint'){if(value>BIG_BOUND||value< -BIG_BOUND)fail('Número fora do limite permitido.');}
 else if(!Number.isFinite(value)||Math.abs(value)>1e100)fail('Número fora do limite permitido.');
 return value;
}
const zero=(value:Numeric)=>value===0||value===0n;
function operate(op:string,a:Numeric,b:Numeric):Numeric{
 if(['/', '//','%'].includes(op)&&zero(b))fail('Operação inválida ou divisão por zero.');
 if(op==='**'){
  if(Math.abs(Number(b))>12)fail('Expoente fora do limite de -12 a 12.');
  return bounded(typeof a==='bigint'&&typeof b==='bigint'&&b>=0n?a**b:Number(a)**Number(b));
 }
 if(typeof a==='bigint'&&typeof b==='bigint'){
  if(op==='+')return bounded(a+b);if(op==='-')return bounded(a-b);if(op==='*')return bounded(a*b);
  if(op==='//'){const q=a/b,r=a%b;return bounded(r!==0n&&(a<0n)!==(b<0n)?q-1n:q);}
  if(op==='%'){const r=a%b;return bounded(r!==0n&&(r<0n)!==(b<0n)?r+b:r);}
 }
 const left=Number(a),right=Number(b);
 if(op==='+')return bounded(left+right);if(op==='-')return bounded(left-right);if(op==='*')return bounded(left*right);
 if(op==='/')return bounded(left/right);if(op==='//')return bounded(Math.floor(left/right));
 const remainder=left%right;return bounded(remainder!==0&&(remainder<0)!==(right<0)?remainder+right:remainder);
}
export function calculateMobile(raw:string):Numeric{
 const source=textInput(raw,200).trim();let at=0,nodes=0,depth=0;
 const skip=()=>{while(/\s/.test(source[at]||'')&&at<source.length)at++};
 const token=(value:string)=>{skip();if(source.startsWith(value,at)){at+=value.length;return true}return false};
 const count=()=>{if(++nodes>64)fail('Expressão complexa demais.')};
 const nested=(fn:()=>Numeric)=>{if(++depth>32)fail('Expressão complexa demais.');try{return fn()}finally{depth--}};
 const atom=():Numeric=>nested(()=>{
  if(token('(')){const value=expression();if(!token(')'))fail('Expressão aritmética inválida.');return value;}
  skip();const match=/^(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?/.exec(source.slice(at));
  if(!match)fail('Use somente números e operadores aritméticos.');
  const literal=match![0];if(/^0\d/.test(literal)&&!/[.eE]/.test(literal))fail('Expressão aritmética inválida.');
  at+=literal.length;count();return bounded(/[.eE]/.test(literal)?Number(literal):BigInt(literal));
 });
 const power=():Numeric=>{const value=atom();if(token('**')){count();return operate('**',value,factor())}return value};
 const factor=():Numeric=>nested(()=>{if(token('+')){count();return factor()}if(token('-')){count();const value=factor();return bounded(typeof value==='bigint'?-value:-value)}return power()});
 const term=():Numeric=>{let value=factor();while(true){skip();const op=source.startsWith('//',at)?'//':['*','/','%'].includes(source[at])&&!source.startsWith('**',at)?source[at]:'';if(!op)return value;at+=op.length;count();value=operate(op,value,factor());}};
 const expression=():Numeric=>{let value=term();while(true){skip();const op=['+','-'].includes(source[at])?source[at]:'';if(!op)return value;at++;count();value=operate(op,value,term());}};
 const result=expression();skip();if(at!==source.length)fail('Use somente números e operadores aritméticos.');return result;
}

/** JSON.parse alone silently accepts duplicate object keys; this reader rejects them. */
export function parseStrictMobileJson(raw:string):unknown{
 const source=textInput(raw);let at=0,nodes=0,depth=0;
 const skip=()=>{while(/[ \t\r\n]/.test(source[at]||'')&&at<source.length)at++};
 const string=():string=>{
  const start=at++;while(at<source.length){const ch=source[at++];if(ch==='"'){try{return JSON.parse(source.slice(start,at))}catch{fail('JSON inválido.')}}if(ch==='\\')at++;}
  return fail('String JSON não terminada.');
 };
 const value=():unknown=>{
  skip();if(++nodes>10000||++depth>64)fail('JSON complexo demais.');
  try{
   if(source[at]==='"')return string();
   if(source[at]==='{'){
    at++;skip();const result:Record<string,unknown>=Object.create(null),keys=new Set<string>();if(source[at]==='}'){at++;return result;}
    while(true){skip();if(source[at]!=='"')fail('Chave JSON inválida.');const key=string();if(keys.has(key))fail('JSON contém chave duplicada: '+key);keys.add(key);skip();if(source[at++]!==':')fail('JSON inválido.');result[key]=value();skip();const next=source[at++];if(next==='}')return result;if(next!==',')fail('JSON inválido.');}
   }
   if(source[at]==='['){at++;skip();const result:unknown[]=[];if(source[at]===']'){at++;return result;}while(true){result.push(value());skip();const next=source[at++];if(next===']')return result;if(next!==',')fail('JSON inválido.');}}
   for(const [literal,result] of [['true',true],['false',false],['null',null]] as const)if(source.startsWith(literal,at)){at+=literal.length;return result;}
   const match=/^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/.exec(source.slice(at));
   if(match){at+=match[0].length;const number=Number(match[0]);if(!Number.isFinite(number))fail('Número JSON não finito.');return number;}
   return fail('JSON inválido.');
  }finally{depth--;}
 };
 const result=value();skip();if(at!==source.length)fail('JSON inválido.');return result;
}
export async function mobileSha256(raw:string|Uint8Array):Promise<string>{
 const bytes=typeof raw==='string'?new TextEncoder().encode(raw):raw;
 const digest=await crypto.subtle.digest('SHA-256',new Uint8Array(bytes).buffer);
 return Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');
}
const lines=(text:string)=>text?text.split(/\r\n|[\n\r\v\f\x1c-\x1e\x85\u2028\u2029]/).filter((_,i,a)=>i!==a.length-1||a[i]!==''):[];
function scaffold(language:unknown,raw:string):Record<string,unknown>{
 const title=raw.trim(),extensions:Record<string,string>={python:'py',javascript:'js',html:'html',css:'css',json:'json'};
 if(typeof language!=='string'||!Object.hasOwn(extensions,language)||textLength(title)<1||textLength(title)>80)fail('Linguagem ou nome de projeto inválido.');
 const literal=JSON.stringify(title).replace(/\u2028/g,'\\u2028').replace(/\u2029/g,'\\u2029');
 const escaped=title.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#x27;'}[c]!));
 const templates:Record<string,string>={
  python:`"""Script inicial criado a partir de um modelo local."""\n\ndef main():\n    print(${literal})\n\n\nif __name__ == "__main__":\n    main()\n`,
  javascript:`// Módulo inicial. Edite e teste no seu ambiente de desenvolvimento.\nexport function mensagem() {\n  return ${literal};\n}\n`,
  html:`<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n<title>${escaped}</title>\n<style>body{font:18px system-ui;background:#100d20;color:#eee;padding:40px}h1{color:#a78bfa}</style>\n</head>\n<body><h1>${escaped}</h1><p>Seu projeto começa aqui.</p></body>\n</html>\n`,
  css:'/* Estilo inicial */\n:root { color-scheme: dark; }\nbody { margin: 0; padding: 32px; font: 18px system-ui; background: #100d20; color: #eee; }\n',
  json:JSON.stringify({projeto:title,versao:1,itens:[]},null,2)+'\n',
 };
 return {code:templates[language as string],extension:extensions[language as string],origin:'Modelo inicial determinístico; não gerado por um modelo de linguagem.'};
}
export async function runMobileTool(payload:unknown):Promise<Record<string,unknown>>{
 if(!payload||typeof payload!=='object'||Array.isArray(payload))fail('Entrada inválida.');
 const p=payload as Record<string,unknown>,text=textInput(p.text);
 if(p.tool==='calculator')return {result:String(calculateMobile(text))};
 if(p.tool==='sha256')return {result:await mobileSha256(text)};
 if(p.tool==='text_stats')return {result:{characters:textLength(text),words:(text.match(/[\p{L}\p{N}_]+/gu)||[]).length,lines:lines(text).length,utf8_bytes:new TextEncoder().encode(text).length}};
 if(p.tool==='json_validate'){const result=parseStrictMobileJson(text);const kind=result===null?'NoneType':Array.isArray(result)?'list':typeof result==='object'?'dict':typeof result==='string'?'str':typeof result==='boolean'?'bool':Number.isInteger(result)?'int':'float';return {result:`JSON válido. Tipo principal: ${kind}. O texto original foi preservado.`};}
 if(p.tool==='code_scaffold')return scaffold(p.language,text);
 if(p.tool==='python_validate')fail('A validação sintática Python ainda não está disponível no Android. O código pode ser editado e exportado, sem execução.');
 return fail('Ferramenta desconhecida.');
}

export async function compareMobileSources(before:unknown,after:unknown):Promise<Record<string,unknown>>{
 const oldText=textInput(before),newText=textInput(after),oldLines=lines(oldText),newLines=lines(newText);
 if(Math.max(oldLines.length,newLines.length)>2000)fail('Use até 2.000 linhas por versão.');
 let prefix=0,suffix=0;while(prefix<Math.min(oldLines.length,newLines.length)&&oldLines[prefix]===newLines[prefix])prefix++;
 while(suffix<Math.min(oldLines.length,newLines.length)-prefix&&oldLines[oldLines.length-1-suffix]===newLines[newLines.length-1-suffix])suffix++;
 const removed=oldLines.slice(prefix,oldLines.length-suffix),added=newLines.slice(prefix,newLines.length-suffix);
 const changed=oldText!==newText;
 const diff=!changed?'':!removed.length&&!added.length?'Diferença apenas nas quebras de linha.':['--- original','+++ proposta',`@@ -${removed.length?prefix+1:prefix},${removed.length} +${added.length?prefix+1:prefix},${added.length} @@`,...removed.map(l=>'-'+l),...added.map(l=>'+'+l)].join('\n');
 return {diff,changed,before_sha256:await mobileSha256(oldText),after_sha256:await mobileSha256(newText),applied:false,limitations:'Comparação móvel de linhas em um bloco contínuo. Nenhum arquivo foi executado ou alterado.'};
}

export async function inspectMobileFile(payload:unknown):Promise<Record<string,unknown>>{
 if(!payload||typeof payload!=='object'||Array.isArray(payload))fail('Arquivo inválido.');const p=payload as Record<string,unknown>;
 if(typeof p.name!=='string'||!p.name.length||textLength(p.name)>240||p.name.includes('\0'))fail('Nome de arquivo inválido.');
 if(typeof p.base64!=='string'||!p.base64.length||p.base64.length>Math.ceil(MAX_FILE/3)*4||p.base64.length%4!==0)fail('Arquivo codificado inválido ou maior que 4 MB.');
 const encoded=p.base64 as string,padding=encoded.endsWith('==')?2:encoded.endsWith('=')?1:0;
 if(/[^A-Za-z0-9+/]/.test(encoded.slice(0,encoded.length-padding)))fail('Arquivo codificado inválido.');
 let data:Uint8Array;try{const binary=atob(p.base64 as string);data=Uint8Array.from(binary,c=>c.charCodeAt(0));}catch{return fail('Arquivo codificado inválido.');}
 if(!data.length||data.length>MAX_FILE)fail('Arquivo vazio ou maior que 4 MB.');
 const view=new DataView(data.buffer),counts=new Uint32Array(256),strings:string[]=[];let entropy=0,run='';
 for(const byte of data){counts[byte]++;if(strings.length<100){if(byte>=32&&byte<=126){run+=String.fromCharCode(byte);if(run.length===160){strings.push(run);run='';}}else{if(run.length>=6)strings.push(run);run='';}}}
 if(strings.length<100&&run.length>=6)strings.push(run);
 for(const count of counts)if(count){const fraction=count/data.length;entropy-=fraction*Math.log2(fraction);}
 const need=(offset:number,size:number)=>{if(!Number.isSafeInteger(offset)||offset<0||offset+size>data.length)fail('Cabeçalho truncado ou inválido.');};
 const u16=(at:number,little=true)=>{need(at,2);return view.getUint16(at,little)},u32=(at:number,little=true)=>{need(at,4);return view.getUint32(at,little)};
 const ascii=(start:number,length:number)=>{need(start,length);return Array.from(data.subarray(start,start+length),b=>b<128?String.fromCharCode(b):'\\x'+b.toString(16).padStart(2,'0')).join('')};
 let format='Desconhecido',details:Record<string,unknown>={};const warnings:string[]=[];
 if(data[0]===0x4d&&data[1]===0x5a){
  const pe=u32(60);need(pe,24);if(pe<64||u32(pe)!==0x00004550)fail('Assinatura PE ausente ou inválida.');
  const machine=u16(pe+4),count=u16(pe+6),optionalSize=u16(pe+20),flags=u16(pe+22),optional=pe+24,table=optional+optionalSize;
  if(count<1||count>96)fail('Quantidade de seções PE inválida.');if(optionalSize&&(optionalSize<20||table>data.length))fail('Cabeçalho opcional PE inválido.');need(table,count*40);
  const sections=[];for(let i=0;i<count;i++){const at=table+i*40,size=u32(at+16),offset=u32(at+20);if(size&&(offset===0||offset+size>data.length))fail('Seção PE truncada.');sections.push({name:ascii(at,8).split('\0')[0],virtual_size:u32(at+8),rva:u32(at+12),size,file_offset:offset});}
  format='PE';details={architecture:({34404:'x64',332:'x86',43620:'ARM64'} as Record<number,string>)[machine]||'0x'+machine.toString(16),kind:flags&0x2000?'DLL':'PE/COFF',optional_magic:'0x'+(optionalSize?u16(optional):0).toString(16),sections};
  if(optionalSize)details.entry_rva=u32(optional+16);warnings.push('No Android, a inspeção PE limita-se aos cabeçalhos e seções; não resolve importações.');
 }else if(data.length>=4&&data[0]===0x7f&&ascii(1,3)==='ELF'){
  need(0,16);if(![1,2].includes(data[4])||![1,2].includes(data[5]))fail('Identificação ELF inválida.');const bits=data[4]===1?32:64,little=data[5]===1;need(0,bits===32?52:64);const machine=u16(18,little);
  format='ELF';details={bits,endianness:little?'little':'big',architecture:({3:'x86',62:'x64',40:'ARM',183:'ARM64'} as Record<number,string>)[machine]||String(machine),type:u16(16,little),entry_address:bits===32?u32(24,little):'0x'+view.getBigUint64(24,little).toString(16)};
 }else if(data.length>=4&&[0x04034b50,0x06054b50].includes(u32(0))){
  let end=-1;for(let at=data.length-22;at>=Math.max(0,data.length-65557);at--)if(u32(at)===0x06054b50&&at+22+u16(at+20)===data.length){end=at;break;}
  if(end<0)fail('Diretório ZIP ausente ou truncado.');const entries=u16(end+10),directorySize=u32(end+12),directory=u32(end+16);
  if(u16(end+4)||u16(end+6)||u16(end+8)!==entries||entries===65535||directory===0xffffffff||directorySize===0xffffffff)fail('ZIP multidisco e ZIP64 não são suportados na inspeção móvel.');
  if(entries>2000||directory+directorySize>end)fail('Diretório ZIP inválido ou grande demais.');let at=directory,total=0,encrypted=false;const names:string[]=[];
  for(let i=0;i<entries;i++){
   need(at,46);if(u32(at)!==0x02014b50)fail('Entrada ZIP inválida.');const flags=u16(at+8),length=u16(at+28),extra=u16(at+30),comment=u16(at+32);need(at+46,length+extra+comment);
   const nameBytes=data.subarray(at+46,at+46+length);let name:string;try{name=flags&0x800?new TextDecoder('utf-8',{fatal:true}).decode(nameBytes):ascii(at+46,length)}catch{return fail('Nome ZIP UTF-8 inválido.');}
   if(textLength(name)>300)fail('Nome interno excessivamente longo.');total+=u32(at+24);if(total>256*1024*1024)fail('Arquivo compactado excede os limites de inspeção.');names.push(name);encrypted=encrypted||!!(flags&1);at+=46+length+extra+comment;
  }
  if(at!==directory+directorySize)fail('Tamanho do diretório ZIP não confere.');format=names.includes('AndroidManifest.xml')?'APK/ZIP':'ZIP';details={entry_count:entries,uncompressed_bytes:total,entries:names.slice(0,100),extracted:false,name_encoding:'UTF-8 quando indicado; bytes não ASCII escapados nos demais nomes'};
  if(names.some(n=>n.startsWith('/')||n.startsWith('\\')||n.replace(/\\/g,'/').split('/').includes('..')))warnings.push('Há caminhos internos suspeitos; nenhum arquivo foi extraído.');if(encrypted)warnings.push('Há entradas criptografadas; conteúdo não foi aberto.');
 }
 return {name:(p.name as string).replace(/\\/g,'/').split('/').pop(),size:data.length,sha256:await mobileSha256(data),entropy_bits_per_byte:Math.round(entropy*1000)/1000,format,details,warnings,strings,executed:false,limitations:'Inspeção estática inicial no telefone. Não executa nem extrai arquivos, não descompila e não comprova segurança, comportamento, autoria ou licença.'};
}
