"""Transactional local Knowledge Vault; no network or model inference."""
from __future__ import annotations
from datetime import datetime, timezone
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlsplit
import uuid

MAX_ITEMS = 500
MAX_CONTENT = 20000
KINDS = {'document', 'note', 'source'}


def data_directory():
    override = os.environ.get('ELYSIA_DATA_DIR')
    if override:
        return Path(override)
    base = Path(os.environ.get('LOCALAPPDATA', Path.home() / '.local/share'))
    return base / 'Elysia'


def validate_item(value, require_id=False):
    if not isinstance(value, dict):
        raise ValueError('Registro inválido.')
    result = {}
    for key, limit in [('title', 160), ('content', MAX_CONTENT), ('url', 2048)]:
        text = value.get(key, '')
        if not isinstance(text, str) or len(text) > limit or '\x00' in text:
            raise ValueError(f'Campo {key} inválido ou longo demais.')
        result[key] = text.strip()
    if not result['title'] or not result['content']:
        raise ValueError('Preencha título e conteúdo.')
    result['kind'] = value.get('kind', 'note')
    if not isinstance(result['kind'], str) or result['kind'] not in KINDS:
        raise ValueError('Tipo de registro inválido.')
    if result['url']:
        parts = urlsplit(result['url'])
        if parts.scheme not in ('http','https') or not parts.netloc or parts.username or parts.password:
            raise ValueError('Use uma URL HTTP ou HTTPS sem credenciais.')
    identifier = value.get('id')
    if require_id or identifier is not None:
        try:
            if str(uuid.UUID(identifier)) != identifier:
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise ValueError('Identificador inválido.') from None
        result['id'] = identifier
    return result


def digest_items(items):
    return hashlib.sha256(json.dumps(items, sort_keys=True, ensure_ascii=False,
                                    separators=(',',':')).encode('utf-8')).hexdigest()


class Vault:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else data_directory() / 'vault.sqlite3'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS entries (id TEXT PRIMARY KEY, kind TEXT NOT NULL, '
                       'title TEXT NOT NULL, content TEXT NOT NULL, url TEXT NOT NULL, updated TEXT NOT NULL)')
            db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(id UNINDEXED, title, content, tokenize='unicode61 remove_diacritics 2')")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def list(self, query='', kind=''):
        if not isinstance(query, str) or len(query) > 300 or kind and kind not in KINDS:
            raise ValueError('Busca inválida.')
        with self.connect() as db:
            if query.strip():
                tokens = re.findall(r'\w+', query, flags=re.UNICODE)[:10]
                if not tokens:
                    return []
                match = ' AND '.join('"' + t + '"*' for t in tokens)
                records = db.execute('SELECT e.* FROM entries e JOIN search_index s ON e.id=s.id '
                    'WHERE search_index MATCH ? AND (?="" OR e.kind=?) ORDER BY rank, e.id LIMIT 500',
                    (match,kind,kind)).fetchall()
            else:
                records = db.execute('SELECT * FROM entries WHERE (?="" OR kind=?) '
                    'ORDER BY updated DESC, id LIMIT 500',(kind,kind)).fetchall()
        return [dict(r) for r in records]

    def save(self, value):
        item = validate_item(value)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if 'id' in item:
                if db.execute('SELECT id FROM entries WHERE id=?',(item['id'],)).fetchone() is None:
                    raise ValueError('Registro não encontrado.')
            else:
                if db.execute('SELECT COUNT(*) FROM entries').fetchone()[0] >= MAX_ITEMS:
                    raise ValueError('Limite de 500 registros atingido. Exporte um backup.')
                item['id'] = str(uuid.uuid4())
            updated = datetime.now(timezone.utc).isoformat()
            db.execute('INSERT OR REPLACE INTO entries VALUES (?,?,?,?,?,?)',
                       (item['id'],item['kind'],item['title'],item['content'],item['url'],updated))
            db.execute('DELETE FROM search_index WHERE id=?',(item['id'],))
            db.execute('INSERT INTO search_index(id,title,content) VALUES (?,?,?)',
                       (item['id'],item['title'],item['content']))
        return {**item,'updated':updated}

    def delete(self, identifier):
        validate_item({'id':identifier,'title':'x','content':'x'}, require_id=True)
        with self.connect() as db:
            db.execute('DELETE FROM search_index WHERE id=?',(identifier,))
            db.execute('DELETE FROM entries WHERE id=?',(identifier,))

    def backup(self):
        with self.connect() as db:
            items = [dict(r) for r in db.execute('SELECT * FROM entries ORDER BY id')]
        return {'format':'elysia-vault-v1','items':items,'sha256':digest_items(items)}

    def restore(self, payload):
        if not isinstance(payload,dict) or payload.get('format') != 'elysia-vault-v1':
            raise ValueError('Formato de backup inválido.')
        items = payload.get('items')
        if not isinstance(items,list) or len(items) > MAX_ITEMS or payload.get('sha256') != digest_items(items):
            raise ValueError('Backup inválido, alterado ou grande demais.')
        validated = [validate_item(item,require_id=True) for item in items]
        if len({i['id'] for i in validated}) != len(validated):
            raise ValueError('Backup contém identificadores duplicados.')
        added = 0
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            count = db.execute('SELECT COUNT(*) FROM entries').fetchone()[0]
            for item in validated:
                old = db.execute('SELECT * FROM entries WHERE id=?',(item['id'],)).fetchone()
                if old:
                    if any(old[k] != item[k] for k in ('title','content','kind','url')):
                        raise ValueError('Há registros com o mesmo identificador e conteúdo diferente. Nada foi importado.')
                    continue
                if count + added >= MAX_ITEMS:
                    raise ValueError('A importação ultrapassaria 500 registros. Nada foi importado.')
                db.execute('INSERT INTO entries VALUES (?,?,?,?,?,?)',(item['id'],item['kind'],item['title'],
                    item['content'],item['url'],datetime.now(timezone.utc).isoformat()))
                db.execute('INSERT INTO search_index(id,title,content) VALUES (?,?,?)',
                           (item['id'],item['title'],item['content']))
                added += 1
        return added
