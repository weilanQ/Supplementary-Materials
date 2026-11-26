import copy
import json
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARTIFACT = HERE.parent
sys.path.insert(0, str(ARTIFACT))
from reproduce import MODELS, byid, dump, get, read, request, sha


def verify():
    manifest = get(HERE / 'freeze.json')
    for path, digest in manifest['hashes'].items():
        assert sha(ARTIFACT / path) == digest, path


def direct(item, model):
    req = copy.deepcopy(get(HERE / 'direct_request.json'))
    req['model'] = model
    block = req['messages'][0]['content']
    req['messages'][0]['content'] = block.replace('<<TRIAL_TEXT>>', item['evidence']).replace('<<STATEMENT>>', item['claim'])
    return req


def api(route, payload=None):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request('http://127.0.0.1:11434/api/' + route, data=data, headers={'Content-Type':'application/json'})
    with opener.open(req, timeout=240) as response:
        return json.load(response)


def run(dest):
    verify()
    dest.mkdir(parents=True, exist_ok=True)
    pins = get(ARTIFACT / 'pins.json')
    tags = {m['name']:m['digest'] for m in api('tags')['models']}
    version = api('version')['version']
    assert version == '0.40.17' and all(tags[m] == pins[m] for m in MODELS)
    for model in MODELS:
        name = model.replace(':', '_')
        for item in read(HERE / 'inputs.jsonl'):
            for method, prompt in [('direct',direct),('select',request)]:
                path = dest / f"{name}_{method}_{item['id']}.json"
                req = prompt(item,model)
                if path.exists():
                    rec = get(path)
                    assert rec['request']==req and rec['digest']==pins[model]
                    continue
                start = time.perf_counter()
                raw = api('chat',req)
                assert raw['model']==model
                receipt = dict(id=item['id'],model=model,method=method,service=version,digest=pins[model],request=req,raw=raw,seconds=time.perf_counter()-start)
                tmp = path.with_suffix('.tmp')
                dump(tmp,receipt)
                tmp.replace(path)
                n = len(list(dest.glob('*.json')))
                if n%40==0: print('Saved',n,'of 320',flush=True)

if __name__=='__main__': run(Path(sys.argv[1]).resolve())
