from build_data import norm, table_text

def den(obj,g):return '; '.join(f"{d.get('units','')}: {p['value']}" for d in obj.get('denoms',[]) for p in d.get('counts',[]) if p.get('groupId')==g)

# Reader note: o is an outcome and oi is its position in the registry. Yield a record, scoped denominator and source pointer per measurement.
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
