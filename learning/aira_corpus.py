"""Pinned, explicitly synthetic Portuguese conversations; no model weights fetched."""
from __future__ import annotations
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
import unicodedata
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REVISION = '1ca52371453cc9e52b650ba4314f2ca0a69f58ba'
REPOSITORY = 'nicholasKluge/instruct-aira-dataset-v3'
FILES = {
 'README.md': ('README.md', 5996, '089f35c894b6c21f7af72d213602ecb215379ffcace4b0fec3a1975dc1ca0a8e'),
 'LICENSE': ('LICENSE', 10762, '746e4bf805bd511e9857cc7eb36f660197470082982d42e6eb47e065f6cf28ae'),
 'data/portuguese-00000-of-00001.parquet': ('portuguese.parquet', 172757977, 'fc43d5033a3f00740eb595cceeb633562b0d593d8a8eff42117fda52825c162a'),
}
IDENTITY = re.compile(r'\b(?:aira|chatgpt|openai|openassistant|llama|gpt[- ]?[2345])\b|finja (?:ser|que)|atue como', re.I)
PII = re.compile(r'[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}|(?:\d[ .()/+-]?){9,}|\b(?:CPF|RG|CEP)\s*[:=]\s*\d', re.I)

def digest(data):
 return hashlib.sha256(data).hexdigest()

