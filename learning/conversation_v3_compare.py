"""Compare frozen checkpoints on identical held-out targets and consumed diagnostics."""
import json
import torch
from learning.conversation_v3 import ROOT, OUT, DEPLOYED, load_data, write_json
from learning.curriculum_v2 import lexical_features
from learning.generate_text import load_inference_checkpoint
from learning.language_pilot import evaluate
from learning.aira_corpus import file_hash


def main():
    destination=ROOT/'reports/conversation-v3/comparison.json'
    if destination.exists():raise ValueError('Frozen comparison exists')
    generations=json.loads((ROOT/'reports/conversation-v3/generations.json').read_text(encoding='utf-8'))
    data,_=load_data();result={}
    torch.set_num_threads(2)
    for name,path in [('deployed',DEPLOYED),('candidate',OUT/'sft-model.pt')]:
        assert file_hash(path)==generations['results'][name]['checkpoint_sha256']
        model,tokenizer=load_inference_checkpoint(path,device=torch.device('cpu'),
            tokenizer_path=ROOT/'data/corpus-pt-v1/tokenizer/elysia-bpe.json')
        cases=generations['results'][name]['cases']
        answers=[m['content'] for c in cases for m in c['messages'] if m['role']=='assistant']
        features=[lexical_features(a) for a in answers]
        result[name]={'checkpoint_sha256':file_hash(path),
            'validation':evaluate(model,[(r['ids'],r['labels']) for r in data['validation']])['assistant'],
            'test':evaluate(model,[(r['ids'],r['labels']) for r in data['test']])['assistant'],
            'diagnostic':{'cases':len(cases),'generated_answers':len(answers),
                'errors':sum(c['error'] is not None for c in cases),
                'generic_deferral_candidate_answers':sum(f['generic_deferral_candidate'] for f in features),
                'strongly_repetitive_answers':sum(f['strong_repetition'] for f in features)},
            'semantic_quality':'Requires separate identified review; lexical counts and loss are not semantic correctness.'}
    write_json(destination,{'identical_held_out_targets':True,'no_checkpoint_selection_from_test':True,
                           'results':result})
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
