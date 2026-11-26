import collections, itertools, re, json, hashlib, zipfile, random, csv
from decimal import Decimal
from pathlib import Path
from collections import defaultdict, Counter
from itertools import combinations
from fields import *
from registry_builder import sha, distinct,make_claim

def build(pool, seen, other, linked, idx, pub):
    """Build the publication-linked series from registry candidates; return paired statements and an audit key."""
    for t in seen:linked|=idx[t]
    checks=[];vs=[];audit=[];cases=[];ids0=seen.copy();ref0=linked.copy();org0=other.copy()
    for s in sorted(pool,key=lambda s:sha('v2-confirm-scope-20261118'+meta(s)[0])):
     if len(cases)==20:break
     t,o,refs,res=meta(s);refs|=idx[t];res|=pub[t];reason='';conds=s['protocolSection'].get('conditionsModule',{}).get('conditions',[]);pan=re.search(r'(?:pancrea\w*[^;]{0,38}(?:cancer|adenocarcinoma|carcinoma|neoplasm|malignan)|(?:cancer|adenocarcinoma|carcinoma|malignan)[^;]{0,38}pancrea)', ';'.join(conds),re.I)
     if t in seen:reason='known trial'
     elif o&other:reason='shared study identifier'
     elif not res:reason='no identified result/derived link'
     elif refs&linked:reason='shared publication key'
     elif not pan:reason='no explicit pancreatic malignancy condition'
     if reason:checks.append([t,reason]);continue
     outs=s.get('resultsSection',{}).get('outcomeMeasuresModule',{}).get('outcomeMeasures',[]);poolr=[];fields=['group','endpoint','statistic','unit','time','population','category','denominator']; allv=defaultdict(set)
     for i,out in enumerate(outs):
      if out.get('paramType') not in ('MEAN','MEDIAN','NUMBER','COUNT_OF_PARTICIPANTS') or not out.get('timeFrame') or not out.get('unitOfMeasure') or len(out.get('title',''))>180:continue
      if len(render(outs,{i}))>14000:continue
      for r in records(out,i):
       r['denominator'],method=scope(out,r);r['scope_rule']=method;r['idt']=tuple(r[k].casefold() for k in fields); rawv=r['value'];allv[r['idt']].add(rawv)
       if r['group'] and len(r['group'])<=150 and re.fullmatch(r'\d+(?:\.\d+)?',rawv):poolr.append(r)
     cand=[];evmap={}
     for a,b in itertools.permutations(poolr,2):
      if a['json_pointer']==b['json_pointer'] or len(allv[a['idt']])!=1 or a['unit']!=b['unit'] or a['statistic']!=b['statistic'] or not distinct(a['value'],b['value']):continue
      different={k for k in fields if a[k].casefold()!=b[k].casefold()};
      if different and different<={'category','denominator','time'} and all(a[k] and b[k] for k in different):tp='condition'
      elif different in ({'group'},{'group','denominator'}) and a['outcome_index']==b['outcome_index']:tp='group'
      elif different=={'endpoint'}:tp='endpoint'
      else:continue
      den=re.search(r'(?:category n: |Participants: )(\d+)',a['denominator'],re.I)
      if den and a['unit'].strip().lower() in ('participant','participants','patients','subjects') and max(Decimal(a['value']),Decimal(b['value']))>int(den[1]):continue
      ix=tuple(sorted({a['outcome_index'],b['outcome_index']}));
      if ix not in evmap:
       ls=render(outs,ix).split('\n'); rr=[r for i in ix for r in records(outs[i],i)];denlines=[j for j,l in enumerate(ls) if l.startswith('Denominator: ')];assert len(denlines)==len(rr)
       for j,r in zip(denlines,rr):ls[j]='Denominator: '+scope(outs[r['outcome_index']],r)[0]
       evmap[ix]='\n'.join(ls)
      if len(evmap[ix])>14000:continue
      cand.append((tp,sha('scope-fresh-pair'+a['json_pointer']+'/'+b['json_pointer']),a,b,ix))
     cand.sort(key=lambda c:c[1]);picked=[];used=set()
     for tp in ('condition','group','endpoint','any'):
      for k in cand:
       if (tp=='any' or k[0]==tp) and k[2]['json_pointer'] not in used:picked.append(k);used.add(k[2]['json_pointer']);break
      if len(picked)==2:break
     if len(picked)<2:checks.append([t,'fewer than two pairs']);continue
     for j,(tp,_,a,b,ix) in enumerate(picked):
      pair=t+'-H'+str(j+1);audit.append(dict(pair=pair,trial=t,target=a,donor=b,type=tp));assert str(fetch(a['json_pointer'],s))==a['value'] and str(fetch(b['json_pointer'],s))==b['value']
      for positive in (True,False):
       claim=make_claim(a,a['value'] if positive else b['value'],j);decoded=claim_parse(claim);assert all(' '.join(decoded[k].split()).casefold()==' '.join(a[k].split()).casefold() for k in fields);assert (Decimal(decoded['value'])==Decimal(a['value']))==positive;vs.append(dict(id=sha(pair+str(positive))[:16],source_group=t,pair_id=pair,dataset='fresh_holdout',error_type=tp,evidence=evmap[ix],claim=claim,gold='consistent' if positive else 'mismatch'))
     cases.append(dict(trial=t,org=sorted(o),all_linked_keys=sorted(refs),result_or_derived_keys=sorted(res),conditions=conds));seen.add(t);linked|=refs;other|=o
    return vs,audit
