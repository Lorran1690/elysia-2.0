"""Independent structural and cross-partition audit of the published corpus."""
import gzip,json
from pathlib import Path
from collections import Counter
from learning.aira_corpus import ROOT,file_hash,leakage_keys,filter_messages

def audit():
    p=ROOT/'data/aira-pt-v1';m=json.loads((p/'manifest.json').read_text());owners={};groups={};ids=set();rows=Counter();multiturn=Counter();overlaps=[]
    for s in m['shards']:
     f=p/s['path'];assert file_hash(f)==s['sha256'];assert f.stat().st_size==s['bytes']
     n=0
     with gzip.open(f,'rt',encoding='utf-8') as stream:
      for line in stream:
       r=json.loads(line);n+=1;assert r['id'] not in ids;ids.add(r['id']);assert r['synthetic'] is True
       assert r['license']=='Apache-2.0' and r['split']==s['split'];assert filter_messages(r['messages']) is None
       split=r['split'];rows[split]+=1;multiturn[split]+=len(r['messages'])>2
       assert groups.setdefault(r['group_id'],split)==split
       for k in leakage_keys(r['messages']):
        if owners.setdefault(k,split)!=split:overlaps.append(k)
     assert n==s['records']
    assert not overlaps
    assert sum(rows.values())+sum(m['excluded'].values())==m['source_rows']
    report={'source_revision':m['revision'],'manifest_sha256':file_hash(p/'manifest.json'),'all_shards_hash_size_and_record_count_valid':True,'records':dict(rows),'multiturn_records':dict(multiturn),'unique_ids':len(ids),'group_count':len(groups),'cross_split_shared_roots_or_long_messages':len(overlaps),'all_retained_pass_declared_structural_and_regex_filters':True,'source_count_reconciles':True,'independent_human_quality_review':False,'limitations':m['limits']}
    (ROOT/'reports/aira-dialogue-v1/data-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    audit()
