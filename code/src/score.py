"""Recreate the post hoc diagnostic and the two main tables offline (Python 3.10+)."""
from method import BASE, MODELS, FIELDS, read, lines, dump, request, judge, repaired, rc, source_table, point, sha
from rules import verdict
from collections import Counter, defaultdict
import csv, hashlib, json, random, re
from pathlib import PureWindowsPath

H=BASE/'historical'; OUT=BASE/'results'; OUT.mkdir(exist_ok=True)
def get(p): return json.loads(p.read_bytes())
def byid(rows): return {r['id']:r for r in rows}
def decoded(raw):
    try: return json.loads(raw)
    except (TypeError,ValueError): return None

# Reader note: item supplies the text, receipt the archived extraction. repair enables wrapper cleanup. Return the first stopping stage and verdict.
def original(item,receipt,repair):
    text=receipt['text']; raw=receipt['raw']; unknown='unclear'; schema=decoded(repaired(text) if repair else text)
    if receipt['status']!='ok':return ('transport',unknown)
    if raw.get('done_reason')=='length':return ('truncated',unknown)
    if schema is None:return ('syntax',unknown)
    records,errors=rc.validate_records(schema,item['claim'])
    if errors:
        first=errors[0]; reason=first if isinstance(first,str) else first['reason']
        if reason=='missing_identity_or_numeric_value':
            row=schema['records'][first['index']]; reason='invalid_point' if point(row.get('value')) is None else 'missing_identity'
        return (reason,unknown)
    if schema.get('complete') is not True or not records:return ('incomplete',unknown)
    result=verdict(source_table(item['evidence'])['records'],records,True)
    if result['prediction']!=unknown:return ('decided',result['prediction'])
    return ('candidate_conflict' if any('conflict' in x['reason'] for x in result['relations']) else 'no_compatible_row',unknown)

# Reader note: Group paired correctness differences by trial. Return the two percentile bounds in percentage points after 2,000 resamples.
def pct_interval(rows):
    groups=defaultdict(list)
    for x in rows:groups[x['trial']].append(int(x['prediction']==x['gold'])-int(x['direct']==x['gold']))
    values=[(sum(v),len(v)) for _,v in sorted(groups.items())]; rng=random.Random(20261118); rates=[]
    for _ in range(2000):
        sample=rng.choices(values,k=len(values)); rates.append(sum(z[0] for z in sample)*100/sum(z[1] for z in sample))
    rates.sort(); return [rates[49],rates[1949]]

# Reader note: For one model and method, count definite answers, errors, gains and losses against Direct. Accuracy uses every statement.
def tally(rows):
    correct=sum(x['prediction']==x['gold'] for x in rows); answered=sum(x['prediction']!='unclear' for x in rows); fix=sum(x['prediction']==x['gold']!=x['direct'] for x in rows);lost=sum(x['direct']==x['gold']!=x['prediction'] for x in rows);tp=sum(x['prediction']==x['gold']=='mismatch' for x in rows);fp=sum(x['prediction']=='mismatch' and x['gold']=='consistent' for x in rows); positive=sum(x['gold']=='mismatch' for x in rows);negative=len(rows)-positive
    ratio=lambda a,b:100*a/b if b else None
    return dict(n=len(rows),correct=correct,answered=answered,wrong=answered-correct,coverage=ratio(answered,len(rows)),accuracy=ratio(correct,len(rows)),precision=ratio(tp,tp+fp),recall=ratio(tp,positive),f1=ratio(2*tp,tp+fp+positive),fpr=ratio(fp,negative),fixed=fix,lost=lost,net=fix-lost,ci=pct_interval(rows),calls=sum(x['calls'] for x in rows),tokens=sum(x['tokens'] for x in rows),seconds=sum(x['seconds'] for x in rows))

def export_csv(path,rows):
    with path.open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)

