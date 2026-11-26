"""Build and verify the navigation index using the frozen inputs and released predictions."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def records(path):
    return [json.loads(line) for line in (ROOT / path).read_bytes().splitlines() if line]


def by_id(path):
    rows = records(path)
    index = {row['id']: row for row in rows}
    assert len(index) == len(rows)
    return index


def build():
    rows = []
    for cohort, inputs, reference, predictions in [
        ('initial', 'data/confirmation.jsonl', 'historical/key.jsonl', 'results/predictions.csv'),
        ('independent', 'independent/inputs.jsonl', 'independent/key.jsonl', 'results/independent_predictions.csv'),
    ]:
        claims, keys = by_id(inputs), by_id(reference)
        assert len(claims) == 80 and claims.keys() == keys.keys()
        with (ROOT / predictions).open(encoding='utf-8', newline='') as stream:
            scored = {(r['model'], r['id'], r['method']): r for r in csv.DictReader(stream)}
        for model in ('qwen2.5:7b', 'llama3.1:8b'):
            tag = model.replace(':', '_')
            model_key = tag if cohort == 'initial' else model
            receipts = by_id(f'historical/{tag}/items.jsonl') if cohort == 'initial' else {}
            for uid, key in sorted(keys.items(), key=lambda v: (v[1]['trial'], v[1]['pair'], v[0])):
                if cohort == 'initial':
                    direct_hash, = receipts[uid]['calls']['direct']
                    direct_path = f'historical/{tag}/calls/{direct_hash}.json'
                    select_path = f'logs/confirmation_{tag}_{uid}.json'
                else:
                    direct_path = f'independent/logs/{tag}_direct_{uid}.json'
                    select_path = f'independent/logs/{tag}_select_{uid}.json'
                direct_raw, select_raw = (json.loads((ROOT / path).read_bytes()) for path in (direct_path, select_path))
                assert select_raw['id'] == uid and select_raw['request']['model'] == model
                assert direct_raw['request']['model'] == model
                if cohort == 'initial':
                    frozen_input = (claims[uid]['evidence'] + '\0' + claims[uid]['claim']).encode()
                    assert hashlib.sha256(frozen_input).hexdigest() == receipts[uid]['input_sha256']
                else:
                    assert direct_raw['id'] == uid
                direct, select, fallback = [scored[model_key, uid, method] for method in ('Direct', 'Select', 'Select + Direct')]
                assert all(x['gold'] == key['gold'] and x['trial'] == key['trial'] and x['pair'] == key['pair'] for x in (direct, select, fallback))
                assert fallback['prediction'] == (direct['prediction'] if select['prediction'] == 'unclear' else select['prediction'])
                rows.append(dict(cohort=cohort, model=model_key, id=uid, trial=key['trial'], pair=key['pair'],
                                 kind=key['kind'], gold=key['gold'], direct=direct['prediction'], select=select['prediction'],
                                 fallback=fallback['prediction'], input_file=inputs, reference_file=reference,
                                 target_pointer=key['target']['json_pointer'], donor_pointer=key['donor']['json_pointer'],
                                 direct_reply=direct_path, select_reply=select_path))
    assert len(rows) == len({(r['cohort'], r['model'], r['id']) for r in rows}) == 320
    with (ROOT / 'guide/evaluation_index.tsv').open('w', encoding='utf-8', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]), delimiter='\t', lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


if __name__ == '__main__':
    build()
