"""Offline sensitivity check. Pass the root of the associated replication archive."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import numeric_evidence_extended as extended


def regression_cases():
    cases = [
        ('5 or more participants', '5', '5', False),
        ('5 or fewer participants', '5', '5', False),
        ('between 3 and 5 days', '3', '3', False),
        ('between 3 and 5 days', '5', '5', False),
        ('between -3 and +5 days', '-3', '-3', False),
        ('3 or more. The observed count was 3.', '3', 'was 3', True),
        ('The two recorded values were 3 and 5.', '5', '5', True),
    ]
    for text, value, quote, expected in cases:
        start = text.index(quote)
        assert extended.occurs_in_spans(value, text, [(start, start + len(quote))]) == expected
    return len(cases)


def main(root):
    sys.path.insert(0, str(root))
    from recompute_final import nested
    from run_confirmation import install, freeze
    from reassess import build_sets, read_lines, request_index

    assert json.loads((root/'confirmation/freeze.json').read_bytes()) == freeze()
    decisions = read_lines(root/'analysis_results/decisions.jsonl')
    examined = Counter()
    changes = []
    with TemporaryDirectory() as temp, ZipFile(root/'archive/source_review_19.zip') as hist, nested(hist,'previous_release.zip') as mid, nested(mid,'baseline/paper_and_replication.zip') as base, ZipFile(root/'archive/update_20.zip') as update:
        install(Path(temp), base, mid)
        import run_experiment
        import numeric_evidence
        from rules import rc, source_table
        index = request_index([base, mid, hist, update])
        inputs = {cohort: {key: item[0] for key, item in group.items()} for cohort, group in build_sets(base, update, hist, mid).items()}
        inputs['New'] = {r['id']: r for r in read_lines(root/'confirmation/confirm.jsonl')}
        for row in decisions:
            cohort, model, uid = row['cohort'], row['model'], row['id']
            item = inputs[cohort][uid]
            assert hashlib.sha256((item['evidence']+'\0'+item['claim']).encode()).hexdigest() == row['hash']
            calls = row['calls']['joint']
            sides = [('claim', calls[-1])]
            if source_table(item['evidence']) is None:
                sides.append(('evidence', calls[0]))
            for side, call in sides:
                if cohort == 'New':
                    raw = (root/'confirmation/runs'/(model+'_confirm')/'calls'/(call+'.json')).read_bytes()
                elif call in index:
                    archive, location = index[call][0]
                    raw = archive.read(location)
                else:
                    raw = (root/'reevaluation/new_calls'/(call+'.json')).read_bytes()
                response = json.loads(raw)
                assert response['call_id'] == call
                extracted = run_experiment.unpack(response)
                rc.occurs_in_spans = numeric_evidence.occurs_in_spans
                validated, errors = rc.validate_records(extracted, item[side])
                assert errors == row['claim_errors' if side == 'claim' else 'source_errors']
                rc.occurs_in_spans = extended.occurs_in_spans
                updated = rc.validate_records(extracted, item[side])
                if updated != (validated, errors):
                    changes.append([cohort, model, uid, side])
                examined[side] += 1
        rc.occurs_in_spans = numeric_evidence.occurs_in_spans
    return dict(regression_cases=regression_cases(), model_statement_rows=len(decisions), validations=dict(examined), changed_validations=changes)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('replication_root', type=Path)
    print(json.dumps(main(parser.parse_args().replication_root.resolve()), indent=2))