# Reader note: Read the frozen inputs and original replies, then write item predictions, first-stage counts and summary metrics.
def score():
    frozen=get(BASE/'freeze.json'); assert all(sha(BASE.joinpath(*PureWindowsPath(k).parts))==v for k,v in frozen['hashes'].items()); inputs=byid(read(BASE/'data/confirmation.jsonl')); keys=byid(read(H/'key.jsonl')); refs=byid(read(H/'checked_confirmation_relations.jsonl')); old={(x['model'],x['id']):x for x in read(H/'decisions.jsonl') if x['cohort']=='New'}; diffs={(x['model'],x['id']):x for x in read(H/'validated_relations.jsonl')}; second={}; predictions=[]; audit=[]; dev=[]
    for x in read(H/'second/inputs.jsonl'):
        req=x['request']; key=hashlib.sha256(json.dumps([x['model_digest'],req],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest();receipt=get(H/'second/responses'/f'{key}.json'); raw=receipt['raw']; obj=decoded(raw['message']['content']); label=obj.get('label') if isinstance(obj,dict) else None; prediction=label if raw.get('done') and raw.get('done_reason')!='length' and label in ('consistent','mismatch') else 'unclear'; second[req['model'],x['id']]=(prediction,[2,x['first_cost'][1]+raw['prompt_eval_count'],x['first_cost'][2]+raw['eval_count'],x['first_cost'][3]+receipt['seconds']]);
    for model in MODELS:
        name=model.replace(':','_'); path=H/name; logs=byid(read(path/'items.jsonl')); devkeys=byid(read(BASE/'data/dev_key.jsonl'))
        for item in read(BASE/'data/dev.jsonl'):
            i=item['id'];receipt=get(BASE/'logs'/f'dev_{name}_{i}.json');assert receipt['request']==request(item,model);dev.append(dict(model=model,id=i,gold=devkeys[i]['gold'],**judge(item,receipt['raw'])))
        for i,item in inputs.items():
            x=old[name,i]; key=keys[i]; ref=refs[i]; orig=logs[i]; direct=x['pred']['direct']; receipts=path/'calls'; c=get(receipts/(orig['calls']['joint'][-1]+'.json')); pre=original(item,c,False);post=original(item,c,True);assert pre[1]==x['pred']['joint']; receipt=get(BASE/'logs'/f'confirmation_{name}_{i}.json'); assert receipt['request']==request(item,model) and receipt['digest']==get(BASE/'pins.json')[model]; raw=receipt['raw']; row=judge(item,raw); value=row['prediction']; fresh=[1,raw.get('prompt_eval_count',0),raw.get('eval_count',0),receipt['seconds']]; rows=source_table(item['evidence'])['records']; compatible=[j for j,r in enumerate(rows,1) if all(rc.eq(r[z],ref['record'][z]) for z in FIELDS)]; assert compatible
            obj=decoded(raw['message']['content']); rr=obj.get('relations') if isinstance(obj,dict) else None; ids=[z.get('row_id') if isinstance(z,dict) else None for z in rr] if isinstance(rr,list) else [];selected=len(ids)==1 and type(ids[0])==int and 1<=ids[0]<=len(rows); exact=selected and ids[0] in compatible; valid=row['stage'] in ('candidate_conflict','selection_unresolved','decided'); audit.append(dict(model=name,id=i,trial=key['trial'],gold=key['gold'],original_first=pre[0],repaired_first=post[0],mechanical_bytes_changed=repaired(c['text'])!=c['text'],old_field_differences=diffs.get((name,i),{}).get('reference_field_differences'),selection_stage=row['stage'],json_valid=isinstance(obj,dict),valid=valid,one_positive_id=selected,returned_ids=ids,compatible_ids=compatible,exact_selection=exact,selected_prediction=value,direct=direct,claim=item['claim']))
            metrics={'Direct':(direct,x['cost']['direct']),'Two-pass Direct':second[model,i],'Record-LLM':(x['pred']['record_llm'],x['cost']['record_llm']),'Joint':(pre[1],x['cost']['joint']),'Joint + Direct':(x['pred']['fusion'],x['cost']['fusion']),'Repair':(post[1],x['cost']['joint']),'Repair + Direct':(post[1] if post[1]!='unclear' else direct,x['cost']['fusion']),'Select':(value,fresh),'Select + Direct':(value if value!='unclear' else direct,[a+b for a,b in zip(fresh,x['cost']['direct'])])}
            for method,(pred,cost) in metrics.items():predictions.append(dict(model=name,id=i,trial=key['trial'],pair=key['pair'],gold=key['gold'],direct=direct,method=method,prediction=pred,calls=cost[0],tokens=cost[1]+cost[2],seconds=cost[3]))
    assert len(audit)==160 and len(dev)==40;lines(OUT/'audit.jsonl',audit);lines(OUT/'development.jsonl',dev);lines(OUT/'predictions.jsonl',predictions);export_csv(OUT/'predictions.csv',predictions); summary=[]; decomposition={}
    for name in [x.replace(':','_') for x in MODELS]:
        group=[x for x in audit if x['model']==name]; d={k:dict(Counter(x[k] for x in group)) for k in ('original_first','repaired_first','selection_stage')};d['offline_differences']=dict(Counter(z for x in group if x['old_field_differences'] is not None for z in x['old_field_differences'])); d['valid_original']=sum(x['old_field_differences'] is not None for x in group);d['groups_overlapping']={k:sum(any(z in fields for z in x['old_field_differences']) for x in group if x['old_field_differences'] is not None) for k,fields in [('count',['relation count']),('identity_or_value',list(rc.IDENTITY)+['value']),('conditions',rc.CONDITIONS)]};d['selection_checks']={k:sum(x[k] for x in group) for k in ['json_valid','valid','one_positive_id','exact_selection']};d['valid_exact']=sum(x['valid'] and x['exact_selection'] for x in group);d['decision_by_selection']=dict(Counter(f"row_{'right' if x['exact_selection'] else 'other'}_verdict_{'abstain' if x['selected_prediction']=='unclear' else ('right' if x['selected_prediction']==x['gold'] else 'wrong')}" for x in group));decomposition[name]=d
        for m in dict.fromkeys(x['method'] for x in predictions):summary.append(dict(model=name,method=m,**tally([x for x in predictions if x['model']==name and x['method']==m])))
    dump(OUT/'failure.json',decomposition);dump(OUT/'metrics.json',summary);export_csv(OUT/'metrics.csv',summary)
if __name__=='__main__':score()

