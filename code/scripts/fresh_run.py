"""Collect the frozen development and confirmation requests with a pinned local Ollama server."""
import sys, json, time, urllib.request
from pathlib import Path
from reproduce import BASE, MODELS, sha, get, read, request, PureWindowsPath

def main(dest):
    if dest.resolve()==(BASE/'logs').resolve(): raise ValueError('Choose a separate run directory')
    dest.mkdir(parents=True,exist_ok=True)
    pins=get(BASE/'pins.json'); hashes=get(BASE/'freeze.json')['hashes'];assert all(sha(BASE.joinpath(*PureWindowsPath(k).parts))==v for k,v in hashes.items());opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def api(route,payload=None):
        req=urllib.request.Request('http://127.0.0.1:11434/api/'+route,data=json.dumps(payload).encode() if payload else None,headers={'Content-Type':'application/json'});return json.load(opener.open(req,timeout=240))
    tags={x['name']:x['digest'] for x in api('tags')['models']};assert all(tags.get(m)==v for m,v in pins.items()); print('Ollama',api('version'))
    for split in ('dev','confirmation'):
        for model in MODELS:
            for item in read(BASE/f'data/{split}.jsonl'):
                uid=item['id'];req=request(item,model);out=dest/f'{split}_{model.replace(":","_")}_{uid}.json'
                if out.exists():
                    existing=get(out);assert existing['request']==req and existing['digest']==pins[model];continue
                start=time.perf_counter();raw=api('chat',req);rec=dict(id=uid,split=split,model=model,digest=pins[model],request=req,raw=raw,seconds=time.perf_counter()-start);temp=out.with_suffix('.tmp');temp.write_text(json.dumps(rec,ensure_ascii=False),encoding='utf8');temp.replace(out)
if __name__=='__main__':main(Path(sys.argv[1]))
