"""Run the paper's scoring and construction checks from the distributed file layout."""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import NamedTemporaryFile, TemporaryDirectory

ROOT = Path(__file__).resolve().parent
HISTORICAL = {
    'data/confirmation.jsonl': 'main_inputs', 'historical/key.jsonl': 'main_key',
    'data/dev.jsonl': 'development_inputs', 'data/dev_key.jsonl': 'development_key',
    'historical/public.jsonl': 'public', 'historical/series_b.jsonl': 'series_b',
    'historical/condition_extension/confirm.jsonl': 'condition_inputs',
    'historical/condition_extension/key.jsonl': 'condition_key', 'cohort_source/screen.jsonl': 'screen',
}
INDEPENDENT = tuple('independent/' + n + '.jsonl' for n in ('inputs', 'key', 'exclusions'))


def publish(path, data):
    """Replace a verified derived file without exposing a partial write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        pending = Path(stream.name)
        stream.write(data)
    try:
        os.replace(pending, path)
    finally:
        pending.unlink(missing_ok=True)


def distributed_index(source, layout):
    """Translate frozen file references in the index to paths in the review archive."""
    reader = csv.DictReader(io.StringIO(source.decode('utf8')), delimiter='\t')
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=reader.fieldnames, delimiter='\t', lineterminator='\n')
    writer.writeheader()
    for row in reader:
        for col in ('input_file', 'reference_file', 'direct_reply', 'select_reply'):
            row[col] = layout[row[col]]
        writer.writerow(row)
    return output.getvalue().encode('utf8')


def construction_input(path, row):
    """Restore the archived newline convention; every other byte must already match."""
    data = path.read_bytes()
    for candidate in (data, data.replace(b'\n', b'\r\n')):
        if hashlib.sha256(candidate).hexdigest() == row['sha256_package'] == row['sha256_frozen']:
            return candidate
    raise ValueError('Regenerated file differs from the frozen input: ' + row['frozen_path'])


def replay(check_cohort, all_data=False):
    """Score archived replies against frozen or regenerated inputs in an isolated workspace."""
    with (ROOT / 'config/file_manifest.tsv').open(encoding='utf8', newline='') as stream:
        records = list(csv.DictReader(stream, delimiter='\t'))
    layout = {row['frozen_path']: row['package_path'] for row in records}
    generated = [key for key in layout if key.startswith('results/')]
    index = 'guide/evaluation_index.tsv'
    with TemporaryDirectory(prefix='r_', dir=ROOT) as workdir:
        # Frozen scripts use their original relative paths. Copies isolate the source records.
        work = Path(workdir)
        reconstructed = work / 'source_rebuild'
        constructors = ROOT / 'code/scripts/construction'
        if all_data:
            for name, expected in json.loads((ROOT/'config/construction_sources.json').read_bytes()).items():
                if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != expected:
                    raise ValueError('Construction dependency differs from the release: ' + name)
            subprocess.run([sys.executable, '-B', str(constructors/'rebuild.py'), str(reconstructed)], check=True)
        for row in records:
            key = row['frozen_path']
            if key in generated or key == index or (all_data and key in INDEPENDENT):
                continue
            if all_data and key in HISTORICAL:
                data = construction_input(reconstructed/(HISTORICAL[key]+'.jsonl'), row)
            else:
                data = (ROOT / row['package_path']).read_bytes()
            if hashlib.sha256(data).hexdigest() != row['sha256_package']:
                raise ValueError('Distributed file differs from the manifest: ' + row['package_path'])
            if key.endswith('.py') and row['sha256_package'] != row['sha256_frozen']:
                data = b''.join(line for line in data.splitlines(keepends=True)
                                if not line.lstrip().startswith(b'# Reader note: '))
            if hashlib.sha256(data).hexdigest() != row['sha256_frozen']:
                raise ValueError('File differs from the frozen release: ' + row['package_path'])
            dest = work / key
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        if all_data:
            subprocess.run([sys.executable, '-B', str(constructors/'independent_replay.py'), str(work)], check=True)
            for row in records:
                if row['frozen_path'] in INDEPENDENT:
                    (work/row['frozen_path']).write_bytes(construction_input(work/'independent_built'/Path(row['frozen_path']).name, row))
        for script in ['reproduce.py', 'guide/build_index.py'] + (['cohort_source/rebuild.py'] if check_cohort else []):
            subprocess.run([sys.executable, '-B', script], cwd=work, check=True)
        hashes = json.loads((ROOT / layout['expected.json']).read_bytes())
        if set(hashes) != {Path(k).name for k in generated}:
            raise ValueError('Result names differ from the frozen manifest')
        output = {layout[k]: (work/k).read_bytes() for k in generated}
        for key in generated:
            if hashlib.sha256(output[layout[key]].replace(b'\r\n', b'\n')).hexdigest() != hashes[Path(key).name]:
                raise ValueError('Result differs from the frozen release: ' + key)
        idx = (work/index).read_bytes()
        frozen_index = next(row['sha256_frozen'] for row in records if row['frozen_path']==index)
        if hashlib.sha256(idx).hexdigest() != frozen_index:
            raise ValueError('Statement index differs from the frozen predictions')
        output[layout[index]] = distributed_index(idx, layout)
        for path, data in output.items():
            publish(ROOT / path, data)
    print('Verified 25 result files and the 320-row statement index. See code/results/.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort', action='store_true', help='also reconstruct the independent cohort from the archived screen')
    parser.add_argument('--all-data', action='store_true', help='rebuild historical partitions and independent inputs before scoring archived replies')
    args = parser.parse_args()
    replay(args.cohort or args.all_data, args.all_data)
