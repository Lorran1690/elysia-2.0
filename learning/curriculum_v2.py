"""Train-only curriculum indices with complete histories and explicit lexical limits."""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import unicodedata
from tokenizers import Tokenizer
from brain.bpe_tokenizer import ByteBPETokenizer
from learning.aira_corpus import ROOT,file_hash
from learning.language_pilot import encode_messages

SOURCE=ROOT/'data/aira-pt-v1'
TOKENIZER=ROOT/'data/foundation-pt-v1/tokenizer'
DEST=ROOT/'data/curriculum-v2'
CONTEXTS=(256,512,1024,2048)
DESIRED={'contextual':0.6,'standalone':0.3,'generic_deferral_candidate':0.1}
DEFERRAL=re.compile(r'^(?:não (?:tenho|possuo|posso|consigo)|(?:sinto muito|lamento|infelizmente).{0,120}não)|como modelo de linguagem.{0,100}não',re.I)


class OwnTokenizer:
    def __init__(self,folder):
        self.own=ByteBPETokenizer.load(folder/'elysia-bpe.json')
        self.fast=Tokenizer.from_file(str(folder/'fast-bpe.json'))
        self.mapping={int(k):v for k,v in json.loads((folder/'fast-id-to-elysia-id.json').read_text()).items()}
        self.bos_id,self.eos_id=self.own.bos_id,self.own.eos_id
        self.vocab_size=self.own.vocab_size

    def encode(self,text,*,add_bos=True,add_eos=True):
        ids=[self.mapping[t] for t in self.fast.encode(unicodedata.normalize('NFC',text)).ids]
        return ([self.bos_id] if add_bos else [])+ids+([self.eos_id] if add_eos else [])

    def decode(self,ids,*,errors='strict'):
        return self.own.decode(ids,errors=errors)


def lexical_features(text):
    words=re.findall(r'\w+',text.casefold())
    grams=Counter(tuple(words[i:i+4]) for i in range(max(0,len(words)-3)))
    total=sum(grams.values());duplicate_fraction=1-len(grams)/total if total else 0
    maximum=max(grams.values(),default=0)
    return {'generic_deferral_candidate':bool(DEFERRAL.search(' '.join(text.split())[:240])),
            'strong_repetition':len(words)>=40 and maximum>=4 and duplicate_fraction>=0.45,
            'duplicate_fourgram_fraction':duplicate_fraction,'max_fourgram_repeat':maximum,
            'prefix_family':hashlib.sha256(' '.join(words[:8]).encode()).hexdigest()}


