"""Inspect the larger own-model profile and optionally calibrate on a local GPU."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import time
import torch
import yaml
from brain.model import ElysiaTransformer,ModelConfig
from learning.aira_corpus import ROOT,file_hash
from learning.prepared_corpus import load_partition
from learning.dataset import make_batch


def architecture_count(configuration):
    # No real allocation of a large set of random weights just to count them.
    with torch.device('meta'):
        model=ElysiaTransformer(ModelConfig(**configuration))
    return model.num_parameters()


def inspect(config_path):
    profile=yaml.safe_load(config_path.read_text(encoding='utf-8'))
    corpus=ROOT/profile['corpus'];tokenizer=json.loads((corpus/'tokenizer/manifest.json').read_text(encoding='utf-8'))
    if profile['model']['vocab_size']!=tokenizer['vocab_size']:raise ValueError('Model vocabulary differs from own tokenizer')
    # Enforce exactly the preassigned partition, without recomputing a split.
    stores={s:load_partition(s,corpus=corpus,for_training=s=='train') for s in ['train','validation','test']}
    curriculum_path=ROOT/profile['curriculum']/'manifest.json'
    curriculum=json.loads(curriculum_path.read_text(encoding='utf-8'))
    if curriculum['tokenizer_sha256']!=tokenizer['elysia_tokenizer_sha256']:raise ValueError('Curriculum tokenizer mismatch')
    if profile['model']['block_size']<curriculum['maximum_context']:raise ValueError('Model cannot contain the complete curriculum context')
    if profile['calibration']['context']>profile['model']['block_size']:raise ValueError('Calibration context exceeds model')
    parameters=architecture_count(profile['model']);gpu=torch.cuda.is_available()
    report={'configuration_sha256':file_hash(config_path),'target_hardware_declared':profile.get('target_hardware'),'parameters':parameters,'own_vocabulary':tokenizer['vocab_size'],
            'maximum_context':profile['model']['block_size'],'available_training_tokens':stores['train'].numel(),
            'corpus_tokens_per_parameter':stores['train'].numel()/parameters,
            'training_token_type':'One pass over sampled encyclopedia train store, not total training exposure.',
            'parameter_gradient_adam_bytes_estimate':16*parameters,
            'memory_estimate_limits':'Parameter/gradient/Adam states only, not activations, attention, temporary buffers or runtime overhead. Not a GPU memory guarantee.',
            'cuda_available':gpu,'gpu_device_count':torch.cuda.device_count(),'gpu_calibration_ready':gpu,
            'blocking_reasons':[] if gpu else ['No local CUDA GPU is available; no CPU fallback for the larger profile.'],
            'curriculum_human_review_complete':curriculum['independent_human_approval'],
            'full_training_readiness':'Not established: broader pretraining and independent curriculum review remain necessary.',
            'neural_weights_updated':False,'old_checkpoint_compatible':False,
            'incompatibility_reason':'New vocabulary and architecture require new own-model pretraining, not loading the old checkpoint.'}
    return profile,report


def benchmark(profile,steps,*,context=None,precision="auto"):
    if not torch.cuda.is_available():raise RuntimeError('GPU calibration requires a local CUDA GPU; no CPU fallback')
    if not 2<=steps<=profile['calibration']['maximum_steps']:raise ValueError('Calibration step count exceeds fixed budget')
    if precision not in {'auto','fp16','fp32'}:raise ValueError('Unknown precision')
    context=profile['calibration']['context'] if context is None else context
    if context not in {256,512,1024,2048} or context>profile['model']['block_size']:raise ValueError('Unsupported calibration context')
    torch.manual_seed(profile['seed']);device=torch.device('cuda')
    model=ElysiaTransformer(ModelConfig(**profile['model'])).to(device)
    optimizer=torch.optim.AdamW(model.parameters(),lr=profile['calibration']['learning_rate'])
    source=load_partition('train',corpus=ROOT/profile['corpus'],for_training=True)
    rng=torch.Generator().manual_seed(profile['seed']+1)
    dtype=torch.float32 if precision=='fp32' else torch.float16 if precision=='fp16' else torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    scaler=torch.amp.GradScaler('cuda',enabled=dtype==torch.float16)
    torch.cuda.reset_peak_memory_stats();started=time.perf_counter();losses=[]
    for _ in range(steps):
        x,y=make_batch(source,batch_size=profile['calibration']['batch_size'],block_size=context,device=device,generator=rng)
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast('cuda',dtype=dtype,enabled=dtype!=torch.float32):_,loss=model(x,y)
        if not torch.isfinite(loss):raise ValueError('Nonfinite calibration loss')
        scaler.scale(loss).backward();scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(),profile['calibration']['gradient_clip_norm'])
        scaler.step(optimizer);scaler.update();losses.append(loss.item())
    torch.cuda.synchronize();seconds=time.perf_counter()-started
    return {'steps':steps,'seconds':seconds,'tokens_per_second':steps*profile['calibration']['batch_size']*context/seconds,
            'peak_cuda_allocated_bytes':torch.cuda.max_memory_allocated(),'peak_cuda_reserved_bytes':torch.cuda.max_memory_reserved(),
            'dtype':str(dtype),'context':context,'gpu_name':torch.cuda.get_device_name(),'gpu_total_memory_bytes':torch.cuda.get_device_properties(device).total_memory,'losses':losses,'weights_saved':False,
            'scope':'Disposable random-initialization hardware calibration only; no held-out evaluation or conversational benchmark.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,default=ROOT/'configs/foundation-gtx1650.yaml');p.add_argument('--output',type=Path,default=ROOT/'reports/curriculum-v2/gpu-preflight.json');p.add_argument('--benchmark-steps',type=int,default=0);p.add_argument('--benchmark-context',type=int);p.add_argument('--precision',choices=['auto','fp16','fp32'],default='auto');a=p.parse_args()
    profile,report=inspect(a.config)
    failed=False
    if a.benchmark_steps:
        try:report['calibration']=benchmark(profile,a.benchmark_steps,context=a.benchmark_context,precision=a.precision)
        except (RuntimeError,ValueError) as exc:
            report['calibration']={'completed':False,'error':str(exc),'weights_saved':False};failed=True
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n', encoding='utf-8', newline='\n');print(json.dumps(report,ensure_ascii=False,indent=2))
    if failed:raise SystemExit(2)
