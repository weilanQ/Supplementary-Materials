import collections, itertools, re, json, hashlib, zipfile, random, csv
from decimal import Decimal
from pathlib import Path
def sha(s):return hashlib.sha256(s.encode()).hexdigest()

def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')

def jsonl(p,x):p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in x),encoding='utf-8')

def norm(s):return re.sub(r'\s+',' ',str(s)).strip()

def same(a,b):return norm(a).lower()==norm(b).lower()

def distinct(a,b):
    x,y=Decimal(a),Decimal(b)
    tol=max(Decimal(10)**x.as_tuple().exponent,Decimal(10)**y.as_tuple().exponent)/2
    return abs(x-y)>tol

def extract_registry_records(study):
    outcomes=study.get('resultsSection',{}).get('outcomeMeasuresModule',{}).get('outcomeMeasures',[])
    records=[]
    for oi,o in enumerate(outcomes):
        if len(o.get('title',''))>180 or o.get('paramType') not in ['MEAN','MEDIAN','NUMBER','COUNT_OF_PARTICIPANTS']:continue
        groups={g['id']:g for g in o.get('groups',[])}
        for ci,c in enumerate(o.get('classes',[])):
            for ki,k in enumerate(c.get('categories',[])):
                for mi,m in enumerate(k.get('measurements',[])):
                    gid=m.get('groupId');g=groups.get(gid,{})
                    value=m.get('value','')
                    if not re.fullmatch(r'\d+(?:\.\d+)?',value):continue
                    if not g.get('title') or len(g['title'])>150 or not o.get('unitOfMeasure') or not o.get('timeFrame'):continue
                    den=[]
                    for d in o.get('denoms',[]):
                        for count in d.get('counts',[]):
                            if count.get('groupId')==gid:den.append(f"{d.get('units','')}: {count['value']}")
                    rec={'outcome_index':oi,'group':g['title'],'endpoint':o['title'],'value':value,'unit':o['unitOfMeasure'],
                      'statistic':o['paramType'],'time':o['timeFrame'],'population':o.get('populationDescription',''),
                      'denominator':'; '.join(den),'category':norm(c.get('title','')+'; '+k.get('title','')).strip('; '),
                      'json_pointer':f'/resultsSection/outcomeMeasuresModule/outcomeMeasures/{oi}/classes/{ci}/categories/{ki}/measurements/{mi}/value',
                      'group_id':gid}
                    records.append(rec)
    return records,outcomes

def table_text(outcomes,indices):
    lines=[]
    for oi in sorted(indices):
        o=outcomes[oi];lines.extend([f'Outcome {oi+1}: {o["title"]}',f'Description: {o.get("description","")}',f'Time frame: {o.get("timeFrame","")}',
         f'Analysis population: {o.get("populationDescription","")}',f'Statistic: {o.get("paramType","")}',f'Unit of measure: {o.get("unitOfMeasure","")}'])
        gs={g['id']:g['title'] for g in o.get('groups',[])}
        for c in o.get('classes',[]):
            for k in c.get('categories',[]):
                for m in k.get('measurements',[]):
                    gid=m.get('groupId');den=[]
                    for d in o.get('denoms',[]):
                        for count in d.get('counts',[]):
                            if count.get('groupId')==gid:den.append(f"{d.get('units','')}: {count['value']}")
                    lines.extend([f'Group: {gs.get(gid,gid)}',f'Category: {norm(c.get("title","")+"; "+k.get("title","")).strip("; ")}',
                     f'Denominator: {"; ".join(den)}',f'Value: {m.get("value","")}'])
        lines.append('')
    return '\n'.join(lines).strip()

def make_claim(r,value,template):
    cond=[]
    if r['time']:cond.append(f'time frame "{r["time"]}"')
    if r['population']:cond.append(f'analysis population "{r["population"]}"')
    if r['category']:cond.append(f'category "{r["category"]}"')
    if r['denominator']:cond.append(f'denominator "{r["denominator"]}"')
    conditions='; '.join(cond)
    if template==0:return f'For group "{r["group"]}", the {r["statistic"].lower()} for "{r["endpoint"]}" was {value} {r["unit"]} ({conditions}).'
    if template==1:return f'The outcome was "{r["endpoint"]}". Under {conditions}, group "{r["group"]}" had a reported {r["statistic"].lower()} of {value} {r["unit"]}.'
    return f'A {r["statistic"].lower()} of {value} {r["unit"]} was recorded for "{r["endpoint"]}" in group "{r["group"]}"; {conditions}.'

