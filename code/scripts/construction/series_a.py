import collections, itertools, re, json, hashlib, zipfile, random, csv
from decimal import Decimal
from pathlib import Path
from collections import defaultdict, Counter
from itertools import combinations
from fields import *
from registry_builder import sha, distinct,make_claim
def meta(s):
 p=s.get('protocolSection',{}); ident=p.get('identificationModule',{}); tid=ident.get('nctId',''); keys={tid.lower()};
 for v in [ident.get('orgStudyIdInfo',{})]+ident.get('secondaryIdInfos',[]):
  if v.get('id'):keys.add('id:'+re.sub(r'\W','',v['id'].lower()))
 for o in p.get('referencesModule',{}).get('references',[]):
  if o.get('pmid'):keys.add('pmid:'+str(o['pmid']))
 return tid,keys

def build(fresh,oldkey):
    """Select trial pairs in fixed hash order, excluding prior trial/publication keys; return statements and source pointers."""
    take=[];audit=[];used=set(oldkey); reasons=[]; allpairs=[]
    for study in sorted(fresh,key=lambda s:sha('confirmation-20261118'+meta(s)[0])):
     if len(take)==20:break
     tid,keys=meta(study)
     if keys&used:reasons.append([tid,'shared_identifier_or_reference']);continue
     outs=study.get('resultsSection',{}).get('outcomeMeasuresModule',{}).get('outcomeMeasures',[]); pool=[r for i,o in enumerate(outs) if o.get('paramType') in ('MEAN','MEDIAN','NUMBER','COUNT_OF_PARTICIPANTS') and o.get('timeFrame') and o.get('unitOfMeasure') and len(o.get('title',''))<=180 for r in records(o,i) if r['group'] and len(r['group'])<=150 and re.fullmatch(r'\d+(?:\.\d+)?',r['value'])]; idf=('group','endpoint','statistic','unit','time','population','denominator','category'); vals=collections.defaultdict(set)
     for r in pool:vals[tuple(r[k].casefold() for k in idf)].add(Decimal(r['value']))
     candidates=[];evcache={}
     for a,b in itertools.permutations(pool,2):
      if a['outcome_index']!=b['outcome_index'] and a['group']!=b['group']:continue
      if a['unit']!=b['unit'] or a['statistic']!=b['statistic'] or not distinct(a['value'],b['value']):continue
      different={k for k in idf if a[k].casefold()!=b[k].casefold()};
      if different and different.issubset({'category','denominator','time'}) and all(a[k] and b[k] for k in different):typ='condition'
      elif different in ({'group'},{'group','denominator'}) and a['outcome_index']==b['outcome_index']:typ='group'
      elif different=={'endpoint'}:typ='endpoint'
      else:continue
      if len(vals[tuple(a[k].casefold() for k in idf)])!=1:continue
      ix=tuple(sorted({a['outcome_index'],b['outcome_index']}));
      if ix not in evcache:evcache[ix]=render(outs,ix)
      if len(evcache[ix])>14000:continue
      candidates.append((typ,sha('choose'+a['json_pointer']+b['json_pointer']),a,b,ix))
     sel=[];targets=set()
     for tp in ['condition','group','endpoint','any']:
      for typ,_,a,b,ix in sorted(candidates,key=lambda v:v[1]):
       if (tp=='any' or tp==typ) and a['json_pointer'] not in targets:sel.append((typ,a,b,ix));targets.add(a['json_pointer']);break
      if len(sel)==2:break
     if len(sel)<2:reasons.append([tid,'fewer_than_two_eligible_pairs']);continue
     for j,(typ,a,b,ix) in enumerate(sel):
      pair=tid+'-C'+str(j+1);ev=evcache[ix];audit.append(dict(pair=pair,trial=tid,target=a,donor=b,type=typ));
      for pos,v in [(True,a['value']),(False,b['value'])]:
       c=make_claim(a,v,j); allpairs.append(dict(id=sha(pair+str(pos))[:16],dataset='confirmation',source_group=tid,pair_id=pair,claim=c,evidence=ev,gold='consistent' if pos else 'mismatch',error_type=typ,evidence_sha256=sha(ev)))
     take.append(tid);used|=keys
    return allpairs, audit
