"""Bounded CPU study: balanced intact dialogue prefixes with the deployed vocabulary."""
from __future__ import annotations
import argparse
from collections import Counter
import gzip
import json
import math
from pathlib import Path
import shutil
import signal
import time
import torch
from torch.nn import functional as F
from brain.model import ElysiaTransformer, ModelConfig
from learning.aira_corpus import ROOT, file_hash, leakage_keys
from learning.curriculum_v2 import prefix_candidates, select_per_group, probabilities, encode_target
from learning.dialogue_v2_data import FastProjectTokenizer
from learning.language_pilot import evaluate, reply
from learning.generate_text import load_inference_checkpoint
from learning.train_dialogue_v2 import atomic_save

DATA = ROOT / 'data/conversation-v3'
OUT = ROOT / 'artifacts/conversation-v3/run-001'
BASE = ROOT / 'artifacts/neural-dialogue-v2/run-001/pretrain-model.pt'
DEPLOYED = ROOT / 'artifacts/aira-dialogue-v1/run-001/sft-model.pt'
SPEC = ROOT / 'evaluation/conversation-v3.json'
CONTEXT = 512


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def prepare():
    if (DATA / 'manifest.json').exists():
        raise ValueError('Published preparation is immutable')
    tokenizer = FastProjectTokenizer()
    source = ROOT / 'data/aira-pt-v1'
    manifest = json.loads((source / 'manifest.json').read_text(encoding='utf-8'))
    specification = json.loads(SPEC.read_text(encoding='utf-8'))
    frozen = set()
    for case in specification['cases']:
        for turn in case['user_turns']:
            frozen.update(leakage_keys([{'role':'user','content':turn}]))
    candidates = {s: [] for s in ('train','validation','test')}
    rows = {}; rejected = Counter(); exclusions = Counter()
    for shard in manifest['shards']:
        path = source / shard['path']
        if file_hash(path) != shard['sha256']:
            raise ValueError('Source shard changed')
        with gzip.open(path, 'rt', encoding='utf-8') as stream:
            for line in stream:
                row = json.loads(line)
                row_keys = set().union(*(leakage_keys([m]) for m in row['messages'] if m['role']=='user'))
                if row_keys & frozen:
                    exclusions[shard['split']] += 1
                    continue
                items, reasons, _ = prefix_candidates(tokenizer, row, maximum=CONTEXT)
                rejected.update(reasons)
                if items:
                    rows[row['id']] = row
                    candidates[shard['split']].extend(items)
    selected = select_per_group(candidates['train'])
    mass = probabilities(selected)
    partitions = {'train':selected}
    for split in ('validation','test'):
        partitions[split] = sorted(candidates[split], key=lambda r:(r['source_record_id'],r['assistant_pair_index']))[:128]
    summaries = {}; group_sets = {}
    DATA.mkdir(exist_ok=True)
    for split, targets in partitions.items():
        encoded = []
        for target in targets:
            ids, labels = encode_target(tokenizer, rows[target['source_record_id']]['messages'], target)
            encoded.append({**target, 'ids':ids, 'labels':labels})
        if not encoded:
            raise ValueError('Empty partition')
        path = DATA / f'{split}.jsonl.gz'
        path.write_bytes(gzip.compress(''.join(json.dumps(r,sort_keys=True)+'\n' for r in encoded).encode(),mtime=0))
        groups = {r['source_group_id'] for r in encoded}; group_sets[split] = groups
        summaries[split] = {'targets':len(encoded),'groups':len(groups),
            'buckets':dict(Counter(r['bucket'] for r in encoded)), 'sha256':file_hash(path),
            'assistant_tokens':sum(sum(t!=-100 for t in r['labels']) for r in encoded)}
    assert not any(group_sets[a] & group_sets[b] for a,b in [('train','validation'),('train','test'),('validation','test')])
    for name in ('SOURCE-LICENSE','SOURCE-README.md'):
        shutil.copyfile(source / name, DATA / name)
    write_json(DATA / 'manifest.json', {'source_manifest_sha256':file_hash(source/'manifest.json'),
        'source':'Aira v3, existing immutable grouped partitions; explicitly synthetic',
        'tokenizer':tokenizer.metadata(),'maximum_full_prefix_tokens':CONTEXT+1,
        'history_cropped':False,'human_reviewed':False,'train_sampling_mass':mass,
        'selection':'At most two targets per group; 60% contextual, 30% standalone, 10% lexical deferral candidates; inverse sqrt prefix-family frequency.',
        'validation_test_selection':'First 128 eligible targets sorted by content-hashed record ID and pair index; no resampling weights.',
        'rejected':dict(rejected),'evaluation_overlap_excluded':dict(exclusions),
        'spec_sha256':file_hash(SPEC),'partitions':summaries})
    print(json.dumps(summaries),flush=True)


