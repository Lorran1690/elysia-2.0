"""Pinned Portuguese encyclopedia sample for own-model language pretraining."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import unicodedata
import urllib.request
from learning.aira_corpus import ROOT, file_hash, PII

REVISION = 'b04c8d1ceb2f5cd4588862100d08de323dccfbaa'
REPOSITORY = 'wikimedia/wikipedia'
LOCK = ROOT/'data/source-locks/wikipedia-pt-20231101.json'
DEFAULT_CACHE = Path('/workspace/elysia-source-cache/wikipedia-pt-20231101')
DEST = ROOT/'data/foundation-pt-v1'
LICENSE_URL = 'https://raw.githubusercontent.com/spdx/license-list-data/31ba1a50e5397e00a304dbadc76531740e89ee48/text/CC-BY-SA-3.0.txt'
LICENSE_SHA = '3f941b3b89cf7b8370ceb83cc76d2120d471b58735d8ca60238a751a48d7f72f'
CARD_SHA = 'a0f2055ac612f924721e9981fa2a49a18adec1c67cc8026f6c97d12f17211b21'


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def fetch(cache):
    cache.mkdir(parents=True, exist_ok=True)
    items=json.loads(LOCK.read_text())
    for info in items:
        p=cache/Path(info['path']).name
        if not p.exists():
            temporary=p.with_suffix('.download')
            try:
                with urllib.request.urlopen(f'https://huggingface.co/datasets/{REPOSITORY}/resolve/{REVISION}/{info["path"]}',timeout=60) as response,temporary.open('wb') as target:
                    count=0
                    while block:=response.read(1024*1024):
                        count+=len(block)
                        if count>info['size']: raise ValueError('Source exceeds pinned size')
                        target.write(block)
                if temporary.stat().st_size!=info['size'] or file_hash(temporary)!=info['lfs']['oid']:
                    raise ValueError('Downloaded source differs from pinned source')
                temporary.replace(p)
            finally:
                temporary.unlink(missing_ok=True)
        if p.stat().st_size!=info['size'] or file_hash(p)!=info['lfs']['oid']:
            raise ValueError('Cached source mismatch')
    card=cache/'README.md'
    if not card.exists():
        card.write_bytes(urllib.request.urlopen(f'https://huggingface.co/datasets/{REPOSITORY}/resolve/{REVISION}/README.md',timeout=30).read(500000))
    if file_hash(card)!=CARD_SHA: raise ValueError('Pinned card changed')
    license_file=cache/'CC-BY-SA-3.0.txt'
    if not license_file.exists():
        license_file.write_bytes(urllib.request.urlopen(LICENSE_URL,timeout=30).read(100000))
    if file_hash(license_file)!=LICENSE_SHA: raise ValueError('License text changed')
    evidence={'license_text_mirror':LICENSE_URL,'sha256':LICENSE_SHA,'upstream_license_declaration':'Pinned wikimedia/wikipedia README.md','original_license_url':'https://creativecommons.org/licenses/by-sa/3.0/','wikimedia_terms_url':'https://dumps.wikimedia.org/legal.html','direct_notice_download':'Original CC text URL and Wikimedia legal URL returned HTTP 403 during acquisition; full CC text is archived from the pinned SPDX mirror.'}
    (cache/'license-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    # Pinned data card states the licenses. Full CC license is kept in repository.
    if b'Creative Commons Attribution-Share-Alike 3.0' not in card.read_bytes():
        raise ValueError('Source license declaration is missing')


def eligible(row):
    text=unicodedata.normalize('NFC',row['text']).strip()
    if not 400<=len(text)<=30000: return None,'length'
    if not row['url'].startswith('https://pt.wikipedia.org/wiki/'): return None,'non_portuguese_url'
    if 'desambiguação' in row['title'].casefold(): return None,'disambiguation'
    if PII.search(text): return None,'identifier_pattern'
    return text,None


def prepare(cache,output):
    import pyarrow.parquet as pq
    if output.exists(): raise ValueError('Published corpus exists; choose a new directory')
    items=json.loads(LOCK.read_text())
    for info in items:
        p=cache/Path(info['path']).name
        if p.stat().st_size!=info['size'] or file_hash(p)!=info['lfs']['oid']: raise ValueError('Pinned parquet mismatch')
    card=cache/'README.md'
    if file_hash(card)!=CARD_SHA or file_hash(cache/'CC-BY-SA-3.0.txt')!=LICENSE_SHA: raise ValueError('Pinned license evidence mismatch')
    # Sample article IDs from ALL six shards, not an ordered prefix of Wikipedia.
    counts=Counter();rows=[];seen=set()
    for info in items:
        for batch in pq.ParquetFile(cache/Path(info['path']).name).iter_batches(batch_size=128):
            for row in batch.to_pylist():
                counts['source_rows_scanned']+=1
                if int(digest('pt:'+row['id'])[:16],16)%100: continue
                counts['sampled_by_id']+=1
                text,reason=eligible(row)
                if reason: counts['excluded_'+reason]+=1;continue
                key=digest(' '.join(text.casefold().split()))
                if key in seen:counts['excluded_exact_duplicate']+=1;continue
                seen.add(key);bucket=int(key[:16],16)%100
                split='train' if bucket<90 else 'validation' if bucket<95 else 'test'
                rows.append({'id':'wikipedia-pt-'+row['id'],'group_id':key,'family':'encyclopedia',
                             'title':row['title'],'text':text,'sha256':digest(text),'split':split,
                             'source':REPOSITORY,'revision':REVISION,'dump':'20231101.pt',
                             'source_url':row['url'],'attribution':'Contributors to the linked Portuguese Wikipedia article; revision history at history_url',
                             'history_url':row['url']+'?action=history','license':'CC-BY-SA-3.0',
                             'license_url':'https://creativecommons.org/licenses/by-sa/3.0/',
                             'modifications':'Upstream cleaned wikitext; local NFC normalization and trimming. No factual correction.',
                             'synthetic':'not established per article; encyclopedia source, not generated as this project curriculum',
                             'independently_fact_checked':False})
        print(json.dumps({'scanned_shard':info['path'],'sample_retained_so_far':len(rows)}),flush=True)
    output.mkdir(parents=True)
    sources=output/'sources';sources.mkdir()
    shutil.copyfile(card,sources/'UPSTREAM-CARD.md')
    for name in ['CC-BY-SA-3.0.txt','license-evidence.json']:
        if not (cache/name).exists():raise ValueError('Missing full source license/notices')
        shutil.copyfile(cache/name,sources/name)
    partitions={}
    for split in ['train','validation','test']:
        target=output/f'{split}.jsonl'
        selected=sorted((r for r in rows if r['split']==split),key=lambda r:r['id'])
        with target.open('w',encoding='utf-8',newline='\n') as f:
            for row in selected:f.write(json.dumps(row,ensure_ascii=False)+'\n')
        if target.stat().st_size>=90_000_000:raise ValueError('Split exceeds conservative GitHub file budget; use shards')
        partitions[split]={'documents':len(selected),'characters':sum(len(r['text']) for r in selected),'bytes':target.stat().st_size,'sha256':file_hash(target)}
    manifest={'source':REPOSITORY,'revision':REVISION,'source_lock_sha256':file_hash(LOCK),'source_files':items,'sample':'1% of SHA256(pt:article_id) buckets across all six shards, before eligibility filters','counts':dict(counts),'partitions':partitions,'grouping':'Exact normalized full text; no group crosses splits','license':'CC-BY-SA-3.0 per upstream card; attribution and history URL retained per article','source_notices':{str(p.relative_to(output)):file_hash(p) for p in sources.iterdir()},'neural_weights_updated':False,'limitations':['Snapshot from November 2023, not current facts.','No independent factual, topic balance, bias or human-authorship audit.','Lexical identifier filters are not complete privacy review.','Near duplicates and shared paragraphs may remain between articles.','Encyclopedic text is not conversational behavior or an instruction corpus.']}
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'counts':dict(counts),'partitions':partitions},ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,default=DEFAULT_CACHE);p.add_argument('--output',type=Path,default=DEST);p.add_argument('--fetch',action='store_true');a=p.parse_args()
    if a.fetch:fetch(a.cache)
    prepare(a.cache,a.output)
