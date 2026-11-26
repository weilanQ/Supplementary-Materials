from registry_builder import norm,table_text,make_claim
import re
from decimal import Decimal
# Counts belong to a group and a table level. Callers retain both before rendering a denominator.
def den(obj,g):return '; '.join(f"{d.get('units','')}: {p['value']}" for d in obj.get('denoms',[]) for p in d.get('counts',[]) if p.get('groupId')==g)

def records(o,oi):
 gs={g['id']:g['title'] for g in o.get('groups',[])}
 for ci,c in enumerate(o.get('classes',[])):
  for ki,k in enumerate(c.get('categories',[])):
   for mi,m in enumerate(k.get('measurements',[])):
    gid=m['groupId']; by={t:den(v,gid) for t,v in [('outcome',o),('class',c),('category',k)]}; use=next((s for s in ('category','class','outcome') if by[s]),None)
    yield dict(group=gs.get(gid,gid),endpoint=o['title'],time=o.get('timeFrame',''),unit=o.get('unitOfMeasure',''),population=o.get('populationDescription',''),statistic=o.get('paramType',''),category=norm(c.get('title','')+'; '+k.get('title','')).strip('; '),denominator=by[use] if use else '',value=str(m.get('value','')),json_pointer=f'/resultsSection/outcomeMeasuresModule/outcomeMeasures/{oi}/classes/{ci}/categories/{ki}/measurements/{mi}/value',levels=by,level=use,outcome_index=oi)

def render(outs,indices):
 # Preserve unchanged headers, ordering, whitespace and individual rows exactly.
 old=table_text(outs,indices); iterrows=iter([r for i in sorted(indices) for r in records(outs[i],i)]); lines=[]
 for l in old.split('\n'):
  if l.startswith('Denominator: '):
   r=next(iterrows); assert l=='Denominator: '+r['levels']['outcome']; l='Denominator: '+r['denominator']
  lines.append(l)
 assert next(iterrows,None) is None
 return '\n'.join(lines)

REG=re.compile(r'\bn\s*[:=]\s*(\d+(?:\s*,\s*\d+)*)(?=\s*\)?\s*(?:$|;))',re.I)
def scope(o,r):
 if r['level']!='outcome':return r['denominator'],'structured_'+str(r['level'])
 c=r['category']; n=r['denominator']; m=REG.search(c); people=re.fullmatch(r'Participants:\s*(\d+)',n,re.I)
 if not people:return n,'unchanged'
 if m:
  vals=re.findall(r'\d+',m[1]);gids=[q['id'] for q in o['groups']]; titles=[q['title'] for q in o['groups']]; a=r['json_pointer'].split('/'); meas=o['classes'][int(a[6])]['categories'][int(a[8])]['measurements']; ids=[q['groupId'] for q in meas];
  if ids==gids and len(vals)==len(ids) and len(set(titles))==len(titles):return 'Outcome arm: '+people[1]+' participants; category n: '+vals[titles.index(r['group'])],'ordered_class_n'
  return 'Outcome arm: '+people[1]+' participants; category n not assigned','unassigned_class_n'
 if re.match(r'^Participant \d+\b',c,re.I) and re.search('per participant',o.get('description',''),re.I):return 'Outcome cohort: '+people[1]+' participants; estimate for one participant','individual_estimate'
 return n,'unchanged'
def claim_parse(claim):
    pats=[r'^For group "(.*?)", the (\w+) for "(.*?)" was (\d+(?:\.\d+)?) (.*) \((time frame .*?)\)\.$',
          r'^The outcome was "(.*?)"\. Under (.*), group "(.*?)" had a reported (\w+) of (\d+(?:\.\d+)?) (.*?)\.$',
          r'^A (\w+) of (\d+(?:\.\d+)?) (.*?) was recorded for "(.*?)" in group "(.*?)"; (.*)\.$']
    for i,p in enumerate(pats):
        m=re.fullmatch(p,claim,re.S)
        if not m: continue
        a=m.groups()
        if i==0: g,s,e,v,u,cond=a
        elif i==1: e,cond,g,s,v,u=a
        else: s,v,u,e,g,cond=a
        d={'group':g,'statistic':s.upper(),'endpoint':e,'value':v,'unit':u}
        labels={'time frame':'time','analysis population':'population','category':'category','denominator':'denominator'}
        matches=list(re.finditer(r'(time frame|analysis population|category|denominator) "(.*?)"(?=; |$)',cond,re.S))
        remainder=cond
        for mm in reversed(matches): remainder=remainder[:mm.start()]+remainder[mm.end():]
        if remainder.strip('; '): raise ValueError('unparsed conditions '+repr(remainder))
        for k in labels.values():d[k]=''
        for mm in matches:d[labels[mm[1]]]=mm[2]
        return d
    raise ValueError('unparsed claim '+claim)
def fetch(path,obj):
 for p in path.split('/')[1:]:obj=obj[int(p)] if isinstance(obj,list) else obj[p]
 return obj
def keyref(pm,text):
 keys=set();pm=str(pm or '').strip();
 if pm.isdigit():keys.add('pmid:'+pm)
 for t in re.findall(r'(?i)\b10\.\d{4,9}/[-._;()/:A-Z0-9]+',text or ''):
  t=t.lower().rstrip('.,;');
  while t.endswith(')') and t.count(')')>t.count('('):t=t[:-1]
  keys.add('doi:'+t)
 return keys
def meta(s):
 p=s['protocolSection'];i=p['identificationModule'];tid=i['nctId'];org={'sid:'+re.sub(r'\W','',x['id'].lower()) for x in [i.get('orgStudyIdInfo',{})]+i.get('secondaryIdInfos',[]) if x.get('id')};refs=set();result=set()
 for x in p.get('referencesModule',{}).get('references',[]):
  k=keyref(x.get('pmid'),x.get('citation'));refs|=k
  if x.get('type','').lower() in ('result','derived'):result|=k
 return tid,org,refs,result
def evidence(outs,ix):
 ls=render(outs,ix).split('\n'); rr=[r for i in sorted(ix) for r in records(outs[i],i)]; it=iter(rr)
 for j,l in enumerate(ls):
  if l.startswith('Denominator: '):
   r=next(it);ls[j]='Denominator: '+scope(outs[r['outcome_index']],r)[0]
 assert next(it,None) is None;return '\n'.join(ls)
