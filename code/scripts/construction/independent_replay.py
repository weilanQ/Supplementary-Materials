"""Run the frozen independent split constructor on source snapshots and the regenerated screen."""
import json
from pathlib import Path
import shutil
import subprocess
import sys


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf8')


def build(work):
    """Prepare the historical layout without supplying the selected inputs or answer key."""
    src = work/'cohort_source'
    snap = work/'work/condition_resolution_20261120'
    evaluation = work/'outputs/paper_condition_audit_20261120/evaluation'
    confirms = work/'outputs/paper_requirements_20261120/confirmation'
    dest = work/'independent_built'
    for path in (evaluation, confirms, dest):
        path.mkdir(parents=True)
    read = lambda name: json.loads((src/name).read_bytes())
    write_json(snap/'pages/page000.json', {'studies': read('studies.json')})
    write_json(snap/'publication_result.json', {'keys': read('earlier_publications.json')})
    for trial, hits in read('candidate_publications.json').items():
        write_json(snap/'pubmed'/(trial+'.json'), {'result': {'esearchresult': {'idlist': hits}}})
    shutil.copyfile(src/'screen.jsonl', evaluation/'screen.jsonl')
    shutil.copyfile(src/'earlier_candidate_trials.jsonl', evaluation/'candidates.jsonl')
    shutil.copyfile(src/'linked_keys.json', confirms/'linked_keys.json')
    shutil.copytree(src/'helpers', snap/'runtime/experiment/code')
    shutil.copyfile(work/'independent/construct.py', dest/'construct.py')
    subprocess.run([sys.executable, '-B', str(dest/'construct.py'), str(work)], check=True)


if __name__ == '__main__':
    build(Path(sys.argv[1]).resolve())
