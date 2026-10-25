"""Answer-only continuation on explicitly synthetic data, with full prompt windows."""
from __future__ import annotations
import argparse
import gzip
import json
import math
from pathlib import Path
import signal
import time
import torch
from torch.nn import functional as F
from brain.model import ElysiaTransformer, ModelConfig
from learning.aira_corpus import ROOT, file_hash, leakage_keys
from learning.dialogue_v2_data import FastProjectTokenizer
from learning.language_pilot import encode_messages, evaluate, reply
from learning.train_dialogue_v2 import atomic_save

DATA=ROOT/'data/aira-pt-v1'
BASE=ROOT/'artifacts/neural-dialogue-v2/run-001/pretrain-model.pt'
OUT=ROOT/'artifacts/aira-dialogue-v1/run-001'


def answer_windows(tokenizer,messages,context=256):
    """Keep the final user question intact; never train disconnected answer tails."""
    result=[]
    for end in range(2,len(messages)+1,2):
        # At most first and last assistant turns per source conversation.
        if end not in {2,len(messages)}: continue
        start=0
        while start<end-2:
            ids,labels=encode_messages(tokenizer,messages[start:end])
            if len(ids)<=context+1: break
            start+=2
        ids,labels=encode_messages(tokenizer,messages[start:end])
        if len(ids)>context+1: continue
        prefix,_=encode_messages(tokenizer,messages[start:end-1],for_reply=True)
        labels[:len(prefix)]=[-100]*len(prefix)
        if any(t!=-100 for t in labels[1:]): result.append((ids,labels))
    return result


def load_windows(tokenizer,context):
    manifest=json.loads((DATA/'manifest.json').read_text())
    evaluation=json.loads((ROOT/'evaluation/aira-v1.json').read_text())
    frozen_keys=set()
    for c in evaluation['cases']:
        for question in c['user_turns']:
            frozen_keys.update(leakage_keys([{'role':'user','content':question}]))
    documents={s:[] for s in ['train','validation','test']}
    counts={s:{'source_records':0,'usable_records':0,'windows':0,'usable_multiturn_records':0} for s in documents}
    for shard in manifest['shards']:
        p=DATA/shard['path']
        if file_hash(p)!=shard['sha256']: raise ValueError('Corpus shard changed')
        split=shard['split']
        # Fixed bounded validation/test subsets by immutable record ID, not content.
        with gzip.open(p,'rt',encoding='utf-8') as f:
            for line in f:
                row=json.loads(line);counts[split]['source_records']+=1
                if leakage_keys(row['messages']) & frozen_keys: raise ValueError('New evaluation overlap; abort before training')
                if split!='train' and int(row['id'][:8],16)%10: continue
                windows=answer_windows(tokenizer,row['messages'],context)
                counts[split]['usable_records']+=bool(windows)
                counts[split]['windows']+=len(windows)
                counts[split]['usable_multiturn_records']+=bool(windows) and len(row['messages'])>2
                documents[split].extend(windows)
    if any(not rows for rows in documents.values()): raise ValueError('Empty usable partition')
    return documents,counts


def batch(documents,generator,size,context):
    x=torch.zeros((size,context),dtype=torch.long);y=torch.full_like(x,-100)
    for i in range(size):
        ids,labels=documents[int(torch.randint(len(documents),(1,),generator=generator))]
        x[i,:len(ids)-1]=torch.tensor(ids[:-1]);y[i,:len(ids)-1]=torch.tensor(labels[1:])
    return x,y


