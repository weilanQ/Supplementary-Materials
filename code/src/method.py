from pathlib import Path
import hashlib,json,sys,re,os
from decimal import Decimal
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'legacy'))
from rules import source_table, norm, rc
from numeric_evidence import occurs_in_spans,point
FIELDS=rc.IDENTITY+rc.CONDITIONS
MODELS=['qwen2.5:7b','llama3.1:8b']
def read(p): return [json.loads(x) for x in p.read_bytes().splitlines() if x.strip()]
def dump(p,x): p.write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding='utf-8')
def lines(p,x): p.write_bytes(b''.join((json.dumps(v,ensure_ascii=False)+'\n').encode() for v in x))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def sig(s): return hashlib.sha256(s.encode()).hexdigest()
PROMPT='''Verify each stated outcome against numbered trial rows. Source outcome values are withheld during selection. Select rows by the group, endpoint, statistic, unit and every stated reporting condition, never by the outcome value. For each stated outcome return the chosen row_id (integer, 0 for no match, -1 for ambiguity), the numeric result as a string and value_quote copied exactly from the claim. Also copy the entire stated time, population, denominator and category as exact substrings from the claim, omitting field labels like "time frame:"; use an empty string for each absent condition. List all numerical outcomes separately, not participant counts used as denominators. Set complete false if the claim cannot be represented or any relation was missed. Output JSON only.'''
props={'row_id':{'type':'integer'},**{k:{'type':'string'} for k in ('value','value_quote',*rc.CONDITIONS)}}
schema={'type':'object','properties':{'complete':{'type':'boolean'},'relations':{'type':'array','items':{'type':'object','properties':props,'required':list(props),'additionalProperties':False}}},'required':['complete','relations'],'additionalProperties':False}
# Reader note: item contains the claim and source excerpt. Return the complete selector request for model.
def request(item,model):
    # Reader note: Number every row in source order. Expose identity and conditions to the selector and withhold the outcome value.
    table=source_table(item['evidence']); rows=[] if not table or not table['complete'] else table['records']; projected=[dict(row_id=i,**{k:r[k] for k in FIELDS}) for i,r in enumerate(rows,1)]
    return {'model':model,'messages':[{'role':'system','content':PROMPT},{'role':'user','content':json.dumps({'statement':item['claim'],'rows':projected},ensure_ascii=False)}],'format':schema,'stream':False,'options':{'temperature':0,'seed':17,'num_ctx':16384,'num_predict':768},'keep_alive':'10m'}
# Reader note: Remove only mechanical wrappers. An absent field or an unsupported value remains invalid.
def repaired(raw):
    trim=raw.strip().lstrip('\ufeff').strip(); m=re.fullmatch(r'```(?:json)?\s*\n(.*?)\n\s*```',trim,re.S|re.I); return m[1].strip() if m else trim

# Reader note: item is the label-free input and reply is the archived model response. Return prediction, first stopping stage and row IDs.
def judge(item,reply):
    def out(stage,verdict='unclear',ids=None): return {'stage':stage,'prediction':verdict,'row_ids': ids or []}
    table=source_table(item['evidence']); claim=item['claim']
    if not table or not table['complete']:return out('source_invalid')
    rows=table['records']
    if not reply.get('done') or reply.get('done_reason')=='length':return out('truncated')
    try: obj=json.loads(reply['message']['content'])
    except (ValueError,KeyError):return out('invalid_json')
    # Reader note: The frozen validator checks whether the full relation list is present before checking each quotation.
    if not isinstance(obj,dict) or obj.get('complete') is not True or not isinstance(obj.get('relations'),list) or not obj['relations']:return out('incomplete')
    ids=[];verdicts=[]; conflict=False
    for rel in obj['relations']:
        if not isinstance(rel,dict) or set(rel)!=set(props) or type(rel['row_id'])!=int or any(not isinstance(rel[k],str) for k in props if k!='row_id'):return out('invalid_schema')
        idx=rel['row_id']; ids.append(idx); value=point(rel['value']); quote=rel['value_quote']; spans=[(m.start(),m.end()) for m in re.finditer(re.escape(quote),claim)] if quote else []
        if value is None or not occurs_in_spans(rel['value'],claim,spans):return out('invalid_value_quote',ids=ids)
        if any(rel[k] and rel[k] not in claim for k in rc.CONDITIONS):return out('invalid_condition_quote',ids=ids)
        # Reader note: Row 0 means no match and -1 means ambiguous. Either leaves this relation unresolved.
        if idx in (0,-1):verdicts.append('unclear');continue
        if not 1<=idx<=len(rows):return out('invalid_row_id',ids=ids)
        chosen=rows[idx-1]; pool=[r for r in rows if all(norm(r[k])==norm(chosen[k]) for k in rc.IDENTITY)]
        for k in rc.CONDITIONS:
            if rel[k]:pool=[r for r in pool if norm(r[k])==norm(rel[k])]
        if chosen not in pool:verdicts.append('unclear');continue
        vals={point(r['value']) for r in pool}
        if len(vals)!=1:conflict=True;continue
        verdicts.append('consistent' if value in vals else 'mismatch')
    # Reader note: Conflicting candidate values take precedence for the whole statement. Otherwise any definite mismatch takes precedence.
    if conflict:return out('candidate_conflict',ids=ids)
    v='mismatch' if 'mismatch' in verdicts else ('consistent' if verdicts and all(a=='consistent' for a in verdicts) else 'unclear')
    return out('decided' if v!='unclear' else 'selection_unresolved',v,ids)
