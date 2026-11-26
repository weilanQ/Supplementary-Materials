"""Secondary checks on archived replies. These diagnostics never replace the frozen predictions."""
from collections import Counter
import json
from method import BASE, MODELS, dump, judge, read, repaired


# Reader note: Rejudge one response with explicit ambiguity given priority over a definite verdict in a different relation.
def ambiguity_first(item, raw):
    frozen = judge(item, raw)
    if frozen['prediction'] == 'unclear':
        return frozen['prediction']
    relations = json.loads(raw['message']['content'])['relations']
    return 'unclear' if any(r['row_id'] == -1 for r in relations) else frozen['prediction']


def compare():
    output_dir = BASE / 'results'
    predictions = read(output_dir / 'predictions.jsonl')
    keys = {r['id']: r for r in read(BASE / 'historical/key.jsonl')}
    audit = read(output_dir / 'audit.jsonl')
    report = {}
    for model in MODELS:
        name = model.replace(':', '_')
        items = [row for row in audit if row['model'] == name]
        estimates = {(row['id'],row['method']):row['prediction'] for row in predictions if row['model']==name}
        counts = Counter()
        details = []
        for row in items:
            uid = row['id']
            old = estimates[uid,'Joint + Direct'] == row['gold']
            new = estimates[uid,'Select + Direct'] == row['gold']
            if old != new:
                details.append({'id':uid, 'trial':row['trial'], 'change':'corrected' if new else 'lost', 'pair_type':keys[uid]['kind'], 'gold':row['gold']})
            if new and row['direct'] != row['gold']:
                counts[keys[uid]['kind']] += 1
        changes = Counter(r['change'] for r in details)
        mixed = []
        changed = []
        priority_overlap = Counter()
        for split in ('dev','confirmation'):
            for item in read(BASE / 'data' / (split+'.jsonl')):
                receipt = json.loads((BASE / 'logs' / f"{split}_{name}_{item['id']}.json").read_bytes())
                raw = receipt['raw']
                frozen = judge(item,raw)
                if ambiguity_first(item,raw) != frozen['prediction']:
                    changed.append({'id':item['id'],'split':split})
                try:
                    payload = json.loads(raw['message']['content'])
                    relations = payload['relations']
                except (KeyError,ValueError,TypeError):
                    continue
                if split == 'confirmation' and frozen['stage'] == 'incomplete' and relations and payload.get('complete') is False:
                    copied = dict(raw, message=dict(raw['message'],content=json.dumps(dict(payload,complete=True))))
                    next_stage = judge(item,copied)['stage']
                    if next_stage.startswith('invalid_'):
                        priority_overlap[next_stage] += 1
                ids = [r.get('row_id') for r in relations if isinstance(r,dict)]
                if -1 in ids and len(ids)>1:
                    mixed.append({'id':item['id'],'split':split,'frozen':judge(item,raw)['prediction']})
        report[name]={'compared_to_original_fallback':dict(changes), 'direct_errors_corrected_by_pair_type':dict(counts), 'changed_from_original_fallback':details, 'explicit_ambiguity_in_multi_relation_replies':mixed, 'changed_by_ambiguity_first':changed, 'later_invalidity_for_incomplete_nonempty':dict(priority_overlap)}
    # Construct an ambiguity case with a true numeric contradiction and an explicit -1.
    # This is an implementation boundary test, not another model call or a scored test item.
    item = next(x for x in read(BASE/'data/confirmation.jsonl') if x['id']=='30110659f9d529aa')
    reply = json.loads((BASE/'logs/confirmation_qwen2.5_7b_30110659f9d529aa.json').read_bytes())['raw']
    payload = json.loads(reply['message']['content'])
    assert judge(item,reply)['prediction']=='mismatch' and len(payload['relations'])==1
    payload['relations'].append(dict(payload['relations'][0],row_id=-1))
    edited=dict(reply,message=dict(reply['message'],content=json.dumps(payload)))
    report['synthetic_ambiguity']={'source_example':item['id'],'row_ids':[r['row_id'] for r in payload['relations']], 'original_aggregation':judge(item,edited)['prediction'],'ambiguity_first':ambiguity_first(item,edited)}
    assert report['synthetic_ambiguity']['original_aggregation']=='mismatch' and ambiguity_first(item,edited)=='unclear'
    example=read(BASE/'data/dev.jsonl')[0]
    # An artificial complete outer wrapper is the only error introduced in this demonstration.
    body=json.dumps({'complete':False,'records':[]}); wrapped='```json\n'+body+'\n```'
    report['synthetic_format']={'development_id':example['id'],'observed_model_output':False,'wrapped_text':wrapped,'after_strip':repaired(wrapped),'parsed_payload':json.loads(repaired(wrapped)),'semantically_complete':False}
    dump(output_dir / 'paired_audit.json', report)

if __name__=='__main__':
    compare()
