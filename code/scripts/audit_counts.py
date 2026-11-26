"""Audit paper counts from the frozen replies without changing predictions."""
from collections import Counter
import json
from method import BASE, FIELDS, MODELS, read, source_table, rc
from rules import inherited_claims, verdict


def keyed(records):
    return {row['id']: row for row in records}


def audit():
    result = {}
    historical = BASE / 'historical'
    inputs = keyed(read(BASE / 'data/confirmation.jsonl'))
    refs = keyed(read(historical / 'checked_confirmation_relations.jsonl'))
    original_keys = keyed(read(historical / 'key.jsonl'))
    archived_differences = {(r['model'], r['id']): r['reference_field_differences']
                            for r in read(historical / 'validated_relations.jsonl')}
    tables = {uid: source_table(item['evidence'])['records'] for uid, item in inputs.items()}
    oracle = {}
    for uid, ref in refs.items():
        relation = dict(ref['record'], value=ref['value_read_from_statement'])
        assert relation['value'] in inputs[uid]['claim']
        decision = verdict(tables[uid], [relation], True)['prediction']
        assert decision == ref['component'] == original_keys[uid]['gold']
        oracle[uid] = decision
    result['reference_input_check'] = dict(Counter(oracle.values()))
    historical_items = read(historical / 'decisions.jsonl')
    development_trials = {x['trial'] for x in read(historical / 'source_checks.jsonl') if x['split'] != 'test'}
    main_prior = development_trials | {x['trial'] for x in historical_items if x['cohort'] in ('Registry','First','Holdout','Public')}
    all_prior = development_trials | {x['trial'] for x in historical_items if x['cohort'] != 'New'}
    result['historical_partition_counts'] = dict(earlier_listed=len(main_prior), additional_screened_trials=len(all_prior-main_prior), all_previously_seen=len(all_prior))
    for model in MODELS:
        name = model.replace(':', '_')
        folder = historical / name
        counts = Counter()
        for item in read(folder / 'items.jsonl'):
            if item['gate'] != 'pass':
                continue
            uid = item['id']
            receipt = json.loads((folder/'calls'/(item['calls']['joint'][-1]+'.json')).read_bytes())
            extracted, errors = rc.validate_records(json.loads(receipt['text']), inputs[uid]['claim'])
            assert not errors
            observed = inherited_claims(tables[uid], extracted, True)
            ref = dict(refs[uid]['record'], value=refs[uid]['value_read_from_statement'])
            counts['passed'] += 1
            if len(observed) != 1:
                reasons = ['relation count']
                counts['extra' if len(observed)>1 else 'missing'] += 1
            else:
                reasons = [f for f in FIELDS if not rc.eq(ref[f], observed[0][f])]
                if not rc.value_eq(ref['value'], observed[0]['value']):
                    reasons.append('value')
                identity = bool(set(reasons) & set(rc.IDENTITY+('value',)))
                condition = bool(set(reasons) & set(rc.CONDITIONS))
                counts['single'] += 1
                counts['identity_or_value'] += identity
                counts['condition'] += condition
                counts['both'] += identity and condition
            assert reasons == archived_differences[name,uid]
        independent = BASE / 'independent'
        stages = {r['id']:r['stage'] for r in read(BASE/'results/independent_stages.jsonl') if r['model']==model}
        flags = Counter()
        for uid, stage in stages.items():
            raw = json.loads((independent/'logs'/f'{name}_select_{uid}.json').read_bytes())['raw']
            incomplete = json.loads(raw['message']['content'])['complete'] is False
            flags['model_marked_incomplete'] += incomplete
            flags['incomplete_at_first_stop'] += stage == 'incomplete'
            flags['incomplete_and_source_invalid'] += incomplete and stage == 'source_invalid'
        result[model] = dict(offline_field_differences=dict(counts), independent_flags=dict(flags))
    return result


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2))
