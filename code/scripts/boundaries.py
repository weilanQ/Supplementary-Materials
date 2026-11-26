"""Offline annotation and validation. Public applicability is based on statement and passage only."""
from score import *
from method import sig
from rules import inherited_claims

def public_scope():
    # A stated exact result must be locatable by subject, outcome and conditions in the supplied passage.
    # Same-unit alternatives can be false and still be in scope. Do not use benchmark labels or predictions.
    groups=[('direct','04178e95 ca09a15d a4e6bb5b','Number of participants with AEs, distinct from the SAE count.'),('direct','2855e123 098f7c20 4318ce37','Imaging subgroup and percentage appear together in one outcome row.'),('direct','73052d5e','The cohort-specific target is a participant count.'),('direct','eb088d03','The first cohort explicitly reports both the count and the percentage with an adverse event.'),('direct','5ba46a49','Two arm titles and two explicit counts. Each arm can be checked separately.'),('conversion','2f57e639','The passage gives a percentage. The statement gives a fraction.'),('conversion','cd8d5a6a','Both arms give explicit percentages. Converting dL to mL is required to identify the comparator.'),('conversion','197bf729','Dose matches. Weeks must be converted to days and a reduction mapped to a signed mean.'),('different construct','08920163 06a1adac ad477da6 51220352','The statement counts recipients of treatment. The excerpt reports the analyzed population and a safety outcome.'),('different construct','585b42d5 9a7f95d5','The passage reports percentages screened at baseline and follow-up, whereas the claim counts people.'),('different construct','2c7901c7','The passage counts affected participants. The statement also counts incidents and asserts where all occurred.'),('derived change','1616266d c2c4cbf5 efbc4408','Two visit medians are given. An individual or aggregate change is not an explicitly reported point estimate.'),('mixed or altered identity','c6b37d94 41cbc4ea 75e0a9f9','The claim changes regimen or endpoint as well as a numerical result. A value check alone is insufficient.'),('mixed or altered identity','ab848536','The comparator is described as 17 mL while the title specifies 3 mL. A matching comparator is unavailable.')]; mapping={i:(g,v) for g,ids,v in groups for i in ids.split()};types=byid(read(H/'public_types.jsonl')); output=[]
    for x in read(H/'public.jsonl'):
        if types[x['id']]['type']!='point-shaped':continue
        category,reason=mapping[x['id'][:8]];quotes=[dict(start=m.start(),end=m.end(),text=m[0]) for m in re.finditer(r'(?m)^\s*(?:Arm/Group Title:|Overall Number of Participants Analyzed:|Unit of Measure:|SAEs:|Cervical Cancer Screening|Ki67 expression at 6 weeks:).*$',x['evidence'])];assert quotes;output.append(dict(id=x['id'],trial=x['source_group'],claim=x['claim'],passage_sha256=sig(x['evidence']),category=category,reason=reason,evidence_lines=quotes))
    assert len(output)==len(mapping)==26;lines(OUT/'public_scope.jsonl',output);return Counter(x['category'] for x in output)

