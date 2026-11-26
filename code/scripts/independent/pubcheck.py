from pathlib import Path
from urllib.request import urlopen,Request
from urllib.parse import urlencode
import time,json
HERE=Path(__file__).resolve().parent
screen=json.loads((HERE/'screen.json').read_bytes());d=HERE/'pubmed';d.mkdir(exist_ok=True)
for tid in screen['selected']:
    f=d/(tid+'.json');term=f'{tid}[si] OR {tid}[tiab]'
    if f.exists(): continue
    url='https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?'+urlencode(dict(db='pubmed',term=term,retmode='json',retmax=10000))
    for attempt in range(3):
        try:
            with urlopen(Request(url,headers={'User-Agent':'RegistryEvidenceResearch/1.0'}),timeout=12) as response: obj=json.load(response)
            assert len(obj['esearchresult']['idlist'])==int(obj['esearchresult']['count']);f.write_text(json.dumps(obj),encoding='utf8');break
        except Exception:
            if attempt==2: raise
            time.sleep(0.8*(attempt+1))
    time.sleep(.36)
print('PMID screens',len(list(d.glob('*.json'))))