def load_data():
    manifest = json.loads((DATA/'manifest.json').read_text(encoding='utf-8'))
    if manifest['spec_sha256'] != file_hash(SPEC):
        raise ValueError('Frozen diagnostic changed')
    documents = {}
    for split, info in manifest['partitions'].items():
        path = DATA / f'{split}.jsonl.gz'
        if file_hash(path) != info['sha256']:
            raise ValueError('Prepared data changed')
        with gzip.open(path, 'rt', encoding='utf-8') as stream:
            documents[split] = [json.loads(line) for line in stream]
    return documents, manifest


def batch(rows, weights, generator, size=4):
    chosen = torch.multinomial(weights, size, replacement=True, generator=generator).tolist()
    length = max(len(rows[i]['ids'])-1 for i in chosen)
    x = torch.zeros((size,length),dtype=torch.long)
    y = torch.full_like(x,-100)
    for j,i in enumerate(chosen):
        ids, labels = rows[i]['ids'], rows[i]['labels']
        x[j,:len(ids)-1] = torch.tensor(ids[:-1])
        y[j,:len(ids)-1] = torch.tensor(labels[1:])
    return x,y


def train(steps=1000, max_seconds=1800, resume=False):
    if not 1 <= steps <= 2000 or not 1 <= max_seconds <= 2700:
        raise ValueError('Invalid bounded CPU budget')
    if (OUT/'results.json').exists() or OUT.exists() and not resume:
        raise ValueError('Finalized runs are frozen; explicit resume required for partial runs')
    torch.set_num_threads(2); torch.use_deterministic_algorithms(True); torch.manual_seed(28102026)
    tokenizer = FastProjectTokenizer(); documents, manifest = load_data()
    checkpoint = torch.load(BASE,weights_only=True,map_location='cpu')
    if checkpoint['tokenizer'] != tokenizer.metadata():
        raise ValueError('Vocabulary mismatch')
    model = ElysiaTransformer(ModelConfig(**checkpoint['model_config']))
    model.load_state_dict(checkpoint['model_state'])
    optimizer = torch.optim.AdamW(model.parameters(),lr=.0002,weight_decay=.01)
    rng = torch.Generator().manual_seed(28102027)
    settings = {'steps':steps,'context':CONTEXT,'batch':4,'lr':.0002,'seed':28102026,
        'initial_sha256':file_hash(BASE),'deployed_reference_sha256':file_hash(DEPLOYED),
        'data_sha256':file_hash(DATA/'manifest.json'),'spec_sha256':file_hash(SPEC),
        'trainer_sha256':file_hash(Path(__file__)),'torch':str(torch.__version__),
        'synthetic':True,'selection':'held-out assistant-token validation loss only',
        'dependency_sha256':{p:file_hash(ROOT/p) for p in ['brain/model.py','learning/language_pilot.py','learning/curriculum_v2.py','learning/dialogue_v2_data.py']}}
    progress = {'step':0,'targets':0,'seconds':0.,'best_loss':float('inf'),'best_step':0,'history':[]}
    if resume:
        saved = torch.load(OUT/'last.pt',weights_only=True,map_location='cpu')
        if saved['settings'] != settings:
            raise ValueError('Resume settings changed')
        model.load_state_dict(saved['model_state']);optimizer.load_state_dict(saved['optimizer'])
        rng.set_state(saved['batch_rng']);torch.set_rng_state(saved['torch_rng']);progress=saved['progress']
    OUT.mkdir(parents=True,exist_ok=resume)
    weights = torch.tensor([r['sampling_probability'] for r in documents['train']],dtype=torch.float64)
    validation = [(r['ids'],r['labels']) for r in documents['validation']]
    started = time.perf_counter(); prior = progress['seconds']; stopping = [False]
    previous = {s:signal.signal(s,lambda a,b:stopping.__setitem__(0,True)) for s in (signal.SIGINT,signal.SIGTERM)}
    def save():
        progress['seconds'] = prior + time.perf_counter()-started
        atomic_save({'model_config':model.config_dict(),'model_state':model.state_dict(),
            'optimizer':optimizer.state_dict(),'tokenizer':tokenizer.metadata(),
            'settings':settings,'progress':progress,'batch_rng':rng.get_state(),'torch_rng':torch.get_rng_state()},OUT/'last.pt')
    try:
        while progress['step'] < steps:
            if stopping[0] or time.perf_counter()-started >= max_seconds:
                save();print(json.dumps({'paused':True,'step':progress['step']}),flush=True);return
            model.train(); x,y = batch(documents['train'],weights,rng)
            factor = min(1,(progress['step']+1)/50)*(.1+.9*(1+math.cos(math.pi*progress['step']/steps))/2)
            for group in optimizer.param_groups:group['lr'] = settings['lr']*factor
            optimizer.zero_grad(set_to_none=True)
            loss = F.cross_entropy(model(x).flatten(0,1),y.flatten(),ignore_index=-100)
            if not torch.isfinite(loss):raise ValueError('Nonfinite training loss')
            loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1);optimizer.step()
            progress['step'] += 1;progress['targets'] += int((y!=-100).sum())
            if progress['step']==1 or progress['step']%100==0 or progress['step']==steps:
                measured = evaluate(model,validation)['assistant']
                progress['history'].append({'step':progress['step'],'train_loss':loss.item(),'validation':measured})
                if measured['loss'] < progress['best_loss']:
                    progress['best_loss'] = measured['loss'];progress['best_step'] = progress['step']
                    atomic_save({'model_config':model.config_dict(),'model_state':model.state_dict(),
                        'tokenizer':tokenizer.metadata(),'stage':'sft','settings':settings,
                        'step':progress['step'],'validation_loss':measured['loss']},OUT/'sft-model.pt')
                save();print(json.dumps(progress['history'][-1]),flush=True)
        best = torch.load(OUT/'sft-model.pt',weights_only=True,map_location='cpu')
        model.load_state_dict(best['model_state'])
        test = evaluate(model,[(r['ids'],r['labels']) for r in documents['test']])
        write_json(OUT/'results.json',{'settings':settings,'progress':progress,'data':manifest['partitions'],
            'test':test,'checkpoint_sha256':file_hash(OUT/'sft-model.pt'),
            'semantic_success':'Not established; fresh diagnostic still needs review.'})
        print(json.dumps({'completed':True,'best_step':progress['best_step'],'test':test}),flush=True)
    finally:
        for s,h in previous.items():signal.signal(s,h)


