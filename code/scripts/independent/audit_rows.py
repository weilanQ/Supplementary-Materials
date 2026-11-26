from pathlib import Path
from collections import Counter
from collect import ARTIFACT, HERE, MODELS, get, byid, read
from score import FIELDS, decoded, source_table, rc, lines


def audit_rows():
    """Offline only. Compare all returned row IDs with the value-blind reference set."""
    inputs = byid(read(HERE / 'inputs.jsonl'))
    keys = byid(read(HERE / 'key.jsonl'))
    diagnoses = []
    for item in read(ARTIFACT / 'results/independent_stages.jsonl'):
        uid, model = item['id'], item['model']
        table = source_table(inputs[uid]['evidence'])
        target = keys[uid]['target']
        complete = bool(table and table['complete'])
        rows = table['records'] if complete else []
        # Reader note: Reference-compatible rows are derived from identity and conditions. This offline score never changes a model verdict.
        compatible = [i for i, row in enumerate(rows, 1) if all(rc.eq(row[k], target[k]) for k in FIELDS)]
        receipt = get(HERE / 'logs' / f"{model.replace(':','_')}_select_{uid}.json")
        reply = decoded(receipt['raw']['message']['content'])
        relations = reply.get('relations') if isinstance(reply, dict) else None
        ids = [r.get('row_id') if isinstance(r,dict) else None for r in relations] if isinstance(relations,list) else []
        exact = len(ids) == 1 and type(ids[0]) is int and ids[0] in compatible
        diagnoses.append(dict(**item, trial=keys[uid]['trial'], gold=keys[uid]['gold'], source_complete=complete, returned_ids=ids, compatible_ids=compatible, exact=exact, json_valid=isinstance(reply,dict)))
    lines(ARTIFACT / 'results/independent_rows.jsonl', diagnoses)
    for model in MODELS:
        group = [r for r in diagnoses if r['model']==model]
        print(model, 'exact', sum(r['exact'] for r in group), 'of', sum(r['source_complete'] for r in group), 'with a parsed table')
        print(Counter((r['exact'], r['frozen']==r['gold']) for r in group if r['stage']=='decided'))

if __name__ == '__main__':
    audit_rows()
