"""Replay the presence-matched no-conditions comparison on the initial 80 claims."""
from rules import inherited_claims, norm
from score import BASE, H, OUT, byid, decoded, get, lines, read, rc, source_table


# Reader note: Compare the two record lists while retaining condition presence. Ignore the values of present conditions.
def no_conditions(rows, claims):
    labels = []
    for claim in inherited_claims(rows, claims, structured=True):
        candidates = [row for row in rows
                      if all(rc.eq(row[k], claim[k]) for k in rc.IDENTITY)
                      and all(bool(norm(row[k])) == bool(norm(claim[k])) for k in rc.CONDITIONS)]
        values = {rc.numeric(row['value']) for row in candidates}
        if len(values) != 1:
            labels.append('unclear')
        else:
            matches = rc.value_eq(claim['value'], candidates[0]['value'])
            labels.append('consistent' if matches else 'mismatch')
    if 'mismatch' in labels:
        return 'mismatch'
    return 'consistent' if labels and all(x == 'consistent' for x in labels) else 'unclear'


def replay_conditions():
    inputs = byid(read(BASE / 'data/confirmation.jsonl'))
    results = []
    for item in read(H / 'decisions.jsonl'):
        if item['cohort'] != 'New':
            continue
        uid, model = item['id'], item['model']
        sample = inputs[uid]
        table = source_table(sample['evidence'])
        receipt = get(H / model / 'calls' / (item['calls']['joint'][-1] + '.json'))
        assert table['complete']
        prediction = 'unclear'
        obj = decoded(receipt['text'])
        if receipt['status'] == 'ok' and receipt['raw'].get('done_reason') != 'length' and isinstance(obj, dict):
            claims, errors = rc.validate_records(obj, sample['claim'])
            if claims and not errors and obj.get('complete') is True:
                prediction = no_conditions(table['records'], claims)
        assert prediction == item['pred']['no_conditions'], (model, uid)
        results.append(dict(model=model, id=uid, trial=item['trial'], kind=item['kind'],
                            gold=item['gold'], joint=item['pred']['joint'], no_conditions=prediction))
    assert len({(row['model'], row['id']) for row in results}) == len(results) == 160
    lines(OUT / 'condition_ablation.jsonl', results)