def custom(excluded):
    """Build paired development and test statements from the archived registry search, excluding public trial IDs."""
    search=json.loads((DATA/'raw/ctgov_search.json').read_text(encoding='utf-8'))
    oldpath=BASE.parent/'research_v2_10/data/v2_9_corpus_combined.json'
    if not oldpath.exists():oldpath=BASE/'legacy_inputs/v2_9_corpus_combined.json'
    oldtext=oldpath.read_text(encoding='utf-8')
    oldids=set(re.findall(r'NCT\d{8}',oldtext));oldpmids=set(re.findall(r'"pmid"\s*:\s*"(\d+)"',oldtext))
    candidates=[];exclusions=[]
    for s in search['studies']:
        ident=s['protocolSection']['identificationModule'];tid=ident['nctId']
        pmids={str(x.get('pmid','')) for x in s['protocolSection'].get('referencesModule',{}).get('references',[])}
        if tid in excluded|oldids or pmids&oldpmids:
            exclusions.append({'trial':tid,'reason':'external-or-old-source-overlap'});continue
        records,outs=extract_registry_records(s);pairs=[]
        for ai,a in enumerate(records):
            for bi,b in enumerate(records):
                if ai==bi or not distinct(a['value'],b['value']):continue
                if not all(same(a[k],b[k]) for k in ['unit','statistic','category']):continue
                group_swap=a['outcome_index']==b['outcome_index'] and not same(a['group'],b['group'])
                endpoint_swap=same(a['group'],b['group']) and not same(a['endpoint'],b['endpoint']) and all(same(a[k],b[k]) for k in ['time','population','denominator'])
                if not(group_swap or endpoint_swap):continue
                # No other reported row with the target identity can support the donor value.
                identity=['group','endpoint','unit','statistic','time','population','denominator','category']
                if any(all(same(a[k],c[k]) for k in identity) and distinct(c['value'],a['value']) for c in records):continue
                evidence=table_text(outs,{a['outcome_index'],b['outcome_index']})
                if len(evidence)>14000:continue
                pairs.append((a,b,'group_swap' if group_swap else 'endpoint_swap',evidence))
        # Prefer covering both error types before extra records, without using model scores.
        pairs.sort(key=lambda x:(x[2],sha(json.dumps(x[0],sort_keys=True))))
        chosen=[];used_targets=set()
        for typ in ['group_swap','endpoint_swap']:
            avail=[x for x in pairs if x[2]==typ]
            if avail:
                chosen.append(avail[0]);used_targets.add(avail[0][0]['json_pointer'])
        for p in pairs:
            if len(chosen)>=3:break
            if p[0]['json_pointer'] not in used_targets:
                chosen.append(p);used_targets.add(p[0]['json_pointer'])
        if len(chosen)>=2:candidates.append((tid,s,chosen))
        else:exclusions.append({'trial':tid,'reason':'fewer-than-two-unambiguous-compatible-pairs','available':len(chosen)})
    candidates.sort(key=lambda x:sha('registry-20261027-'+x[0]));candidates=candidates[:60]
    # Assign sources before producing claims. Template 2 occurs only in held-out groups.
    devn=round(len(candidates)/3);assignment={tid:('development' if i<devn else 'test') for i,(tid,_,_) in enumerate(candidates)}
    dump(DATA/'source_split_before_claims.json',assignment)
    rows=[];bases=[];sources=[]
    for tid,s,pairs in candidates:
        raw=DATA/'raw'/f'{tid}.json';dump(raw,s)
        sources.append({'trial':tid,'title':s['protocolSection']['identificationModule']['briefTitle'],'split':assignment[tid],
         'url':f'https://clinicaltrials.gov/study/{tid}','raw_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),
         'org_study_id':s['protocolSection']['identificationModule'].get('orgStudyIdInfo',{}),'secondary_ids':s['protocolSection']['identificationModule'].get('secondaryIdInfos',[])})
        for pi,(a,b,typ,evidence) in enumerate(pairs):
            bid=tid+f'-R{pi+1}';template=pi%2 if assignment[tid]=='development' else pi%3
            base={'base_id':bid,'source_group':tid,'record':a,'donor':b,'mutation':typ,'evidence':evidence,'evidence_sha256':sha(evidence),
             'label_basis':'structured registry values; same-study AI construction and source checks; no independent human adjudication'}
            bases.append(base)
            for sign,value in [('pos',a['value']),('neg',b['value'])]:
                claim=make_claim(a,value,template);rid=sha(bid+sign)[:16]
                rows.append({'id':rid,'dataset':'registry_pairs','source_group':tid,'pair_id':bid,'base_id':bid,'split':assignment[tid],
                  'evidence':evidence,'claim':claim,'gold':'consistent' if sign=='pos' else 'mismatch','error_type':typ,
                  'template':template,'cross_sentence':template==1,'unseen_template':template==2,
                  'close_values':abs(Decimal(a['value'])-Decimal(b['value']))/max(abs(Decimal(a['value'])),abs(Decimal(b['value'])),Decimal('0.001'))<=Decimal('.15'),
                  'evidence_sha256':sha(evidence),'mutation':{'field':'value','before':a['value'],'after':value,'donor_pointer':b['json_pointer']},
                  'label_basis':base['label_basis'],'source_url':f'https://clinicaltrials.gov/study/{tid}'})
    jsonl(DATA/'base_records.jsonl',bases);jsonl(DATA/'registry_development.jsonl',[r for r in rows if r['split']=='development']);jsonl(DATA/'registry_test.jsonl',[r for r in rows if r['split']=='test'])
    dump(DATA/'source_inventory.json',sources);dump(DATA/'exclusions.json',exclusions)
    dump(DATA/'registry_summary.json',{'retrieved':len(search['studies']),'sources':len(candidates),'dev_sources':devn,'test_sources':len(candidates)-devn,'base_records':len(bases),'variants':len(rows),
     'error_types':dict(collections.Counter(r['error_type'] for r in rows)),'split_records':dict(collections.Counter(r['split'] for r in rows)),
     'independence':'grouped by NCT and registry secondary IDs screened; linked publications excluded by known NCT/PMID; participant overlap cannot be ruled out',
     'scope':'pancreatic-cancer registry search; mixed-tumour studies may be present; frozen source snapshots, not patient-level data'})
    # Human-facing blind form contains complete evidence and claim, without labels or paired IDs.
    blinded=list(rows);random.Random(20261027).shuffle(blinded)
    with (DATA/'blinded_annotation.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['id','source_url','evidence','claim','reviewer','label','reason','evidence_location']);w.writeheader()
        for r in blinded:w.writerow({k:r.get(k,'') for k in w.fieldnames})
    jsonl(DATA/'annotation_key_private.jsonl',[{'id':r['id'],'pair_id':r['pair_id'],'gold':r['gold']} for r in rows])
    return rows