def file_hash(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  while b:=f.read(1024*1024): h.update(b)
 return h.hexdigest()

def normalize(text):
 return ' '.join(unicodedata.normalize('NFC',text).casefold().split())

def fetch(cache):
 cache.mkdir(parents=True,exist_ok=True)
 for remote,(local,size,expected) in FILES.items():
  target=cache/local
  if not target.exists():
   temporary=target.with_suffix('.download')
   try:
    with urllib.request.urlopen(f'https://huggingface.co/datasets/{REPOSITORY}/resolve/{REVISION}/{remote}',timeout=60) as r,temporary.open('wb') as w:
     count=0
     while block:=r.read(1024*1024):
      count+=len(block)
      if count>size: raise ValueError('Source exceeds pinned size')
      w.write(block)
    if temporary.stat().st_size!=size or file_hash(temporary)!=expected: raise ValueError('Source hash mismatch')
    temporary.replace(target)
   finally:
    temporary.unlink(missing_ok=True)
  if target.stat().st_size!=size or file_hash(target)!=expected: raise ValueError('Cached source mismatch')

def filter_messages(messages):
 if not isinstance(messages,list) or len(messages)<2 or len(messages)>12 or len(messages)%2: return 'turn_count'
 for i,m in enumerate(messages):
  if not isinstance(m,dict) or m.get('role')!=('user' if i%2==0 else 'assistant'): return 'role_order'
  t=m.get('content')
  if not isinstance(t,str) or not t.strip() or len(t)>12000: return 'message_length'
  if IDENTITY.search(t): return 'external_identity_or_impersonation'
  if PII.search(t): return 'possible_identifier'
 if sum(len(m['content']) for m in messages)>24000: return 'conversation_length'
 if any(len(m['content'].strip())<20 for m in messages if m['role']=='assistant'): return 'short_assistant'
 return None

def leakage_keys(messages):
 # Root shared even when short; long messages shared at any position unite groups.
 return {digest(normalize(m['content']).encode()) for i,m in enumerate(messages) if i==0 or len(normalize(m['content']))>=80}

def assign_groups(records):
 parent=list(range(len(records)))
 def find(i):
  while parent[i]!=i:
   parent[i]=parent[parent[i]];i=parent[i]
  return i
 owner={}
 for i,r in enumerate(records):
  for key in sorted(leakage_keys(r['messages'])):
   if key in owner: parent[find(i)]=find(owner[key])
   else: owner[key]=i
 members={}
 for i,r in enumerate(records): members.setdefault(find(i),[]).append(r['id'])
 group_ids={root:digest('\n'.join(sorted(ids)).encode()) for root,ids in members.items()}
 for i,r in enumerate(records):
  group=group_ids[find(i)];bucket=int(group[:8],16)%100
  r['group_id']=group
  r['split']='train' if bucket<90 else 'validation' if bucket<95 else 'test'
 return records

def historical_keys():
 keys=set()
 paths=list((ROOT/'data/language-pilot').glob('*.json'))+list((ROOT/'data/neural-dialogue-v2/dialogues').glob('*.json'))
 paths+=[ROOT/'evaluation/portuguese-v1.json']
 for p in paths:
  value=json.loads(p.read_text())
  rows=value if isinstance(value,list) else value.get('cases',value.get('records',[]))
  if not isinstance(rows,list): continue
  for row in rows:
   if isinstance(row,dict) and row.get('messages'): keys.update(leakage_keys(row['messages']))
 return keys

def prepare(cache,output):
 import pyarrow.parquet as pq
 if output.exists(): raise ValueError('Choose a new output directory; published partitions are immutable')
 for _,(local,size,h) in FILES.items():
  f=cache/local
  if not f.exists() or f.stat().st_size!=size or file_hash(f)!=h: raise ValueError('Run pinned fetch first')
 excluded=Counter();records=[];seen=set();old=historical_keys()
 for batch in pq.ParquetFile(cache/'portuguese.parquet').iter_batches(batch_size=256):
  for row in batch.to_pylist():
   messages=row['conversations'];reason=filter_messages(messages)
   if reason: excluded[reason]+=1;continue
   messages=[{'role':m['role'],'content':unicodedata.normalize('NFC',m['content']).strip()} for m in messages]
   if leakage_keys(messages)&old: excluded['historical_overlap']+=1;continue
   content=digest(json.dumps([(m['role'],normalize(m['content'])) for m in messages],ensure_ascii=False).encode())
   if content in seen: excluded['exact_duplicate']+=1;continue
   seen.add(content)
   records.append({'id':content,'messages':messages,'synthetic':True,'source':REPOSITORY,'revision':REVISION,'license':'Apache-2.0','independently_fact_checked':False})
 assign_groups(records)
 output.mkdir(parents=True)
 for name in ['README.md','LICENSE']: (output/('SOURCE-'+name)).write_bytes((cache/name).read_bytes())
 shards=[];summary={}
 for split in ['train','validation','test']:
  rows=sorted((r for r in records if r['split']==split),key=lambda r:r['id'])
  summary[split]={'records':len(rows),'groups':len({r['group_id'] for r in rows}),'multiturn':sum(len(r['messages'])>2 for r in rows),'characters':sum(len(m['content']) for r in rows for m in r['messages'])}
  for start in range(0,len(rows),500):
   path=output/f'{split}-{start//500:04d}.jsonl.gz'
   raw=''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows[start:start+500]).encode()
   path.write_bytes(gzip.compress(raw,mtime=0))
   shards.append({'path':path.name,'split':split,'records':len(rows[start:start+500]),'bytes':path.stat().st_size,'sha256':file_hash(path)})
 manifest={'source':REPOSITORY,'revision':REVISION,'source_files':FILES,'source_rows':50000,'retained':len(records),'excluded':dict(excluded),'splits':summary,'shards':shards,'synthetic':True,'license':'Apache-2.0 as published; upstream prompts are not independently cleared','deduplication':'NFC casefold whitespace; exact conversations deduplicated; connected components of shared root or any >=80-character message kept in one split','limits':['No independent factual or language review; source labels portuguese.','Regex checks cannot guarantee absence of private data.','Near-duplicate paraphrases and upstream benchmark contamination may remain.','No weights trained or improved by corpus preparation.','All old evaluation remains historical; a new independent evaluation is needed.']}
 (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:manifest[k] for k in ['source_rows','retained','excluded','splits']},ensure_ascii=False,indent=2))

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--cache',type=Path,default=Path('/workspace/elysia-source-cache/aira-v3'))
 parser.add_argument('--output',type=Path,default=ROOT/'data/aira-pt-v1')
 parser.add_argument('--fetch',action='store_true')
 args=parser.parse_args()
 if args.fetch: fetch(args.cache)
 prepare(args.cache,args.output)
