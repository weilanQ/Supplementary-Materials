from shared import *
import copy
import relation_core as rc
from source_parser import parse_table
from decimal import Decimal
oldnorm=rc.norm
def norm(x):
 s=str(x or ''); s=re.sub(r'<=|>=|≤|≥|<|>|−|(?<![A-Za-z])-(?=\d)',lambda m:' '+{'<=':'leq','≤':'leq','>=':'geq','≥':'geq','<':'lt','>':'gt','−':'minus','-':'minus'}[m[0]]+' ',s); return oldnorm(s)
rc.norm=norm
# Reader note: Parse the source excerpt and return its records plus a completeness flag. A missing row field prevents a definite lookup.
def source_table(text):
 if not re.search(r'^Outcome \d+: ',text,re.M):return None
 s=parse_table(text); lines=text.splitlines(); groups=sum(l.startswith('Group: ') for l in lines); vals=sum(l.startswith('Value: ') for l in lines); good=bool(s) and len(s['records'])==groups==vals and groups>0
 if good:
  for i,l in enumerate(lines):
   if l.startswith('Group: '):good &= (len(lines)>i+3 and lines[i+1].startswith('Category: ') and lines[i+2].startswith('Denominator: ') and lines[i+3].startswith('Value: '))
  good &= all(all(r.get(k,'').strip() for k in rc.IDENTITY) for r in s['records'])
 return dict(records=s['records'] if s else [],complete=bool(good),parser='registry-text-v2')
def compact(rs):return [{k:r.get(k,'') for k in rc.FIELDS} for r in rs]
# Reader note: Only structured sources can supply an omitted time or population from a unique compatible heading.
def inherited_claims(sr,qr,structured):
 # Inherit only a unique source-header time/population under the same identity.
 claims=copy.deepcopy(qr)
 for q in claims:
  pool=[r for r in sr if all(rc.eq(q[k],r[k]) for k in rc.IDENTITY)]
  for k in ('time','population'):
   vals={norm(r[k]) for r in pool};
   if structured and not q[k] and len(vals)==1 and '' not in vals:q[k]=pool[0][k]
 return claims

def verdict(sr,qr,structured,mode='joint'):
 return rc.decide(sr,inherited_claims(sr,qr,structured),mode)