def diagnose():
    destination = ROOT/'reports/conversation-v3/generations.json'
    if destination.exists():raise ValueError('Diagnostic already consumed; do not rerun or tune on it')
    torch.set_num_threads(2)
    cases = json.loads(SPEC.read_text(encoding='utf-8'))['cases']; results = {}
    for name,path in [('deployed',DEPLOYED),('candidate',OUT/'sft-model.pt')]:
        model,tokenizer = load_inference_checkpoint(path,device=torch.device('cpu'),tokenizer_path=ROOT/'data/corpus-pt-v1/tokenizer/elysia-bpe.json')
        outputs=[]
        for case in cases:
            messages=[];error=None
            for turn in case['user_turns']:
                messages.append({'role':'user','content':turn})
                try:
                    answer=reply(model,tokenizer,messages,tokens=96)
                    if not answer.strip():raise ValueError('Empty response')
                    messages.append({'role':'assistant','content':answer})
                except ValueError as exc:
                    error=str(exc);break
            outputs.append({**case,'messages':messages,'error':error})
        results[name]={'checkpoint_sha256':file_hash(path),'cases':outputs}
        print(json.dumps({'diagnosed':name}),flush=True)
    write_json(destination,{'spec_sha256':file_hash(SPEC),'selection_independent':True,'results':results})


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','train','diagnose'])
    parser.add_argument('--steps',type=int,default=1000);parser.add_argument('--max-seconds',type=int,default=1800)
    parser.add_argument('--resume',action='store_true');args=parser.parse_args()
    if args.action=='prepare':prepare()
    elif args.action=='train':train(args.steps,args.max_seconds,args.resume)
    else:diagnose()
