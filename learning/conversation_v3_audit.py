import json,gzip,math
from collections import Counter
from pathlib import Path
from learning.conversation_v3 import load_data, ROOT, SPEC, encode_target
from learning.dialogue_v2_data import FastProjectTokenizer
from learning.aira_corpus import leakage_keys

def main():
    parts,manifest=load_data();tokenizer=FastProjectTokenizer(); membership={}; originals={};groups={}
    selected={(r['source_record_id'],r['assistant_pair_index']) for records in parts.values() for r in records}
    source=ROOT/'data/aira-pt-v1';upstream=json.loads((source/'manifest.json').read_text(encoding='utf-8'))
    for shard in upstream['shards']:
     with gzip.open(source/shard['path'],'rt',encoding='utf-8') as f:
      for line in f:
       r=json.loads(line);membership[r['id']]=shard['split'];groups[r['id']]=r['group_id']
       if any((r['id'],i) in selected for i in range(len(r['messages'])//2)):originals[r['id']]=r
    frozen=set()
    for case in json.loads(SPEC.read_text(encoding='utf-8'))['cases']:
     for text in case['user_turns']:frozen.update(leakage_keys([{'role':'user','content':text}]))
    sets={};counts={};sample=[]
    for split,records in parts.items():
     sets[split]={r['source_group_id'] for r in records};counts[split]=len(records)
     for r in records:
      assert membership[r['source_record_id']]==split
      assert groups[r['source_record_id']]==r['source_group_id']
      assert len(r['ids'])==len(r['labels'])==r['tokens_with_bos']<=513
      assert r['labels'][-1]==tokenizer.eos_id
      assert sum(v!=-100 for v in r['labels'])==r['target_tokens']
      row=originals[r['source_record_id']]
      assert not set().union(*(leakage_keys([m]) for m in row['messages'] if m['role']=='user')) & frozen
     for bucket in ['contextual','standalone','generic_deferral_candidate']:
      sample.extend([(split,r) for r in records if r['bucket']==bucket][:12 if split=='train' else 4])
    assert not any(sets[a]&sets[b] for a,b in [('train','validation'),('train','test'),('validation','test')])
    assert max(Counter(r['source_group_id'] for r in parts['train']).values())<=2
    mass={b:math.fsum(r['sampling_probability'] for r in parts['train'] if r['bucket']==b) for b in ['contextual','standalone','generic_deferral_candidate']}
    assert all(math.isclose(mass[b],v) for b,v in [('contextual',.6),('standalone',.3),('generic_deferral_candidate',.1)])
    for split,r in sample:
     ids,labels=encode_target(tokenizer,originals[r['source_record_id']]['messages'],r)
     assert ids==r['ids'] and labels==r['labels']
    json.dump({'targets_checked':counts,'group_splits_disjoint':True,'source_partition_membership_checked':True,'frozen_questions_absent_from_all_user_turns':True,'tokens_and_supervised_label_counts_verified':True,'canonical_full_prefix_encoding_and_mask_samples':len(sample),'train_sampling_mass':mass,'human_quality_review':False},(ROOT/'reports/conversation-v3/data-audit.json').open('w',encoding='utf-8'),indent=2)
    print('audit passed')

if __name__ == "__main__":
    main()
