"""Deterministic joint-record decision rules. No labels or construction code imported."""
import re
from numeric_evidence import occurs_in_spans, point

IDENTITY=('group','endpoint','unit','statistic')
CONDITIONS=('time','population','denominator','category')
FIELDS=IDENTITY+CONDITIONS+('value',)
ALIASES={'pfs':'progression free survival','os':'overall survival','orr':'objective response rate',
 'progressionfree':'progression free','months':'month','weeks':'week','days':'day',
 'percentage':'percent','%':'percent','count of participants':'count','number':'count',
 'mean value':'mean','median value':'median'}
def norm(x):
    s=str(x or '').lower().replace('%',' percent ')
    s=re.sub(r'[^a-z0-9.]+',' ',s).strip()
    for a,b in ALIASES.items():s=re.sub(r'\b'+re.escape(a)+r'\b',b,s)
    return re.sub(r'\s+',' ',s).strip()
def eq(a,b):return norm(a)==norm(b)
def numeric(x):
    return point(x)
def value_eq(a,b):
    x,y=numeric(a),numeric(b)
    return x is not None and y is not None and x==y
# Reader note: Validate the extracted records against the claim text. Return accepted records with offsets and a separate list of validation errors.
def validate_records(payload,text):
    good=[];bad=[]
    if not isinstance(payload,dict) or not isinstance(payload.get('records'),list):return [],['invalid_schema']
    for i,r in enumerate(payload['records']):
        if not isinstance(r,dict):bad.append({'index':i,'reason':'invalid_record'});continue
        r={**{k:'' for k in FIELDS},**r}
        if isinstance(r.get('value'),(int,float)):r['value']=str(r['value'])
        if not all(isinstance(r.get(k),str) for k in FIELDS):bad.append({'index':i,'reason':'nonstring_field'});continue
        if numeric(r['value']) is None or not all(r[k].strip() for k in IDENTITY):bad.append({'index':i,'reason':'missing_identity_or_numeric_value'});continue
        quotes=r.get('quotes',[])
        if not isinstance(quotes,list) or not quotes or not all(isinstance(q,str) and q.strip() for q in quotes):
            bad.append({'index':i,'reason':'invalid_quotes'});continue
        # Reconcile only one-to-one quotation-mark variants; offsets always reference original text.
        trans=str.maketrans({'"':"'",'\u201c':"'",'\u201d':"'",'\u2018':"'",'\u2019':"'"})
        resolved=[]
        for quote in quotes:
            start=text.find(quote)
            if start<0:start=text.translate(trans).find(quote.translate(trans))
            if start<0:break
            resolved.append(text[start:start+len(quote)])
        if len(resolved)!=len(quotes):bad.append({'index':i,'reason':'quote_not_found'});continue
        quotes=resolved
        spans=[{'start':text.index(q),'end':text.index(q)+len(q),'quote':q} for q in quotes]
        # Literal numeric membership is a necessary provenance check, never a support decision.
        if not occurs_in_spans(r['value'],text,[(s['start'],s['end']) for s in spans]):
            bad.append({'index':i,'reason':'value_not_quoted'});continue
        r['spans']=spans
        good.append(r)
    return good,bad

# Reader note: Use a source-row list and claim relations to return a verdict with evidence per relation. mode selects the ablation.
def decide(source,claims,mode='joint',extraction_errors=None,complete=True):
    errors=extraction_errors or []
    if not claims or not source or errors or not complete:
        return {'prediction':'unclear','reason':'missing, incomplete, or invalid extraction','relations':[]}
    out=[]
    for q in claims:
        fields=IDENTITY if mode=='no_conditions' else IDENTITY+CONDITIONS
        if mode=='field_only':
            # No common-record requirement: deliberate ablation can assemble unrelated fields.
            ok=all(any((value_eq(q[k],r[k]) if k=='value' else eq(q[k],r[k])) for r in source) for k in fields+('value',) if q[k])
            out.append({'label':'consistent' if ok else 'unclear','reason':'independent field membership','spans':[]});continue
        candidates=[r for r in source if all(eq(q[k],r[k]) for k in IDENTITY)]
        if mode!='no_conditions':
            # Conditions must be explicitly compatible. Missing necessary condition is uncertainty.
            candidates=[r for r in candidates if all(eq(q[k],r[k]) for k in CONDITIONS)]
        if not candidates:
            out.append({'label':'unclear','reason':'no record with matching identity and conditions','spans':[]});continue
        values={numeric(r['value']) for r in candidates}
        if len(values)>1:
            out.append({'label':'unclear','reason':'conflicting candidates','spans':[s for r in candidates for s in r['spans']]});continue
        ok=any(value_eq(q['value'],r['value']) for r in candidates)
        out.append({'label':'consistent' if ok else 'mismatch','reason':'one compatible record supports relation' if ok else 'same identity and conditions have an explicitly different value',
          'mismatch_fields':[] if ok else ['value_assignment'],'claim':q,'source_records':candidates,'spans':[s for r in candidates for s in r['spans']]})
    labels=[r['label'] for r in out]
    pred='mismatch' if 'mismatch' in labels else 'consistent' if labels and all(x=='consistent' for x in labels) else 'unclear'
    return {'prediction':pred,'reason':'atomic-relation aggregation','relations':out}
