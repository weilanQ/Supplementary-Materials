from pathlib import Path
import json, hashlib, re, sys, os
HERE=Path(__file__).resolve().parent; EXP=HERE.parent; ROOT=EXP.parents[2]; BASE=Path(os.environ.get('TRIAL_V3_ROOT',ROOT/'work/pc11r2/workspace/outputs/research_v3')); OLD=BASE/'data'; DATA=EXP/'data'; RES=EXP/'results'
sys.path.append(str(BASE/'code'))
load=lambda p:json.loads(p.read_text(encoding='utf8'))
rows=lambda p:[json.loads(l) for l in p.read_text(encoding='utf8').splitlines() if l.strip()]
sha=lambda s:hashlib.sha256(s.encode()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=1),encoding='utf8')
def jsonl(p,x):p.write_text(''.join(json.dumps(v,ensure_ascii=False)+'\n' for v in x),encoding='utf8')
