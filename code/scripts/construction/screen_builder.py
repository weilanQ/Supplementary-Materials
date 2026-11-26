import collections, itertools, re, json, hashlib, zipfile, random, csv
from decimal import Decimal
from pathlib import Path
from collections import defaultdict, Counter
from itertools import combinations
from fields import *
from registry_builder import sha, distinct,make_claim
from registry_builder import sha as digest
FIELDS=('group','endpoint','statistic','unit','population','category','denominator','time')
normalize=lambda v:' '.join(v.casefold().split())
def visit(s):return bool(re.fullmatch(r'(?:at |after )?(?:baseline|(?:day|week|month|year|cycle)s?\s*\d+|\d+\s*[- ]?\s*(?:days?|weeks?|months?|years?)(?: post[- ](?:treatment|dose))?)',s,re.I))

def build(ds,ids,org,refs,index):
    """Return one decision per registry study and the eligible contrasts, using prior trial, study and publication identifiers."""
    disp=[];cand=[]
    for s in sorted(ds,key=lambda s:digest('scope-v3'+meta(s)[0])):
        trial,secondary,linked,_=meta(s);conds=';'.join(s['protocolSection'].get('conditionsModule',{}).get('conditions',[]));reason= 'previous_trial' if trial in ids else 'previous_secondary' if secondary&org else 'shared_reference' if (linked|index[trial])&refs else 'indication' if not re.search(r'pancrea\w*[^;]{0,40}(?:cancer|neoplasm|carcinoma|malignan)|(?:cancer|neoplasm|carcinoma|malignan)[^;]{0,40}pancrea',conds,re.I) else 'screened';disp.append([trial,reason]);
        if reason!='screened':continue
        outs=s.get('resultsSection',{}).get('outcomeMeasuresModule',{}).get('outcomeMeasures',[]);entries=[];allrows=defaultdict(list)
        for i,o in enumerate(outs):
            for r in records(o,i):
                r['denominator']=scope(o,r)[0]; ident=tuple(normalize(r[k]) for k in FIELDS);allrows[ident].append(r);entries.append((i,r,ident))
        def add(kind,a,b):
            a,b=sorted([a,b],key=lambda r:digest('orientation-v1'+trial+r['json_pointer'])); ix={a['outcome_index'],b['outcome_index']};ev=evidence(outs,ix)
            if len(ev)>14000:return
            key=digest('scope-v3'+kind+trial+a['json_pointer']+b['json_pointer']);cand.append(dict(key=key,kind=kind,trial=trial,target=a,donor=b,evidence=ev,descriptions=[outs[r['outcome_index']].get('description','') for r in (a,b)],linked=sorted(linked|index[trial]),secondary=sorted(secondary)))
        valid=[(i,r,key) for i,r,key in entries if r['statistic'] in ('NUMBER','MEAN','MEDIAN','COUNT_OF_PARTICIPANTS') and all(r[k] for k in ('group','endpoint','unit','time')) and re.fullmatch(r'\d+(?:\.\d+)?',r['value']) and len(allrows[key])==1];
        for fld,kind in [('time','time'),('category','time_category'),('denominator','denominator'),('group','denominator_claim')]:
            omit={fld} if kind!='denominator_claim' else {'group','denominator'}; buckets=defaultdict(list)
            for i,r,key in valid:buckets[tuple(key[j] for j,k in enumerate(FIELDS) if k not in omit)].append((i,r))
            for bucket in buckets.values():
                for (i,a),(j,b) in combinations(bucket,2):
                    if not a[fld] or not b[fld] or normalize(a[fld])==normalize(b[fld]):continue
                    if kind!='denominator_claim' and not distinct(a['value'],b['value']):continue
                    if kind=='time_category' and (i!=j or not (visit(a[fld]) and visit(b[fld]))):continue
                    if kind in ('denominator','denominator_claim'):
                        if not all(re.fullmatch(r'Participants: [1-9]\d*',r['denominator'],re.I) for r in (a,b)) or a['denominator']==b['denominator']:continue
                        if kind=='denominator_claim' and (i!=j or a['category'] or a['population'] or len({v['group'] for oi,v,k in entries if oi==i})!=sum(oi==i for oi,v,k in entries)):continue
                        low=min(int(r['denominator'].split(':')[1]) for r in (a,b));
                        if re.search(r'^(?:participants?|patients?|subjects?)$',a['unit'],re.I) and max(Decimal(a['value']),Decimal(b['value']))>low:continue
                    add(kind,a,b)
    return disp, sorted(cand,key=lambda x:x['key'])
