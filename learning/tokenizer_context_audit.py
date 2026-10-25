"""Compare own tokenizers on a fixed training-only sample; not model evaluation."""
import gzip
import json
from pathlib import Path
import statistics
from collections import Counter
from learning.aira_corpus import ROOT,file_hash
from learning.curriculum_v2 import OwnTokenizer,lexical_features,prefix_candidates
from learning.aira_dialogue import answer_windows
from learning.language_pilot import encode_messages


def audit(limit=1000):
    source=ROOT/'data/aira-pt-v1';manifest=json.loads((source/'manifest.json').read_text())
    folders={'previous_2048':ROOT/'data/corpus-pt-v1/tokenizer','new_8192':ROOT/'data/foundation-pt-v1/tokenizer'}
    encoders={k:OwnTokenizer(p) for k,p in folders.items()};lengths={k:[] for k in encoders};ids=[]
    legacy=Counter();new_candidates=Counter()
    for shard in manifest['shards']:
        if shard['split']!='train' or len(ids)>=limit:continue
        path=source/shard['path']
        if file_hash(path)!=shard['sha256']:raise ValueError('Source shard mismatch')
        with gzip.open(path,'rt',encoding='utf-8') as stream:
            for line in stream:
                row=json.loads(line);ids.append(row['id'])
                for key,tokenizer in encoders.items():lengths[key].append(len(encode_messages(tokenizer,row['messages'])[0]))
                for _,labels in answer_windows(encoders['previous_2048'],row['messages'],256):
                    text=encoders['previous_2048'].decode([t for t in labels if t!=-100])
                    legacy['windows']+=1
                    legacy['generic_deferral_candidates']+=lexical_features(text)['generic_deferral_candidate']
                items,_,_=prefix_candidates(encoders['new_8192'],row,2048)
                new_candidates.update(item['bucket'] for item in items)
                if len(ids)>=limit:break
    report={'scope':'First 1000 immutable content-hash-sorted training records; no validation/test fitting or qualitative benchmark.','sample_records':len(ids),'source_manifest_sha256':file_hash(source/'manifest.json'),'sample_id_sha256':__import__('hashlib').sha256('\n'.join(ids).encode()).hexdigest(),'tokenizers':{key:{'vocab':encoders[key].vocab_size,'own_sha256':file_hash(folders[key]/'elysia-bpe.json'),'total_tokens':sum(values),'median_conversation_tokens':statistics.median(values),'complete_conversations_fitting_context':{str(c):sum(n<=c+1 for n in values) for c in [256,512,1024,2048]}} for key,values in lengths.items()},'new_to_previous_token_ratio':sum(lengths['new_8192'])/sum(lengths['previous_2048']),'legacy_256_window_distribution':dict(legacy),'new_2048_complete_prefix_candidates_before_balancing':dict(new_candidates),'comparison_limits':'Window distributions change tokenizer, context length and history policy together; this does not isolate a single cause. Prefix labels are lexical, not semantic quality judgments.','neural_weights_updated':False,'limits':'Compression and context coverage are not comprehension or factual correctness. Tokenizer vocabularies are incompatible; old model embeddings cannot be reused unchanged.'}
    p=ROOT/'reports/curriculum-v2/tokenizer-context-audit.json';p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':audit()
