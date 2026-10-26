"""Bounded, read-only first-look analysis. Never loads or executes selected files."""
import ast
import base64
import binascii
from collections import Counter
import difflib
import hashlib
import io
import math
import re
import struct
import zipfile

MAX_FILE=4*1024*1024


def inspect_file(payload):
    if not isinstance(payload,dict) or not isinstance(payload.get('name'),str) or not 1<=len(payload['name'])<=240 or '\x00' in payload['name']:
        raise ValueError('Nome de arquivo inválido.')
    encoded=payload.get('base64')
    if not isinstance(encoded,str) or len(encoded)>((MAX_FILE+2)//3)*4:
        raise ValueError('Escolha um arquivo de até 4 MB.')
    try:data=base64.b64decode(encoded,validate=True)
    except (binascii.Error,ValueError):raise ValueError('Arquivo codificado inválido.') from None
    if not data or len(data)>MAX_FILE:raise ValueError('Arquivo vazio ou maior que 4 MB.')
    counts=Counter(data)
    report={'name':payload['name'].replace('\\','/').split('/')[-1],'size':len(data),'sha256':hashlib.sha256(data).hexdigest(),
            'entropy_bits_per_byte':round(-sum(n/len(data)*math.log2(n/len(data)) for n in counts.values()),3),
            'format':'Desconhecido','details':{},'warnings':[],
            'strings':[m.group().decode('ascii') for _,m in zip(range(100),re.finditer(rb'[\x20-\x7e]{6,160}',data))],
            'executed':False,'limitations':'Inspeção estática inicial. Não comprova segurança, comportamento, autoria ou licença; não descompila.'}
    def unpack(fmt,offset):
        if offset<0 or offset+struct.calcsize(fmt)>len(data):raise ValueError('Cabeçalho truncado ou inválido.')
        return struct.unpack_from(fmt,data,offset)
    if data.startswith(b'MZ'):
        pe=unpack('<I',60)[0]
        if pe<64 or data[pe:pe+4]!=b'PE\0\0':raise ValueError('Assinatura PE ausente ou inválida.')
        machine,sections,_,_,_,optional_size,flags=unpack('<HHIIIHH',pe+4)
        if not 1<=sections<=96:raise ValueError('Quantidade de seções PE inválida.')
        optional=pe+24;table=optional+optional_size;items=[]
        if optional_size and (optional_size<20 or table>len(data)):raise ValueError('Cabeçalho opcional PE inválido.')
        magic=unpack('<H',optional)[0] if optional_size else 0
        for i in range(sections):
            offset=table+i*40
            name,virtual_size,rva,raw_size,raw_offset=unpack('<8sIIII',offset)
            unpack('<I',offset+36)
            if raw_size and (raw_offset==0 or raw_offset+raw_size>len(data)):raise ValueError('Seção PE truncada.')
            items.append({'name':name.split(b'\0')[0].decode('ascii','replace'),'rva':rva,'virtual_size':virtual_size,'file_offset':raw_offset,'size':raw_size})
        report['format']='PE';report['details']={'architecture':{0x8664:'x64',0x14c:'x86',0xaa64:'ARM64'}.get(machine,hex(machine)),
            'kind':'DLL' if flags&0x2000 else 'PE/COFF','optional_magic':hex(magic),'sections':items}
        if optional_size:report['details']['entry_rva']=unpack('<I',optional+16)[0]
        # Resolve import names only inside bytes actually present in a section.
        def file_offset(rva):
            for item in items:
                delta=rva-item['rva']
                if 0<=delta<item['size']:return item['file_offset']+delta
            raise ValueError('RVA de importação fora das seções presentes.')
        directory=112 if magic==0x20b else 96 if magic==0x10b else None
        if directory is not None and optional_size>=directory+16:
            imports_rva,imports_size=unpack('<II',optional+directory+8)
            imports=[]
            if imports_rva and imports_size:
                try:
                    offset=file_offset(imports_rva)
                    for i in range(min(imports_size//20,128)):
                        descriptor=unpack('<IIIII',offset+i*20)
                        if not any(descriptor):break
                        at=file_offset(descriptor[3]);end=data.find(b'\0',at,min(len(data),at+256))
                        if end<0:raise ValueError('Nome de biblioteca sem terminador.')
                        imports.append(data[at:end].decode('ascii','replace'))
                except ValueError:report['warnings'].append('Tabela de importações incompleta ou não resolvida.')
            report['details']['imported_libraries']=imports
    elif data.startswith(b'\x7fELF'):
        if len(data)<16 or data[4] not in (1,2) or data[5] not in (1,2):raise ValueError('Identificação ELF inválida.')
        bits=32 if data[4]==1 else 64;order='<' if data[5]==1 else '>'
        unpack(order+('I' if bits==32 else 'Q'),48 if bits==32 else 56)
        kind,machine=unpack(order+'HH',16)
        report['format']='ELF';report['details']={'bits':bits,'endianness':'little' if order=='<' else 'big',
            'architecture':{3:'x86',62:'x64',40:'ARM',183:'ARM64'}.get(machine,str(machine)),
            'type':kind,'entry_address':unpack(order+('I' if bits==32 else 'Q'),24)[0]}
    elif data[:4] in (b'PK\x03\x04',b'PK\x05\x06'):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                entries=archive.infolist()
                if len(entries)>2000 or sum(e.file_size for e in entries)>256*1024*1024:raise ValueError('Arquivo compactado excede os limites de inspeção.')
                paths=[e.filename for e in entries]
                if any(len(p)>300 for p in paths):raise ValueError('Nome interno excessivamente longo.')
                report['format']='APK/ZIP' if 'AndroidManifest.xml' in paths else 'ZIP'
                report['details']={'entry_count':len(entries),'uncompressed_bytes':sum(e.file_size for e in entries),'entries':paths[:100],'extracted':False}
                if any(p.startswith(('/','\\')) or '..' in p.replace('\\','/').split('/') for p in paths):report['warnings'].append('Há caminhos internos suspeitos; nenhum arquivo foi extraído.')
                if any(e.flag_bits&1 for e in entries):report['warnings'].append('Há entradas criptografadas; conteúdo não foi aberto.')
        except (zipfile.BadZipFile,NotImplementedError):raise ValueError('Arquivo ZIP inválido.') from None
    return report


def analyze_python(text):
    if not isinstance(text,str) or len(text)>20000:raise ValueError('Use até 20.000 caracteres de Python.')
    try:tree=ast.parse(text)
    except (SyntaxError,RecursionError,ValueError) as exc:raise ValueError('Python inválido: '+str(exc)) from None
    if sum(1 for _ in ast.walk(tree))>5000:raise ValueError('Estrutura muito grande.')
    definitions=[];imports=[];calls=[];scope=[]
    class Visitor(ast.NodeVisitor):
        def definition(self,node,kind):
            name='.'.join(scope+[node.name]);definitions.append({'name':name,'kind':kind,'line':node.lineno,'end_line':node.end_lineno})
            scope.append(node.name);self.generic_visit(node);scope.pop()
        def visit_FunctionDef(self,node):self.definition(node,'function')
        def visit_AsyncFunctionDef(self,node):self.definition(node,'async function')
        def visit_ClassDef(self,node):self.definition(node,'class')
        def visit_Import(self,node):
            for alias in node.names:imports.append({'module':alias.name,'name':None,'alias':alias.asname,'line':node.lineno,'scope':'.'.join(scope) or '<module>'})
        def visit_ImportFrom(self,node):
            for alias in node.names:imports.append({'module':'.'*node.level+(node.module or ''),'name':alias.name,'alias':alias.asname,'line':node.lineno,'scope':'.'.join(scope) or '<module>'})
        def visit_Call(self,node):
            parts=[];target=node.func
            while isinstance(target,ast.Attribute):parts.insert(0,target.attr);target=target.value
            if isinstance(target,ast.Name):
                parts.insert(0,target.id);calls.append({'from':'.'.join(scope) or '<module>','target':'.'.join(parts),'line':node.lineno,'relation':'syntactic-call-name'})
            self.generic_visit(node)
    try:Visitor().visit(tree)
    except RecursionError:raise ValueError('Estrutura aninhada além do limite de análise.') from None
    return {'sha256':hashlib.sha256(text.encode()).hexdigest(),'definitions':definitions[:200],'imports':imports[:200],'calls':calls[:300],
            'truncated':len(definitions)>200 or len(imports)>200 or len(calls)>300,'executed':False,
            'limitations':'Relações extraídas da sintaxe de um arquivo. Nomes de chamadas não comprovam qual função será executada; não resolve outros arquivos nem infere dependências.'}


def compare_sources(before,after):
    if not isinstance(before,str) or not isinstance(after,str) or max(len(before),len(after))>20000:raise ValueError('Cada versão deve ter até 20.000 caracteres.')
    if max(len(before.splitlines()),len(after.splitlines()))>2000:raise ValueError('Use até 2.000 linhas por versão.')
    lines=list(difflib.unified_diff(before.splitlines(),after.splitlines(),fromfile='original',tofile='proposta',lineterm=''))
    return {'diff':('\n'.join(lines) or ('Diferença apenas na quebra de linha final.' if before!=after else '')),'changed':before!=after,'before_sha256':hashlib.sha256(before.encode()).hexdigest(),
            'after_sha256':hashlib.sha256(after.encode()).hexdigest(),'applied':False}
