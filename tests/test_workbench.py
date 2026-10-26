import base64
import io
import json
import struct
import zipfile
import pytest
from actions.workbench import inspect_file, analyze_python, compare_sources
from actions.capabilities import catalog


def payload(data,name='sample.bin'):
    return {'name':name,'base64':base64.b64encode(data).decode()}


def pe_fixture():
    data=bytearray(1024);data[:2]=b'MZ';struct.pack_into('<I',data,60,128);data[128:132]=b'PE\0\0'
    struct.pack_into('<HHIIIHH',data,132,0x8664,1,0,0,0,240,0x2000)
    struct.pack_into('<H',data,152,0x20b);struct.pack_into('<I',data,168,0x1000)
    struct.pack_into('<II',data,152+112+8,0x1000,40)
    struct.pack_into('<8sIIII',data,392,b'.idata\0\0',512,0x1000,512,512)
    struct.pack_into('<IIIII',data,512,0,0,0,0x1040,0x1060)
    data[576:589]=b'KERNEL32.dll\0'
    return data


def test_pe_metadata_and_imports_are_read_without_loading_binary():
    report=inspect_file(payload(pe_fixture(),'sample.dll'))
    assert report['format']=='PE' and report['executed'] is False
    assert report['details']['architecture']=='x64'
    assert report['details']['imported_libraries']==['KERNEL32.dll']
    assert len(report['sha256'])==64
    for data in [b'MZ',b'MZ'+bytes(58)+b'\xff'*4,pe_fixture()[:700]]:
        with pytest.raises(ValueError):inspect_file(payload(data))


def test_elf_endianness_archive_paths_and_no_extraction(tmp_path):
    data=bytearray(64);data[:6]=b'\x7fELF\x02\x02';struct.pack_into('>HH',data,16,2,183)
    assert inspect_file(payload(data))['details']['architecture']=='ARM64'
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w') as archive:
        archive.writestr('AndroidManifest.xml','fake test fixture, not an app')
        archive.writestr('../escape.txt','not extracted')
    report=inspect_file(payload(output.getvalue(),'fixture.apk'))
    assert report['format']=='APK/ZIP' and report['warnings'] and report['details']['extracted'] is False
    assert not (tmp_path/'escape.txt').exists()
    bomb=bytearray(output.getvalue());at=bomb.find(b'PK\x01\x02');struct.pack_into('<I',bomb,at+24,300*1024*1024)
    with pytest.raises(ValueError):inspect_file(payload(bomb))


def test_bounds_and_bad_types():
    for value in [{},{'name':'x','base64':'invalid'},{'name':'x','base64':''},{'name':{},'base64':'YQ=='},payload(bytes(4*1024*1024+1))]:
        with pytest.raises(ValueError):inspect_file(value)
    report=inspect_file(payload(b'not a known file but printable'))
    assert report['format']=='Desconhecido'


def test_python_provenance_no_execution_and_diff(tmp_path):
    target=tmp_path/'must-not-exist'
    code=f"from pathlib import Path\nPath({str(target)!r}).write_text('never')\nclass C:\n def method(self):\n  return max(1,2)\n"
    result=analyze_python(code)
    assert not target.exists() and not result['executed']
    assert any(item['name']=='C.method' and item['line']==4 for item in result['definitions'])
    assert result['imports'][0]['module']=='pathlib'
    assert any(c['target']=='max' and c['from']=='C.method' and c['line']==5 for c in result['calls'])
    assert compare_sources('a=1','a=2')['diff'].endswith('+a=2')
    assert compare_sources('a=1','a=1\n')['changed'] and compare_sources('a=1','a=1\n')['diff']
    with pytest.raises(ValueError):analyze_python('def bad(')
    with pytest.raises(ValueError):compare_sources('x',None)


def test_catalog_never_claims_planned_cores_are_available():
    items={item['id']:item for item in catalog()['capabilities']}
    assert items['image']['status']=='parcial'
    assert items['voice']['status']=='pausada'
    assert items['neural']['status']=='experimental'
    assert 'não' in items['workbench']['limitations'].lower() or 'Sem Ghidra' in items['workbench']['limitations']
    json.dumps(catalog(),allow_nan=False)
