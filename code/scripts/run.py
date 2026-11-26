from method import *
import urllib.request,time,datetime
repo=BASE.parents[1]; original=repo/'outputs/paper_requirements_20261120'; devfile=repo/'outputs/paper_revision_round2_20261118/experiment/data/registry_development.jsonl'
def prepare():
    all_dev=read(devfile); groups={}
    for row in sorted(all_dev,key=lambda x:sig('row-probe-v1|'+x['id'])):groups.setdefault(row['source_group'],row)
    assert len(groups)==20
    for name,records in [('dev',list(groups.values())),('confirmation',read(original/'confirmation/confirm.jsonl'))]:lines(BASE/f'data/{name}.jsonl',[{k:x[k] for k in ('id','claim','evidence')} for x in records]);
    lines(BASE/'data/dev_key.jsonl',[{'id':x['id'],'trial':x['source_group'],'gold':x['gold']} for x in groups.values()]);
    pins={m:json.loads((original/f'confirmation/runs/{m.replace(":","_")}_confirm/completed.json').read_bytes())['digest'] for m in MODELS};dump(BASE/'pins.json',pins)
    paths=[BASE/'method.py',BASE/'run.py',BASE/'pins.json',BASE/'data/dev.jsonl',BASE/'data/confirmation.jsonl',*sorted((BASE/'legacy').glob('*.py'))]; dump(BASE/'freeze.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'protocol':'One round on 20 development items then 80 archived confirmation items per model. Development selected by hash, one per trial. No parameter selection, no test-driven revisions. Stage priority: transport/JSON/schema, numerical validation, quotations, completeness, candidate decision. Only outer whitespace/BOM/one complete JSON fence may be removed in mechanical replay. Row selection uses every parsed row, in source order, with point values hidden; offline scorer accepts all identity- and condition-compatible row IDs. Unknown/no row leads to abstention; conflicting candidates and invalid lists abstain before aggregation. No new data independence claimed.','hashes':{str(p.relative_to(BASE)):sha(p) for p in paths}})
def execute():
    freeze=json.loads((BASE/'freeze.json').read_bytes());assert all(sha(BASE/k)==v for k,v in freeze['hashes'].items()); pins=json.loads((BASE/'pins.json').read_bytes()); opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));
    def api(endpoint,data=None):
        req=urllib.request.Request('http://127.0.0.1:11434/api/'+endpoint,data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json'});return json.load(opener.open(req,timeout=240))
    tags=api('tags')['models']; assert all(any(x['name']==m and x['digest']==pins[m] for x in tags) for m in MODELS); dump(BASE/'data/runtime.json',{'version':api('version'),'models':{m:api('show',{'model':m}) for m in MODELS}})
    for split in ('dev','confirmation'):
        for model in MODELS:
            for item in read(BASE/f'data/{split}.jsonl'):
                dest=BASE/'logs'/f'{split}_{model.replace(":","_")}_{item["id"]}.json'; req=request(item,model)
                if dest.exists():assert json.loads(dest.read_bytes())['request']==req;continue
                start=time.perf_counter(); raw=api('chat',req); elapsed=time.perf_counter()-start; temp=dest.with_suffix('.tmp');dump(temp,{'id':item['id'],'split':split,'model':model,'digest':pins[model],'request':req,'raw':raw,'seconds':elapsed});temp.replace(dest)
if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    else:execute()
