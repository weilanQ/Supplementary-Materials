import json
from collect import ARTIFACT, HERE, MODELS, byid, direct, dump, get, read, request, verify
from paired_audit import ambiguity_first
from reproduce import judge, tally, export_csv, lines


# Reader note: Verify trial rows and archived requests, then write independent item predictions, aggregate metrics and first-stage labels.
def score():
    verify()
    inputs=byid(read(HERE/'inputs.jsonl'));keys=byid(read(HERE/'key.jsonl'));pins=get(ARTIFACT/'pins.json');screen=get(HERE/'screen.json')
    assert set(inputs)==set(keys) and len(inputs)==80
    assert len({x['trial'] for x in keys.values()})==20 and not set(screen['selected'])&set(screen['prior_trials'])
    for row in keys.values():
        study=get(HERE/'registry'/(row['trial']+'.json'))
        for field in ('target','donor'):
            pointer=row[field]['json_pointer'];obj=study
            for part in pointer.strip('/').split('/'):obj=obj[int(part)] if isinstance(obj,list) else obj[part]
            assert str(obj)==str(row[field]['value'])
        assert row['target']['value']!=row['donor']['value']
    counted=[]; checks=[]
    for model in MODELS:
        for uid,item in inputs.items():
            k=keys[uid]; name=model.replace(':','_');labels={};cost={}
            for method,prompt in [('direct',direct),('select',request)]:
                rec=get(HERE/'logs'/f'{name}_{method}_{uid}.json');raw=rec['raw'];assert rec['request']==prompt(item,model) and rec['digest']==pins[model] and rec['id']==uid and rec['model']==model and rec['method']==method
                cost[method]=(1,raw.get('prompt_eval_count',0)+raw.get('eval_count',0),rec['seconds'])
                if method=='direct':
                    try: label=json.loads(raw['message']['content'])['label'] if raw.get('done') and raw.get('done_reason')!='length' else 'unclear'
                    except (TypeError,KeyError,ValueError):label='unclear'
                    labels[method]=label if label in ('consistent','mismatch') else 'unclear'
                else:
                    outcome=judge(item,raw);labels[method]=outcome['prediction'];strict=ambiguity_first(item,raw);checks.append(dict(model=model,id=uid,stage=outcome['stage'],frozen=labels[method],ambiguity_first=strict));labels['strict']=strict
            # Reader note: An abstention uses Direct for this item. The combined cost counts both calls for every item.
            fallback=lambda label:labels['direct'] if label=='unclear' else label
            combined=tuple(a+b for a,b in zip(cost['direct'],cost['select']))
            for method,pred,usage in [('Direct',labels['direct'],cost['direct']),('Select',labels['select'],cost['select']),('Select + Direct',fallback(labels['select']),combined),('Ambiguity first + Direct',fallback(labels['strict']),combined)]:
                counted.append(dict(model=model,id=uid,trial=k['trial'],pair=k['pair'],kind=k['kind'],gold=k['gold'],direct=labels['direct'],method=method,prediction=pred,calls=usage[0],tokens=usage[1],seconds=usage[2]))
    metrics=[dict(model=m,method=method,**tally([x for x in counted if x['model']==m and x['method']==method])) for m in MODELS for method in ('Direct','Select','Select + Direct','Ambiguity first + Direct')]
    out=ARTIFACT/'results';out.mkdir(exist_ok=True);export_csv(out/'independent_predictions.csv',counted);dump(out/'independent_metrics.json',metrics);lines(out/'independent_stages.jsonl',checks)

if __name__=='__main__':score()
