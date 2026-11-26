"""Collect or verify the fixed second-pass controls using the local archived model versions."""
import argparse
import hashlib
import json
import time
import urllib.request
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def collect(folder, live):
    plan = json.loads((folder / 'protocol.json').read_bytes())
    data = (folder / 'inputs.jsonl').read_bytes()
    assert digest(data) == plan['inputs_sha256']
    assert digest(Path(__file__).read_bytes()) == plan['runner_sha256']
    calls = [json.loads(line) for line in data.splitlines()]
    assert len(calls) == len({(r['request']['model'], r['id']) for r in calls}) == 160
    cache = folder / 'responses'
    cache.mkdir(exist_ok=True)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    address = 'http://127.0.0.1:11434'
    if live:
        with opener.open(address + '/api/tags', timeout=15) as response:
            installed = {m['name']: m['digest'] for m in json.load(response)['models']}
        assert all(installed.get(model) == pin for model, pin in plan['models'].items())
    for i, call in enumerate(calls, 1):
        req = call['request']
        assert plan['models'][req['model']] == call['model_digest']
        key = digest(encode([call['model_digest'], req]))
        path = cache / (key + '.json')
        if not path.exists():
            if not live:
                raise FileNotFoundError(path)
            start = time.monotonic()
            msg = urllib.request.Request(address + '/api/chat', data=encode(req), headers={'Content-Type': 'application/json'})
            with opener.open(msg, timeout=180) as response:
                raw = json.load(response)
            record = {'key': key, 'model_digest':call['model_digest'], 'raw':raw, 'seconds':time.monotonic()-start}
            tmp = path.with_suffix('.tmp')
            tmp.write_bytes(encode(record))
            tmp.replace(path)
        stored = json.loads(path.read_bytes())
        assert stored['key'] == key and stored['model_digest'] == call['model_digest']
        if i % 20 == 0:
            print(i, '/', len(calls), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('folder', type=Path)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    collect(args.folder, args.run)