def train(output=OUT,resume=False,steps=2000,max_seconds=1800):
    if not 1<=steps<=4000 or not 1<=max_seconds<=2700: raise ValueError('Invalid CPU budget')
    if (output/'results.json').exists(): raise ValueError('Finalized run is frozen')
    if output.exists() and not resume: raise ValueError('Explicit resume required')
    torch.set_num_threads(2);torch.use_deterministic_algorithms(True);torch.manual_seed(27102026)
    tokenizer=FastProjectTokenizer()
    checkpoint=torch.load(BASE,weights_only=True,map_location='cpu')
    model=ElysiaTransformer(ModelConfig(**checkpoint['model_config']));model.load_state_dict(checkpoint['model_state'])
    optimizer=torch.optim.AdamW(model.parameters(),lr=0.00015,weight_decay=0.01)
    rng=torch.Generator().manual_seed(27102027)
    settings={'steps':steps,'context':256,'batch':4,'source_sha256':file_hash(DATA/'manifest.json'),'initial_checkpoint_sha256':file_hash(BASE),'trainer_sha256':file_hash(Path(__file__)),'dependencies_sha256':{str(p.relative_to(ROOT)):file_hash(p) for p in [ROOT/'learning/language_pilot.py',ROOT/'learning/aira_corpus.py',ROOT/'brain/model.py',ROOT/'data/corpus-pt-v1/tokenizer/elysia-bpe.json',ROOT/'evaluation/aira-v1.json']},'torch':str(torch.__version__),'synthetic':True,'selection':'Only fixed validation assistant-token loss; old 24-case benchmark is not run.','scope':'Short-dialogue research; not complex-conversation or ChatGPT equivalence.'}
    progress={'step':0,'history':[],'best_loss':float('inf'),'best_step':0,'seconds':0.0,'targets':0}
    if resume:
        saved=torch.load(output/'last.pt',weights_only=True,map_location='cpu')
        if settings!=saved['settings']: raise ValueError('Resume settings changed')
        model.load_state_dict(saved['model_state']);optimizer.load_state_dict(saved['optimizer'])
        rng.set_state(saved['batch_rng']);torch.set_rng_state(saved['torch_rng']);progress=saved['progress']
    documents,counts=load_windows(tokenizer,settings['context'])
    print(json.dumps({'usable_data':counts}),flush=True)
    output.mkdir(parents=True,exist_ok=resume)
    started=time.perf_counter();prior=progress['seconds'];stopping=[False]
    previous={s:signal.signal(s,lambda signum,frame:stopping.__setitem__(0,True)) for s in [signal.SIGINT,signal.SIGTERM]}
    def save():
        progress['seconds']=prior+time.perf_counter()-started
        atomic_save({'model_config':model.config_dict(),'model_state':model.state_dict(),'tokenizer':tokenizer.metadata(),'optimizer':optimizer.state_dict(),'batch_rng':rng.get_state(),'torch_rng':torch.get_rng_state(),'settings':settings,'progress':progress},output/'last.pt')
    try:
        while progress['step']<steps:
            if stopping[0] or time.perf_counter()-started>=max_seconds:
                save();print(json.dumps({'paused':True,'step':progress['step']}),flush=True);return
            model.train();x,y=batch(documents['train'],rng,settings['batch'],settings['context'])
            factor=min(1,(progress['step']+1)/100)*(0.1+0.9*(1+math.cos(math.pi*progress['step']/steps))/2)
            for g in optimizer.param_groups:g['lr']=0.00015*factor
            optimizer.zero_grad(set_to_none=True)
            loss=F.cross_entropy(model(x).flatten(0,1),y.flatten(),ignore_index=-100)
            if not torch.isfinite(loss):raise ValueError('Nonfinite loss')
            loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1);optimizer.step()
            progress['step']+=1;progress['targets']+=int((y!=-100).sum())
            if progress['step']==1 or progress['step']%250==0 or progress['step']==steps:
                validation=evaluate(model,documents['validation'])['assistant']
                progress['history'].append({'step':progress['step'],'train_loss':loss.item(),'validation':validation})
                if validation['loss']<progress['best_loss']:
                    progress['best_loss']=validation['loss'];progress['best_step']=progress['step']
                    atomic_save({'model_config':model.config_dict(),'model_state':model.state_dict(),'tokenizer':tokenizer.metadata(),'stage':'sft','settings':settings,'step':progress['step'],'validation_loss':validation['loss']},output/'sft-model.pt')
                save();print(json.dumps(progress['history'][-1]),flush=True)
        best=torch.load(output/'sft-model.pt',weights_only=True,map_location='cpu');model.load_state_dict(best['model_state'])
        specification=json.loads((ROOT/'evaluation/aira-v1.json').read_text())
        generations=[]
        for case in specification['cases']:
            history=[];error=None
            for user in case['user_turns']:
                history.append({'role':'user','content':user})
                try:
                    answer=reply(model,tokenizer,history,tokens=96)
                    if not answer.strip(): raise ValueError('Empty response')
                    history.append({'role':'assistant','content':answer})
                except ValueError as exc:
                    error=str(exc);break
            generations.append({**case,'messages':history,'error':error})
        # Synthetic held-out loss and one frozen qualitative evaluation.
        result={'settings':settings,'progress':progress,'data_counts':counts,'test':evaluate(model,documents['test']),'generations':generations,'qualitative_generation_count':1,'checkpoint_sha256':file_hash(output/'sft-model.pt'),'semantic_evaluation':'Not established; no claim of conversational success.','old_benchmark_rerun':False}
        (output/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'completed':True,'best_step':progress['best_step'],'test':result['test']}),flush=True)
    finally:
        for s,h in previous.items(): signal.signal(s,h)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--resume',action='store_true');parser.add_argument('--steps',type=int,default=2000);parser.add_argument('--max-seconds',type=int,default=1800)
    args=parser.parse_args();train(resume=args.resume,steps=args.steps,max_seconds=args.max_seconds)