def ledger():
    decisions=read(H/'decisions.jsonl'); group=byid(read(H/'source_checks.jsonl')); series=byid(read(H/'series_b.jsonl')); repairs=byid(get(H/'source_evidence/percentile_wording.json')); entries=[]
    for row in decisions:
        if row['model']!='qwen2.5_7b' or row['cohort'] not in ('Registry','Holdout'):continue
        pair=row['pair'];uid=row['id'];rec=group.get(uid);trial=row['trial']; status=None
        if pair in ('NCT03665441-R2','NCT03665441-R3'):status='unresolved';issue='Responder count unavailable for duration, including where the value is the donor. Arm count 257 is not a responder count.'
        elif pair=='NCT05673811-R1':status='source-qualified';issue='Sponsor supplies 19 and 15 responders for 11.2 and 5.4 months. Preserve assigned label.'
        elif pair=='NCT01964430-H2':status='wording repaired';issue='Median heading over percentile rows. Revised wording identifies the 75th percentile. No reference-label change.'
        elif pair=='NCT03914950-H1':status='unresolved';issue='SUVmax endpoint and unit interpretation unresolved. The separate tracer-uptake participant-count pair is outside this exclusion.'
        else:continue
        claim=rec['final_claim'] if rec else series[uid]['claim']; target=rec['target'] if rec else None; donor=rec['donor'] if rec else None
        entries.append(dict(id=uid,trial=trial,pair=pair,cohort=row['cohort'],status=status,issue=issue,original_reference=row['gold'],scored_reference=row['gold'],claim=claim,amended_claim=repairs.get(uid,{}).get('revised_claim',claim),target=target,donor=donor,evidence=(None if rec else series[uid]['evidence'])))
    lines(OUT/'label_ledger.jsonl',entries); remove={x['id'] for x in entries if x['status']=='unresolved'};a=[]
    for cohort in ('Registry','First','Holdout','New','Public'):
        for model in [m.replace(':','_') for m in MODELS]:
            xs=[x for x in decisions if x['model']==model and x['cohort']==cohort]; kept=[x for x in xs if x['id'] not in remove]; a.append(dict(cohort=cohort,model=model,total=len(xs),excluded=len(xs)-len(kept),n=len(kept),trials=len({x['trial'] for x in kept}),direct=sum(x['pred']['direct']==x['gold'] for x in kept),fusion=sum(x['pred']['fusion']==x['gold'] for x in kept)))
    assert len(remove)==6;dump(OUT/'sensitivity.json',a)

def corroborate():
    audit=read(OUT/'audit.jsonl');refs=byid(read(H/'checked_confirmation_relations.jsonl')); inputs=byid(read(BASE/'data/confirmation.jsonl')); evidence=[]
    for uid,model,kind in [('30110659f9d529aa','qwen2.5_7b','valid JSON with missing identity'),('239c89fe7cc44f1e','llama3.1_8b','extra selected relation')]:
        item=inputs[uid]; old=byid(read(H/model/'items.jsonl'))[uid]; cl=get(H/model/'calls'/(old['calls']['joint'][-1]+'.json'));receipt=get(BASE/'logs'/f'confirmation_{model}_{uid}.json');row=next(x for x in audit if x['model']==model and x['id']==uid);evidence.append(dict(kind=kind,id=uid,model=model,claim=item['claim'],rows=source_table(item['evidence'])['records'],extraction=json.loads(cl['text']),raw_selected=receipt['raw']['message']['content'],diagnosis=row))
    c=byid(read(H/'condition_extension/confirm.jsonl'));k=byid(read(H/'condition_extension/key.jsonl'));uid='c696a7c518d11bb1';evidence.append(dict(kind='denominator lookup abstains',id=uid,paired_id='a66b8a1808ccc153',claim=c[uid]['claim'],evidence=c[uid]['evidence'],key=k[uid]));dump(OUT/'cases.json',evidence)
    # Mechanical wrapper checks on the twenty fixed development texts. These overlays are synthetic.
    for item in read(BASE/'data/dev.jsonl'):
        body=json.dumps({'complete':False,'records':[],'statement':item['claim']}); assert decoded(repaired('```json\n'+body+'\n```'))==decoded(body);assert decoded(repaired('\ufeff'+body))==decoded(body); assert decoded(repaired(body[:-1])) is None
    decisions=read(H/'decisions.jsonl'); counts=Counter(); public=defaultdict(Counter)
    for x in decisions:
        assert x['calls']['joint']; counts['claim']+=1;counts['source']+=int(len(x['calls']['joint'])==2)
        if x['cohort']=='Public':
            a=bool(x['claim_errors']);b=bool(x['source_errors']);public[x['model']].update(dict(n=1,claim=int(a),source=int(b),both=int(a and b),matched=int(x['gate']=='pass')))
    assert counts=={'claim':1316,'source':300};assert len(read(H/'source_checks.jsonl'))==344 and len({x['pair'] for x in read(H/'source_checks.jsonl')})==172;dump(OUT/'denominators.json',dict(extractions=counts,public=public,public_scope=public_scope()));ledger()
if __name__=='__main__':corroborate()
