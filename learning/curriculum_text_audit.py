"""Training-only lexical diagnostics; no semantic or human quality labels."""
import gzip,json,re
from collections import Counter
from pathlib import Path
from learning.aira_corpus import ROOT,file_hash

def audit():
    p=ROOT/'data/aira-pt-v1';m=json.load(open(p/'manifest.json'));prefix=Counter();counts=Counter();families=Counter()
    for s in m['shards']:
     if s['split']!='train':continue
     if file_hash(p/s['path'])!=s['sha256']:raise ValueError('Source shard changed')
     with gzip.open(p/s['path'],'rt') as f:
      for line in f:
       r=json.loads(line);counts['conversations']+=1
       for msg in r['messages']:
        if msg['role']!='assistant':continue
        t=' '.join(msg['content'].casefold().split());words=re.findall(r'\w+',t);counts['answers']+=1
        prefix[' '.join(words[:8])]+=1
        if t.startswith(('não tenho acesso','não tenho informações','não possuo acesso','não sou capaz')):counts['generic_deferral_prefix']+=1
        grams=[tuple(words[i:i+4]) for i in range(max(0,len(words)-3))]
        if grams and max(Counter(grams).values())>=4:counts['repeated_fourgram_at_least_four']+=1
        if len(words)<60:counts['under_60_words']+=1
    (ROOT/'reports/curriculum-v2/train-text-audit.json').write_text(json.dumps({'source_manifest_sha256':file_hash(p/'manifest.json'),'scope':'Training split only; no validation/test contents inspected for these statistics.','counts':dict(counts),'common_eight_word_prefixes':prefix.most_common(20),'limits':'Lexical diagnostics, not semantic labels of truth, refusal correctness or quality.'},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'counts':dict(counts),'top_prefixes':prefix.most_common(6)},ensure_ascii=False))

if __name__ == "__main__":
    audit()
