import collections, itertools, re, json, hashlib, zipfile, random, csv
from decimal import Decimal
from pathlib import Path
from collections import defaultdict, Counter
from itertools import combinations
from fields import *
from registry_builder import sha, distinct,make_claim
from rules import source_table
normalize=lambda x: " ".join(x.casefold().split())
def build(studies,elig,allkeys,oldpub,oldorg):
    """Select condition changes from eligible trials, excluding earlier publications and organizations; return inputs and keys."""
    norm=normalize
    candidates=[]
    identity="group endpoint unit statistic time population category denominator".split()
    for tid in sorted(elig):
     if tid not in studies:continue
     s=studies[tid]; outs=s.get('resultsSection',{}).get('outcomeMeasuresModule',{}).get('outcomeMeasures',[]); rr=[];seen=defaultdict(set); tablecache={}
     for oi,o in enumerate(outs):
      for a in records(o,oi):
       a['denominator']=scope(o,a)[0]; sig=tuple(norm(a[k]) for k in identity);seen[sig].add(a['value']);rr.append((sig,a))
     def gettable(i):
      if i not in tablecache:
       o=outs[i];txt=render(outs,{i}); ls=txt.splitlines(); indices=[k for k,l in enumerate(ls) if l.startswith('Denominator: ')];rs=list(records(o,i));assert len(indices)==len(rs)
       for k,x in zip(indices,rs):ls[k]='Denominator: '+scope(o,x)[0]
       tablecache[i]='\n'.join(ls)
      return tablecache[i]
     def add(kind,a,b):
      ind=sorted({a['outcome_index'],b['outcome_index']});e='\n\n'.join(gettable(i) for i in ind)
      if kind=='scoped denominator':
       total=a['levels']['outcome'];e=e.replace('Statistic: ',f'Outcome-level participant count for {a["group"]}: {total}\nStatistic: ',1)
      if len(e)>14000 or not source_table(e)['complete']:return
      k=sha('conditions-20261120'+kind+tid+a['json_pointer']+b['json_pointer']);candidates.append(dict(key=k,trial=tid,kind=kind,target=a,donor=b,evidence=e))
     valid=[]
     for sig,a in rr:
      if len(seen[sig])!=1 or not re.fullmatch(r'Participants: [1-9]\d*',a['denominator']) or not re.fullmatch(r'\d+(?:\.\d+)?',a['value']) or a['statistic'] not in ('NUMBER','MEAN','MEDIAN','COUNT_OF_PARTICIPANTS') or not all(a[k] for k in ('group','endpoint','time','unit')):continue
      if re.search(r'quartile|percentile|duration of response|positron emission|ROC curve',a['endpoint']+' '+a['category'],re.I):continue
      valid.append(a)
      if a['level'] in ('class','category') and re.fullmatch(r'Participants: [1-9]\d*',a['levels']['outcome']) and int(a['levels']['outcome'].split()[-1])>int(a['denominator'].split()[-1]) and a['category']:
       if a['unit'].lower() in ('participants','patients','subjects') and Decimal(a['value'])>int(a['denominator'].split()[-1]):continue
       alt=dict(a,denominator=a['levels']['outcome']);add('scoped denominator',a,alt)
     for field in ('denominator','time','category'):
      bs=defaultdict(list)
      for a in valid:bs[tuple(norm(a[k]) for k in identity if k!=field)].append(a)
      for bucket in bs.values():
       for a,b in combinations(bucket,2):
        if field=='category' and (a['outcome_index']!=b['outcome_index'] or not all(re.fullmatch(r'(?:at |after )?(?:baseline|(?:day|week|month|year|cycle)s?\s*\d+|\d+[- ]*(?:days?|weeks?|months?|years?)(?: post[- ](?:treatment|dose))?)',x['category'],re.I) for x in (a,b))):continue
        if not distinct(a['value'],b['value']) or norm(a[field])==norm(b[field]):continue
        oa,ob=[outs[x['outcome_index']] for x in (a,b)];fields=['description','unitOfMeasure','type','analyzedUnits','denomUnitsSelected'];
        if any(oa.get(k)!=ob.get(k) for k in fields):continue
        groupdesc=lambda o,x:[g.get('description','') for g in o['groups'] if g['title']==x['group']];
        if groupdesc(oa,a)!=groupdesc(ob,b):continue
        if a['unit'].lower() in ('participants','patients','subjects') and max(map(Decimal,[a['value'],b['value']]))>min(int(x['denominator'].split()[-1]) for x in (a,b)):continue
        if field=='time' and not all(re.search(r'\b(day|week|month|year|cycle|baseline|hours?|minutes?)s?\b',x['time'],re.I) for x in (a,b)):continue
        add('visit' if field=='category' else field,a,b)
    candidates.sort(key=lambda x:x['key'])
    picked=[];samples=[];labels=[];used=set();usedpub=set(oldpub);usedorg=set(oldorg)
    for kind in ('denominator','time','visit','scoped denominator'):
     for x in [v for v in candidates if v['kind']==kind]:
      tid=x['trial'];a=x['target'];b=x['donor']; org=meta(studies[tid])[1]; links=allkeys[tid]
      if tid in used or org&usedorg or links&usedpub:continue
      if sum(y['kind']==kind for y in picked)>=4:break
      # Preserve two source pointers and independently re-read target/donor values.
      for record in ([a] if kind=='scoped denominator' else [a,b]):
       assert str(fetch(record['json_pointer'],studies[tid]))==record['value']
      used.add(tid);usedorg.update(org);usedpub.update(links);picked.append(x)
      for ix,label in enumerate(('consistent','mismatch')):
       qr=b if ix and kind=='scoped denominator' else a; val=b['value'] if ix else a['value'];claim=make_claim(qr,val,(len(picked)-1)%2); ident=sha(tid+x['key']+claim)[:16];samples.append(dict(dataset='additional_conditions',id=ident,evidence=x['evidence'],claim=claim));labels.append(dict(id=ident,trial=tid,kind=kind,pair=x['key'],gold=label,target=a['json_pointer'],donor=b['json_pointer']))

    return samples,labels
