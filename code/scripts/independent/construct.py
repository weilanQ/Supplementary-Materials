"""Construct the fresh trial split using the archived November registry snapshot and original pairing rules.
Optional construction entry: supply the project directory (including archived sources) as argument.
The cohort, selected registry snapshots, source pointers and frozen inputs are distributed for offline scoring.
"""
from pathlib import Path
from collections import defaultdict
from decimal import Decimal
from hashlib import sha256
import itertools,json,re,sys,os
DEST=Path(__file__).resolve().parent
PREFIX='independent-trial-evaluation-20261122/'
def hashed(text):return sha256(text.encode()).hexdigest()
def emit(path,records):path.write_bytes(b''.join((json.dumps(r,ensure_ascii=False)+'\n').encode() for r in records))
def read(path):return [json.loads(l) for l in path.read_bytes().splitlines()]
# Reader note: repo supplies screening decisions, registries and exclusion lists. Write selected trials, paired claims and the separate answer key.
def build(repo):
    snapshot=repo/'work/condition_resolution_20261120'; runtime=snapshot/'runtime'; prior_dir=repo/'outputs/paper_condition_audit_20261120/evaluation'
    sys.path[:0]=[str(runtime/s) for s in ('experiment/code','archive_inputs/code','tools')];os.environ['TRIAL_V3_ROOT']=str(runtime/'archive_inputs')
    from additional import meta
    from audit import fetch
    from prepare import records,render
    from scope_v2 import scope
    from build_data import distinct
    all_studies={meta(s)[0]:s for page in sorted((snapshot/'pages').glob('*.json')) for s in json.loads(page.read_bytes())['studies']}
    prior=json.loads((snapshot/'publication_result.json').read_bytes())['keys']; earlier=set(prior); assert len(earlier)==168
    previous_candidates={x['trial'] for x in read(prior_dir/'candidates.jsonl')}
    eligible={t for t,why in read(prior_dir/'screen.jsonl') if why=='screened'};pool=eligible-earlier-previous_candidates
    index=json.loads((repo/'outputs/paper_requirements_20261120/confirmation/linked_keys.json').read_bytes())
    org=set().union(*(meta(all_studies[t])[1] for t in earlier|previous_candidates if t in all_studies));pub=set().union(*(set(v) for v in prior.values()));
    for t in previous_candidates:pub.update(index.get(t,[]));pub.update(meta(all_studies[t])[2] if t in all_studies else [])
    keys=('group','endpoint','unit','statistic','time','population','category','denominator')
    key=[];questions=[];exclusions=[];trial_count=0;selected=[];used_keys={};frozen_prior=sorted(pub)
    # Reader note: Hash ordering fixes candidate order before any model verdicts. Exclude linked studies before constructing pairs.
    for tid in sorted(pool,key=lambda t:hashed(PREFIX+t)):
        if trial_count==20:break
        study=all_studies[tid];_,o,p,_=meta(study);p=set(p)|set(index.get(tid,[]));cached=snapshot/'pubmed'/(tid+'.json')
        if cached.exists():p.update('pmid:'+v for v in json.loads(cached.read_bytes())['result']['esearchresult']['idlist'])
        if org&o or pub&p:exclusions.append([tid,'linked identifier or publication']);continue
        outs=study.get('resultsSection',{}).get('outcomeMeasuresModule',{}).get('outcomeMeasures',[]); val=defaultdict(set); all_rows=[]; spans={}
        for i,out in enumerate(outs):
            rr=list(records(out,i));ev=render(outs,{i}).split('\n'); den=[j for j,l in enumerate(ev) if l.startswith('Denominator: ')];assert len(rr)==len(den)
            for r,j in zip(rr,den):
                r['denominator']=scope(out,r)[0];ev[j]='Denominator: '+r['denominator'];val[tuple(r[k].strip().casefold() for k in keys)].add(r['value'])
                if r['statistic'] not in ('NUMBER','MEAN','MEDIAN','COUNT_OF_PARTICIPANTS') or not all(r[k] for k in ('group','endpoint','unit','time')):continue
                if not re.fullmatch(r'\d+(?:\.\d+)?',r['value']) or len(r['endpoint'])>150 or len(r['group'])>140:continue
                if re.search(r'duration of response|percentile|quartile|positron emission|ROC curve',r['endpoint']+' '+r['category'],re.I):continue
                all_rows.append(r)
            spans[i]='\n'.join(ev)
        if len(all_rows)>900:exclusions.append([tid,'large table']);continue
        cand=[]
        for a,b in itertools.permutations(all_rows,2):
            field={k for k in keys if a[k].strip().casefold()!=b[k].strip().casefold()}; ia,ib=a['outcome_index'],b['outcome_index']
            if field in ({'group'},{'group','denominator'}) and ia==ib:kind='group'
            elif field=={'endpoint'}:kind='endpoint'
            elif field=={'category'} and a['category'] and b['category'] and ia==ib:kind='category'
            elif field=={'time'} and a['time'] and b['time']:kind='time'
            else:continue
            if not distinct(a['value'],b['value']) or any(len(val[tuple(r[k].strip().casefold() for k in keys)])!=1 for r in [a,b]):continue
            if not re.fullmatch(r'Participants: [1-9]\d*',a['denominator']) or not re.fullmatch(r'Participants: [1-9]\d*',b['denominator']):continue
            if a['unit'].strip().casefold() in ('participants','participant','subjects','patients') and max(Decimal(a['value']),Decimal(b['value']))>int(a['denominator'].split(':')[1]):continue
            evidence='\n\n'.join(spans[j] for j in sorted({ia,ib}));
            if len(evidence)>9000:continue
            cand.append((hashed(PREFIX+tid+a['json_pointer']+b['json_pointer']),kind,a,b,evidence))
        ordered=sorted(cand,key=lambda z:z[0]);picked=[];used=set()
        for k in ('endpoint','group','time','category','any'):
            for v in ordered:
                if k!='any' and v[1]!=k:continue
                pts={v[2]['json_pointer'],v[3]['json_pointer']}
                if used&pts:continue
                picked.append(v);used.update(pts);break
            if len(picked)==2:break
        if len(picked)<2:exclusions.append([tid,'fewer than two disjoint eligible pairs']);continue
        for j,(_,kind,a,b,ev) in enumerate(picked):
            pair=f'{tid}-C{j+1}';assert str(fetch(a['json_pointer'],study))==a['value'] and str(fetch(b['json_pointer'],study))==b['value']
            for positive in (False,True):
                value=a['value'] if positive else b['value'];parts=[f"time frame: {a['time']}",f"denominator: {a['denominator']}"]+([f"population: {a['population']}"] if a['population'] else [])+([f"category: {a['category']}"] if a['category'] else []);conditions='; '.join(parts)
                claim=(f"For {a['group']}, the reported {a['statistic']} for {a['endpoint']} was {value} {a['unit']} ({conditions})." if j==0 else f"The table gives {value} {a['unit']} as the {a['statistic']} for {a['endpoint']} in {a['group']} ({conditions}).")
                uid=hashed(PREFIX+pair+str(positive))[:16];questions.append(dict(id=uid,dataset='independent',evidence=ev,claim=claim));key.append(dict(id=uid,pair=pair,trial=tid,kind=kind,gold='consistent' if positive else 'mismatch',target=a,donor=b))
        org.update(o);pub.update(p);trial_count+=1

        selected.append(tid);used_keys[tid]=sorted(p)
    emit(DEST/'inputs.jsonl',sorted(questions,key=lambda r:hashed(PREFIX+r['id'])));emit(DEST/'key.jsonl',key);emit(DEST/'exclusions.jsonl',exclusions)
    assert len(set(selected))==trial_count and len(key)==trial_count*4
    (DEST/'registry').mkdir(exist_ok=True)
    for t in selected:(DEST/'registry'/(t+'.json')).write_text(json.dumps(all_studies[t],ensure_ascii=False),encoding='utf8')
    (DEST/'screen.json').write_text(json.dumps(dict(pool=len(pool),prior_trials=sorted(earlier),prior_candidate_trials=sorted(previous_candidates),prior_known_links=frozen_prior,selected=selected,selected_links=used_keys),indent=2),encoding='utf8');print('trials',trial_count,'statements',len(key),'available',len(pool),flush=True)
if __name__=='__main__':build(Path(sys.argv[1]).resolve())

