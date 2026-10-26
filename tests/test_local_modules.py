import hashlib
import json
import uuid

import pytest

from actions.local_tools import calculate, run_tool
from memory.vault import Vault, digest_items


def test_vault_survives_reopen_and_indexes_accents_and_updates(tmp_path):
    path=tmp_path/'private.sqlite3'
    vault=Vault(path)
    item=vault.save({'title':'São Paulo','content':'Café e informações úteis.','kind':'document'})
    assert Vault(path).list('cafe')[0]['id']==item['id']
    assert vault.list('sao')[0]['id']==item['id']
    assert not vault.list('cafe','note')
    vault.save({**item,'content':'Agora somente chocolate.'})
    assert not vault.list('cafe')
    assert vault.list('chocol')[0]['content']=='Agora somente chocolate.'
    vault.delete(item['id'])
    assert not Vault(path).list('chocolate')


def test_private_backup_is_portable_verified_and_idempotent(tmp_path):
    first=Vault(tmp_path/'first.sqlite3')
    first.save({'title':'Fonte','content':'Uma referência.','kind':'source','url':'https://example.org/page'})
    backup=json.loads(json.dumps(first.backup(),ensure_ascii=False))
    second=Vault(tmp_path/'second.sqlite3')
    assert second.restore(backup)==1
    assert second.restore(backup)==0
    assert second.list()[0]['content']=='Uma referência.'
    backup['items'][0]['content']='alterado'
    with pytest.raises(ValueError,match='alterado'):
        second.restore(backup)
    assert second.list()[0]['content']=='Uma referência.'


def test_restore_conflict_rolls_back_earlier_additions(tmp_path):
    vault=Vault(tmp_path/'private.sqlite3')
    existing=vault.save({'title':'Manter','content':'Original'})
    added={'id':str(uuid.uuid4()),'kind':'note','title':'Outra','content':'Texto','url':''}
    conflicting={**existing,'content':'Conflito'}
    items=[added,conflicting]
    with pytest.raises(ValueError,match='Nada foi importado'):
        vault.restore({'format':'elysia-vault-v1','items':items,'sha256':digest_items(items)})
    assert len(vault.list())==1 and vault.list()[0]['content']=='Original'


@pytest.mark.parametrize('fields',[
    {'title':'','content':'x'}, {'title':'x','content':'y'*20001},
    {'title':'x','content':'y','url':'javascript:alert(1)'},
    {'title':'x','content':'y','url':'https://name:secret@example.org'},
    {'title':'x','content':'y','kind':[]}, {'title':'x','content':'y','id':'../other'},
])
def test_vault_rejects_invalid_records_without_saving(tmp_path,fields):
    vault=Vault(tmp_path/'private.sqlite3')
    with pytest.raises(ValueError):vault.save(fields)
    assert not vault.list()


def test_search_input_is_not_executed_as_sql_or_fts_operators(tmp_path):
    vault=Vault(tmp_path/'private.sqlite3')
    vault.save({'title':'Nota','content':'Um café.'})
    assert not vault.list('" OR 1=1; DROP TABLE entries; --')
    assert len(vault.list())==1


def test_calculator_and_explicit_local_tools():
    assert calculate('(6 * 3) + 2**3 / 4')==20
    assert run_tool({'tool':'calculator','text':'2 + 3'})=={'result':'5'}
    assert run_tool({'tool':'sha256','text':'Olá'})['result']==hashlib.sha256('Olá'.encode()).hexdigest()
    assert run_tool({'tool':'text_stats','text':'Olá mundo\nCafé'})['result']=={
        'characters':14,'words':3,'lines':2,'utf8_bytes':16}
    assert 'JSON válido' in run_tool({'tool':'json_validate','text':'{"olá":[1,true,null]}'})['result']


@pytest.mark.parametrize('expression',[
    '__import__("os").system("echo fail")','open("private")','(lambda: 4)()',
    'True + 1','[1,2]','10**1000000','1/0','(-2)**0.5','1e200','2 << 300',
])
def test_calculator_rejects_execution_and_unbounded_computation(expression):
    with pytest.raises(ValueError):calculate(expression)


@pytest.mark.parametrize('text',['{"x":1,"x":2}','NaN','Infinity','{"x":1e999}','not json'])
def test_json_validation_rejects_invalid_values_and_duplicate_keys(text):
    with pytest.raises(ValueError):run_tool({'tool':'json_validate','text':text})
