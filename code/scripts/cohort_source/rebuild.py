"""Rebuild the independent cohort from the archived screen with the frozen constructor."""
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'cohort_source'
FROZEN = ROOT / 'independent'


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding='utf8')


def read(path):
    return json.loads(path.read_bytes())


def verify():
    for name, digest in read(SOURCE / 'checksums.json').items():
        assert hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() == digest, name
    digest = read(FROZEN / 'freeze.json')['hashes']['independent/construct.py']
    assert hashlib.sha256((FROZEN / 'construct.py').read_bytes()).hexdigest() == digest
    with TemporaryDirectory() as temp:
        repo = Path(temp)
        snapshot = repo / 'work/condition_resolution_20261120'
        evaluation = repo / 'outputs/paper_condition_audit_20261120/evaluation'
        confirms = repo / 'outputs/paper_requirements_20261120/confirmation'
        generated = repo / 'regenerated'
        for directory in (evaluation, confirms, generated):
            directory.mkdir(parents=True)
        write_json(snapshot / 'pages/page000.json', {'studies': read(SOURCE / 'studies.json')})
        write_json(snapshot / 'publication_result.json', {'keys': read(SOURCE / 'earlier_publications.json')})
        for tid, pmids in read(SOURCE / 'candidate_publications.json').items():
            write_json(snapshot / 'pubmed' / (tid + '.json'), {'result': {'esearchresult': {'idlist': pmids}}})
        shutil.copyfile(SOURCE / 'screen.jsonl', evaluation / 'screen.jsonl')
        shutil.copyfile(SOURCE / 'earlier_candidate_trials.jsonl', evaluation / 'candidates.jsonl')
        shutil.copyfile(SOURCE / 'linked_keys.json', confirms / 'linked_keys.json')
        shutil.copytree(SOURCE / 'helpers', snapshot / 'runtime/experiment/code')
        shutil.copyfile(FROZEN / 'construct.py', generated / 'construct.py')
        subprocess.run([sys.executable, '-B', str(generated / 'construct.py'), str(repo)], check=True)
        for name in ('inputs.jsonl', 'key.jsonl', 'exclusions.jsonl'):
            assert (generated / name).read_bytes() == (FROZEN / name).read_bytes(), name
        screen = read(generated / 'screen.json')
        assert screen['pool'] == 78 and len(screen['selected']) == 20
        frozen_screen = read(FROZEN / 'screen.json')
        assert all(value == frozen_screen[key] for key, value in screen.items())
        assert set(frozen_screen) == set(screen) | {'n_selected_with_known_publication'}
        checked_publications = {}
        used_links = set(screen['prior_known_links'])
        for tid in screen['selected']:
            name = f'registry/{tid}.json'
            assert (generated / name).read_bytes() == (FROZEN / name).read_bytes(), name
            hits = read(FROZEN / 'pubmed' / f'{tid}.json')['esearchresult']
            assert int(hits['count']) == len(hits['idlist'])
            links = set(screen['selected_links'][tid]) | {'pmid:' + x for x in hits['idlist']}
            assert not used_links.intersection(links), tid
            used_links.update(links)
            checked_publications[tid] = sorted(links)
        assert sum(bool(v) for v in checked_publications.values()) == frozen_screen['n_selected_with_known_publication']
        scored = ROOT / 'results/independent_source_audit.json'
        if scored.is_file():
            assert checked_publications == read(scored)['trial_links']
    print('Verified 20 trial IDs, 20 registry snapshots, 40 pairs, 80 statement inputs and keys, exclusions and publication links.')


if __name__ == '__main__':
    verify()
