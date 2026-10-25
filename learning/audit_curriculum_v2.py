"""Validate concrete curriculum indices and article partitions without semantic grading."""
from collections import Counter
import gzip
import json
import math
from learning.aira_corpus import ROOT,file_hash
from learning.curriculum_v2 import OwnTokenizer,encode_target
from learning.prepared_corpus import load_partition


def audit():
    source=ROOT/'data/aira-pt-v1';destination=ROOT/'data/curriculum-v2';corpus=ROOT/'data/foundation-pt-v1'
    manifest=json.loads((destination/'manifest.json').read_text(encoding='utf-8'));original=json.loads((source/'manifest.json').read_text(encoding='utf-8'))
    assert file_hash(source/'manifest.json')==manifest['source_manifest_sha256']
    train_groups={}
    for shard in original['shards']:
        if shard['split']!='train':continue
        assert file_hash(source/shard['path'])==shard['sha256']
        with gzip.open(source/shard['path'],'rt',encoding='utf-8') as f:
            for line in f:
                r=json.loads(line);train_groups[r['id']]=(r['group_id'],len(r['messages'])//2)
    targets=destination/'train-targets.jsonl.gz';assert file_hash(targets)==manifest['targets_sha256']
    groups=Counter();buckets=Counter();probabilities=Counter();identities=set();count=0
    with gzip.open(targets,'rt',encoding='utf-8') as f:
        for line in f:
            r=json.loads(line);key=(r['source_record_id'],r['assistant_pair_index'])
            assert key not in identities;identities.add(key)
            group,turns=train_groups[r['source_record_id']]
            assert group==r['source_group_id'] and 0<=r['assistant_pair_index']<turns
            assert r['preceding_pairs']==r['assistant_pair_index']
            assert 0<r['target_tokens']<r['tokens_with_bos']<=2049
            assert math.isfinite(r['sampling_probability']) and r['sampling_probability']>0
            assert r['synthetic'] is True
            groups[group]+=1;buckets[r['bucket']]+=1;probabilities[r['bucket']]+=r['sampling_probability'];count+=1
    assert max(groups.values())<=2 and count==manifest['selected_targets']
    assert math.isclose(sum(probabilities.values()),1,abs_tol=1e-9)
    assert probabilities['generic_deferral_candidate']<=0.100000001
    tokenizer=OwnTokenizer(corpus/'tokenizer');queue=destination/'review-queue.jsonl'
    assert file_hash(queue)==manifest['review_queue_sha256']
    reviewed=0
    for line in queue.read_text(encoding='utf-8').splitlines():
        r=json.loads(line);assert r['decision']=='pending' and r['reviewer'] is None
        ids,labels=encode_target(tokenizer,r['messages'],r['target'])
        expected=''.join(('Usuário: ' if m['role']=='user' else 'Elysia: ')+' '.join(m['content'].split())+('\n' if m['role']=='user' else '') for m in r['messages'])
        assert tokenizer.decode(ids)==expected
        assert sum(t!=-100 for t in labels)==r['target']['target_tokens']
        reviewed+=1
    assert reviewed==manifest['review_queue_rows']
    article_groups={};article_ids=set();articles=Counter()
    for split in ['train','validation','test']:
        load_partition(split,corpus=corpus,for_training=split=='train')
        for line in (corpus/f'{split}.jsonl').open(encoding='utf-8'):
            r=json.loads(line);assert r['id'] not in article_ids;article_ids.add(r['id'])
            assert article_groups.setdefault(r['group_id'],split)==split
            assert r['license']=='CC-BY-SA-3.0' and r['source_url'].startswith('https://pt.wikipedia.org/wiki/')
            assert r['attribution'] and r['history_url'] and r['modifications']
            articles[split]+=1
    report={'selected_targets':count,'distinct_training_groups':len(groups),'maximum_targets_per_group':max(groups.values()),'bucket_counts':dict(buckets),'sampling_mass':dict(probabilities),'all_target_ids_belong_to_train_only':True,'complete_prefix_metadata_valid':True,'queue_rows_round_trip_and_target_mask_checked':reviewed,'queue_human_decisions':'all pending; none approved','article_partition_counts':dict(articles),'article_ids_unique':len(article_ids),'article_full_text_groups_crossing_splits':0,'article_attribution_and_license_fields_present':True,'all_language_partition_source_and_token_store_hashes_valid':True,'neural_weights_updated':False,'limits':'Structural/integrity audit; not independent human semantic or factual review. Near duplicates are not excluded by exact hash grouping.'}
    p=ROOT/'reports/curriculum-v2/integrity-audit.json';p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n', encoding='utf-8', newline='\n');print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':audit()