def prefix_candidates(tokenizer,row,maximum=2048):
    """No history cropping: train a target only with its entire preceding dialog."""
    length=1;prior_bad=False;candidates=[];rejected=Counter();coverage=Counter()
    for pair_index in range(len(row['messages'])//2):
        pair=row['messages'][2*pair_index:2*pair_index+2]
        ids,labels=encode_messages(tokenizer,pair)
        length+=len(ids)-1
        features=lexical_features(pair[1]['content'])
        for context in CONTEXTS:
            if length<=context+1:
                coverage[f'full_prefix_targets_{context}']+=1
                coverage[f'full_prefix_contextual_targets_{context}']+=pair_index>0
        if length>maximum+1:rejected['complete_history_exceeds_context']+=1
        elif prior_bad or features['strong_repetition']:rejected['strong_repetition_in_prefix']+=1
        else:
            bucket='generic_deferral_candidate' if features['generic_deferral_candidate'] else 'contextual' if pair_index else 'standalone'
            candidates.append({'source_record_id':row['id'],'source_group_id':row['group_id'],
                               'assistant_pair_index':pair_index,'preceding_pairs':pair_index,
                               'tokens_with_bos':length,'target_tokens':sum(t!=-100 for t in labels),
                               'bucket':bucket,'prefix_family':features['prefix_family'],
                               'synthetic':True,'semantic_quality':'not independently reviewed'})
        prior_bad|=features['strong_repetition']
    return candidates,rejected,coverage


def select_per_group(candidates,maximum=2):
    groups=defaultdict(list)
    for c in candidates:groups[c['source_group_id']].append(c)
    selected=[]
    for key in sorted(groups):
        rows=groups[key];chosen=[]
        for bucket in ['contextual','standalone','generic_deferral_candidate']:
            options=[r for r in rows if r['bucket']==bucket]
            if options and len(chosen)<maximum:
                # Prefer the deepest intact context, with deterministic ties.
                chosen.append(min(options,key=lambda r:(-r['preceding_pairs'],r['source_record_id'],r['assistant_pair_index'])))
        selected.extend(chosen)
    return selected


def probabilities(rows):
    families=Counter(r['prefix_family'] for r in rows)
    buckets=defaultdict(list)
    for r in rows:buckets[r['bucket']].append(r)
    if not (buckets.get('contextual') or buckets.get('standalone')):
        raise ValueError('A curriculum consisting only of generic deferrals is not accepted')
    active={k:DESIRED[k] for k in buckets}
    # Redistribute missing substantive mass only to substantive buckets.
    missing=1-sum(active.values());substantive=[k for k in active if k!='generic_deferral_candidate']
    for k in substantive:active[k]+=missing/len(substantive)
    for bucket,records in buckets.items():
        raw=[1/math.sqrt(families[r['prefix_family']]) for r in records]
        total=math.fsum(raw)
        for r,value in zip(records,raw):r['sampling_probability']=active[bucket]*value/total
    if not math.isclose(math.fsum(r['sampling_probability'] for r in rows),1,abs_tol=1e-10):raise ValueError('Sampling probabilities do not sum to one')
    return {k:math.fsum(r['sampling_probability'] for r in v) for k,v in buckets.items()}


def encode_target(tokenizer,messages,target):
    prefix=messages[:2*target['assistant_pair_index']+2]
    ids,labels=encode_messages(tokenizer,prefix)
    prompt,_=encode_messages(tokenizer,prefix[:-1],for_reply=True)
    labels[:len(prompt)]=[-100]*len(prompt)
    if len(ids)!=target['tokens_with_bos']:raise ValueError('Tokenizer or source target changed')
    return ids,labels


def prepare(output=DEST,tokenizer_folder=TOKENIZER):
    tokenizer_folder=tokenizer_folder.resolve()
    if output.exists():raise ValueError('Curriculum already exists; use a new directory')
    tokenizer_manifest=json.loads((tokenizer_folder/'manifest.json').read_text())
    if file_hash(tokenizer_folder/'elysia-bpe.json')!=tokenizer_manifest['elysia_tokenizer_sha256']:raise ValueError('Tokenizer changed')
    source_manifest=json.loads((SOURCE/'manifest.json').read_text())
    tokenizer=OwnTokenizer(tokenizer_folder);candidates=[];rejected=Counter();coverage=Counter();stats=Counter()
    for shard in source_manifest['shards']:
        if shard['split']!='train':continue
        path=SOURCE/shard['path']
        if file_hash(path)!=shard['sha256']:raise ValueError('Training shard changed')
        with gzip.open(path,'rt',encoding='utf-8') as f:
            for line in f:
                row=json.loads(line);stats['training_records']+=1
                items,why,covered=prefix_candidates(tokenizer,row)
                candidates.extend(items);rejected.update(why);coverage.update(covered)
                stats['training_assistant_targets']+=len(row['messages'])//2
        if stats['training_records']%5000==0:print(json.dumps({'processed_train_records':stats['training_records']}),flush=True)
    selected=select_per_group(candidates);mass=probabilities(selected)
    selected.sort(key=lambda r:(r['source_record_id'],r['assistant_pair_index']))
    output.mkdir(parents=True)
    path=output/'train-targets.jsonl.gz'
    path.write_bytes(gzip.compress(''.join(json.dumps(r,sort_keys=True)+'\n' for r in selected).encode(),mtime=0))
    for name in ['SOURCE-LICENSE','SOURCE-README.md']:shutil.copyfile(SOURCE/name,output/name)
    # A deterministic queue is an invitation to review, not an approval label.
    ranked=sorted(selected,key=lambda r:hashlib.sha256((r['source_record_id']+str(r['assistant_pair_index'])).encode()).hexdigest())
    queue_targets=[]
    for bucket in DESIRED:
        queue_targets.extend([r for r in ranked if r['bucket']==bucket][:12])
    keys={(r['source_record_id'],r['assistant_pair_index']) for r in queue_targets}
    for r in ranked:
        key=(r['source_record_id'],r['assistant_pair_index'])
        if len(queue_targets)>=40: break
        if key not in keys:queue_targets.append(r);keys.add(key)
    queue=[];by_record=defaultdict(list)
    for r in queue_targets:by_record[r['source_record_id']].append(r)
    for shard in source_manifest['shards']:
        if shard['split']!='train':continue
        with gzip.open(SOURCE/shard['path'],'rt',encoding='utf-8') as f:
            for line in f:
                row=json.loads(line)
                for target in by_record.get(row['id'],[]):
                    ids,labels=encode_target(tokenizer,row['messages'],target)
                    if len(ids)>2049 or not any(t!=-100 for t in labels):raise ValueError('Invalid complete target')
                    queue.append({'target':target,'messages':row['messages'][:2*target['assistant_pair_index']+2],
                                  'reviewer':None,'decision':'pending','factual_correctness':None,'context_correctness':None})
    (output/'review-queue.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in queue))
    manifest={'version':2,'source_manifest_sha256':file_hash(SOURCE/'manifest.json'),'fit_partition':'train only; validation and test remain untouched in source corpus','tokenizer_manifest_sha256':file_hash(tokenizer_folder/'manifest.json'),'tokenizer_sha256':file_hash(tokenizer_folder/'elysia-bpe.json'),'tokenizer_directory':str(tokenizer_folder.relative_to(ROOT)),'vocab_size':tokenizer.vocab_size,'maximum_context':2048,'history_policy':'Entire conversation prefix from first user through target; no cropped earlier turns','selection':'At most two targets per original connected group, prefer deepest contextual then standalone then lexical deferral candidate','counts':dict(stats),'coverage_before_lexical_filters':dict(coverage),'rejected_targets':dict(rejected),'candidate_targets':len(candidates),'selected_targets':len(selected),'bucket_target_counts':dict(Counter(r['bucket'] for r in selected)),'sampling_probability_mass':mass,'prefix_family_adjustment':'inverse square root frequency inside each bucket, computed from selected training targets only','targets_sha256':file_hash(path),'review_queue_sha256':file_hash(output/'review-queue.jsonl'),'review_queue_rows':len(queue),'independent_human_approval':False,'neural_weights_updated':False,'limits':['Lexical deferral is a candidate label, not proof that uncertainty is unwarranted.','High verbatim repetition filter may reject legitimate repetitive writing.','Bucket proportions are a new experimental hypothesis, not validated conversation quality.','Synthetic answers remain factually unverified.','The new 8192-token vocabulary is incompatible with old 2048-token checkpoints; new pretraining is required.']}
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(manifest,ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=DEST);p.add_argument('--tokenizer',type=Path,default=TOKENIZER);a=p.parse_args();prepare(a.output,a.tokenizer)
