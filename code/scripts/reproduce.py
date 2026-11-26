"""Verify archived requests and generate every diagnostic table without an inference server."""
import sys, os
from pathlib import Path
# The legacy shared module computes unused workstation paths on import. At a shallow
# POSIX extraction path supply only its standard modules, which are all rules.py uses.
if len(Path(__file__).resolve().parent.parents)<3:
    import types, json, re, hashlib
    shared=types.ModuleType('shared');shared.__dict__.update(re=re,json=json,hashlib=hashlib,os=os,sys=sys,Path=Path);sys.modules['shared']=shared
from score import *
from boundaries import corroborate
from tables import make
from paired_audit import compare

def old_label(receipt):
    if receipt['status']!='ok' or receipt['raw'].get('done_reason')=='length':return 'unclear'
    obj=decoded(receipt['text']);label=obj.get('label') if isinstance(obj,dict) else None
    return label if label in ('consistent','mismatch') else 'unclear'

def verify_receipts():
    pins=get(BASE/'pins.json');dev=byid(read(BASE/'data/dev.jsonl'));confirm=byid(read(BASE/'data/confirmation.jsonl'));assert len(set(dev)&set(confirm))==0;assert len(list((BASE/'logs').glob('*.json')))==200
    for model in MODELS:
        name=model.replace(':','_');folder=H/name
        for item in read(folder/'items.jsonl'):
            uid=item['id']; text=confirm[uid];assert item['input_sha256']==hashlib.sha256((text['evidence']+'\0'+text['claim']).encode()).hexdigest();received={}
            for method in ('direct','joint','record_llm'):
                cost=[0,0,0,0.];logs=[]
                for call in item['calls'][method]:
                    receipt=get(folder/'calls'/f'{call}.json');digest=hashlib.sha256(json.dumps({'request':receipt['request'],'model_digest':receipt['model_digest']},sort_keys=True).encode()).hexdigest();assert digest==call and receipt['model_digest']==pins[model];raw=receipt['raw']; cost=[a+b for a,b in zip(cost,[1,raw.get('prompt_eval_count',0),raw.get('eval_count',0),receipt['seconds']])];logs.append(receipt)
                assert all(abs(a-b)<1e-6 for a,b in zip(cost,item['cost'][method]));received[method]=logs
            assert old_label(received['direct'][0])==item['pred']['direct'];pick=old_label(received['record_llm'][-1]) if item['gate']=='pass' else 'unclear';assert pick==item['pred']['record_llm']
        for split,inputs in [('dev',dev),('confirmation',confirm)]:
            for uid,it in inputs.items():
                r=get(BASE/'logs'/f'{split}_{name}_{uid}.json');assert r['id']==uid and r['split']==split and r['digest']==pins[model] and r['request']==request(it,model)

if __name__=='__main__':
    verify_receipts();score();corroborate();make();compare()
    from condition_ablation import replay_conditions
    replay_conditions()
    sys.path.insert(0,str(BASE/'independent'))
    from holdout_score import score as score_independent
    from verify_sources import audit_sources
    from render_holdout import write_table
    audit_sources()
    score_independent()
    write_table()
    from audit_rows import audit_rows
    audit_rows()
    from audit_counts import audit as audit_counts
    dump(OUT/'paper_counts.json',audit_counts())
    from validation_order import run as replay_validation_order
    replay_validation_order()
    if (BASE/'expected.json').exists():
        for name,value in get(BASE/'expected.json').items():assert hashlib.sha256((OUT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==value,name
    print('Verified both cohorts and regenerated the paper tables and individual predictions.')
