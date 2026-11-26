import re

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
