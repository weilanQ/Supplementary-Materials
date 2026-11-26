import collections, itertools, re, json, hashlib, zipfile, random, csv
from decimal import Decimal
from pathlib import Path
from collections import defaultdict, Counter
from itertools import combinations
from fields import *
from registry_builder import sha, distinct,make_claim
from hashlib import sha256
PREFIX="requirements-cohort-fixed-1/"
def hashed(text):return sha256(text.encode()).hexdigest()

def build(all_studies,pool,prior,idx):
    """Use the screened pool and prior publication keys to produce initial statements, keys and exclusions in frozen order."""
    org=set();pub=set()
    for tid in prior:
        _,o,r,_=meta(all_studies[tid]);org.update(o);pub.update(r);pub.update(idx.get(tid,[]))
    keys=('group','endpoint','unit','statistic','time','population','category','denominator'); questions=[];key=[];exclusions=[];trial_count=0
    for tid in sorted(pool,key=lambda t:hashed(PREFIX+t)):
        if trial_count==20:break
        study=all_studies[tid]; _,o,p,_=meta(study);p=set(p)|set(idx.get(tid,[]))
        if org&o or pub&p:exclusions.append([tid,'linked identifier or citation']);continue
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
                uid=hashed(PREFIX+pair+str(positive))[:16];questions.append(dict(id=uid,dataset='confirmation',evidence=ev,claim=claim));key.append(dict(id=uid,pair=pair,trial=tid,kind=kind,gold='consistent' if positive else 'mismatch',target=a,donor=b))
        org.update(o);pub.update(p);trial_count+=1
    return sorted(questions,key=lambda r:hashed(PREFIX+r['id'])),key,exclusions
