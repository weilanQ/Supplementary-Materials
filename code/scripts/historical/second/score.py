"""Score the second pass from the archived replies. Run with Python and NumPy."""
from collections import defaultdict
from pathlib import Path
import json
import numpy as np
from run_control import digest, encode


def rows(path):
    return [json.loads(line) for line in path.read_bytes().splitlines()]


def label_from(raw):
    if raw.get('done') and raw.get('done_reason') != 'length':
        try:
            label = json.loads(raw['message']['content'])['label']
            if label in ('consistent', 'mismatch', 'unclear'):
                return label
        except (KeyError, TypeError, ValueError):
            pass
    return 'unclear'


def accuracy_difference(data, left, right):
    grouped = defaultdict(list)
    for row in data:
        grouped[row['trial']].append(int(row[left] == row['gold']) - int(row[right] == row['gold']))
    trials = np.array([(sum(v),len(v)) for _,v in sorted(grouped.items())])
    draws = np.random.default_rng(20261118).integers(0, len(trials), (2000, len(trials)))
    delta, size = trials[draws].sum(axis=1).T
    differences = [v for values in grouped.values() for v in values]
    return dict(gained=differences.count(1), lost=differences.count(-1), ci_pp=np.quantile(100*delta/size,[.025,.975]).tolist())


def main(folder):
    ref = {(r['model'],r['id']):r for r in rows(folder/'scoring_reference.jsonl')}
    plan = json.loads((folder/'protocol.json').read_bytes())
    assert len(ref)==160 and digest((folder/'inputs.jsonl').read_bytes())==plan['inputs_sha256']
    results = []
    for call in rows(folder/'inputs.jsonl'):
        req = call['request']
        model = req['model'].replace(':','_')
        key = digest(encode([call['model_digest'],req]))
        receipt = json.loads((folder/'responses'/(key+'.json')).read_bytes())
        assert receipt['key']==key and receipt['model_digest']==plan['models'][req['model']]
        raw = receipt['raw']
        row = ref[model,call['id']].copy()
        prompt = req['messages'][0]['content'].split('\n',1)[1]
        msg = json.loads(prompt)
        assert set(msg)=={'source','statement','earlier_judgment'}
        assert digest((msg['source']+'\0'+msg['statement']).encode())==row['input_hash']
        assert raw['model']==req['model'] and row['direct']==call['first']==msg['earlier_judgment']
        assert row['direct_cost']==call['first_cost'] and row['direct_cost'][0]==1 and row['fusion_cost'][0]==2
        row['second']=label_from(raw)
        row['token_total']=sum(row['direct_cost'][1:3])+raw['prompt_eval_count']+raw['eval_count']
        row['seconds_total']=row['direct_cost'][3]+receipt['seconds']
        results.append(row)
    summaries={}
    for model in sorted({r['model'] for r in results}):
        data=[r for r in results if r['model']==model]
        assert len(data)==len({r['id'] for r in data})==80 and len({r['trial'] for r in data})==20
        summary={k:sum(r[k]==r['gold'] for r in data) for k in ('direct','second','fusion')}
        summary.update(seconds=round(sum(r['seconds_total'] for r in data)), tokens=sum(r['token_total'] for r in data), calls=2*len(data), abstentions=sum(r['second']=='unclear' for r in data), second_vs_direct=accuracy_difference(data,'second','direct'), fusion_vs_second=accuracy_difference(data,'fusion','second'), fusion_fixes_also_fixed_by_second=sum(r['direct']!=r['gold'] and r['fusion']==r['gold']==r['second'] for r in data))
        summaries[model]=summary
    (folder/'results.json').write_text(json.dumps(summaries,indent=2)+'\n',encoding='utf8')
    print(json.dumps(summaries,indent=2))


if __name__=='__main__':
    main(Path(__file__).resolve().parent)
