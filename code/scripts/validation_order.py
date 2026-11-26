"""Post hoc replay using the written validation order. Both experimental freezes stay intact."""
from collections import Counter
from copy import deepcopy
import csv
import json
import re

from method import BASE, MODELS, dump, judge, lines, occurs_in_spans, point, props, rc, read, source_table


# Reader note: Replay the alternative validation order against one archived selector reply. The comparison records any change in the first failure.
def ordered_judgment(item, raw):
    """Validate all fields before completeness. Give explicit ambiguity whole-statement priority."""
    def abstain(stage):
        return {'stage': stage, 'prediction': 'unclear'}

    table = source_table(item['evidence'])
    if not table or not table['complete']:
        return abstain('source_invalid')
    if not raw.get('done') or raw.get('done_reason') == 'length':
        return abstain('truncated')
    try:
        body = json.loads(raw['message']['content'])
    except (ValueError, KeyError, TypeError):
        return abstain('invalid_json')
    if (not isinstance(body, dict) or type(body.get('complete')) is not bool
            or not isinstance(body.get('relations'), list)):
        return abstain('invalid_schema')
    relations = body['relations']
    for rel in relations:
        if (not isinstance(rel, dict) or set(rel) != set(props) or type(rel['row_id']) is not int
                or any(not isinstance(rel[k], str) for k in props if k != 'row_id')):
            return abstain('invalid_schema')
        if not -1 <= rel['row_id'] <= len(table['records']):
            return abstain('invalid_row_id')
    if any(point(rel['value']) is None for rel in relations):
        return abstain('invalid_point')
    claim = item['claim']
    for rel in relations:
        quote = rel['value_quote']
        spans = [m.span() for m in re.finditer(re.escape(quote), claim)] if quote else []
        if not occurs_in_spans(rel['value'], claim, spans):
            return abstain('invalid_value_quote')
    if any(rel[k] and rel[k] not in claim for rel in relations for k in rc.CONDITIONS):
        return abstain('invalid_condition_quote')
    if not body['complete'] or not relations:
        return abstain('incomplete')
    if any(rel['row_id'] == -1 for rel in relations):
        return abstain('explicit_ambiguity')
    # Delegate all candidate and outcome comparisons to the frozen evaluator.
    return judge(item, raw)


def boundary_checks():
    item = next(r for r in read(BASE/'data/confirmation.jsonl') if r['id']=='30110659f9d529aa')
    raw = json.loads((BASE/'logs/confirmation_qwen2.5_7b_30110659f9d529aa.json').read_bytes())['raw']
    body = json.loads(raw['message']['content'])
    def with_body(fn):
        modified = deepcopy(body)
        fn(modified)
        return dict(raw,message=dict(raw['message'],content=json.dumps(modified)))
    conflicting = with_body(lambda b: b['relations'].append(dict(b['relations'][0],row_id=-1)))
    assert judge(item,conflicting)['prediction']=='mismatch'
    assert ordered_judgment(item,conflicting)['stage']=='explicit_ambiguity'
    def incomplete_bad_quote(b):
        b['complete'] = False
        b['relations'][0]['value_quote'] = 'synthetic string absent from the statement'
    invalid = with_body(incomplete_bad_quote)
    assert judge(item,invalid)['stage']=='incomplete'
    assert ordered_judgment(item,invalid)['stage']=='invalid_value_quote'


def run():
    boundary_checks()
    out=BASE/'results'
    historical=read(out/'predictions.jsonl')
    with (out/'independent_predictions.csv').open(encoding='utf8',newline='') as f:
        independent=list(csv.DictReader(f))
    records=[]
    summary={}
    for split, path in [('dev', BASE/'data/dev.jsonl'),('confirmation',BASE/'data/confirmation.jsonl'),('independent',BASE/'independent/inputs.jsonl')]:
        summary[split]={}
        for model in MODELS:
            name=model.replace(':','_')
            labels=independent if split=='independent' else historical
            def predictions(method):
                return {r['id']:r['prediction'] for r in labels if r['method']==method and r['model'] in (model,name)}
            direct=predictions('Direct')
            official=predictions('Select + Direct')
            changes=Counter()
            result_changes=0
            fallback_changes=0
            items=read(path)
            for item in items:
                uid=item['id']
                if split=='independent':
                    file=BASE/'independent/logs'/f'{name}_select_{uid}.json'
                else:
                    file=BASE/'logs'/f'{split}_{name}_{uid}.json'
                raw=json.loads(file.read_bytes())['raw']
                before=judge(item,raw)
                after=ordered_judgment(item,raw)
                if before['stage']!=after['stage']:
                    changes[before['stage']+' -> '+after['stage']]+=1
                result_changes+=before['prediction']!=after['prediction']
                fallback=None
                if split!='dev':
                    previous=before['prediction'] if before['prediction']!='unclear' else direct[uid]
                    assert previous==official[uid]
                    fallback=after['prediction'] if after['prediction']!='unclear' else direct[uid]
                    fallback_changes+=fallback!=previous
                records.append(dict(split=split,model=model,id=uid,archived_stage=before['stage'],written_stage=after['stage'],archived_verdict=before['prediction'],written_verdict=after['prediction'],written_fallback=fallback))
            summary[split][model]=dict(replies=len(items),stage_changes=dict(changes),verdict_changes=result_changes,fallback_changes=fallback_changes if split!='dev' else None)
    lines(out/'validation_order_items.jsonl',records)
    dump(out/'validation_order_summary.json',summary)
    return summary

if __name__=='__main__':
    print(json.dumps(run(),indent=2))
