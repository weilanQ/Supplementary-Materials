import collections, itertools, re, json, hashlib, zipfile, random, csv
from decimal import Decimal
from pathlib import Path
from registry_builder import sha
def build(gold,trials):
    """Sample numeric Results statements by ID and trial; attach the published labels only after selection."""
    eligible={k:v for k,v in gold.items() if v['Type']=='Single' and v['Section_id']=='Results' and re.search(r'\d',v['Statement'])}
    grouped=collections.defaultdict(list)
    for k,v in eligible.items():grouped[v['Primary_id']].append((k,v))
    selected=[]
    # Round robin over source groups; within source, hash order; never uses Label.
    for items in grouped.values():items.sort(key=lambda x:sha('external-20261027-'+x[0]))
    for depth in range(max(map(len,grouped.values()))):
        for tid in sorted(grouped,key=lambda x:sha(x)):
            if depth<len(grouped[tid]) and len(selected)<150:selected.append(grouped[tid][depth])
    rows=[]
    for k,v in selected:
        tid=v['Primary_id'];text='\n'.join(trials[tid]['Results'])
        rows.append({'id':k,'dataset':'nli4ct_p','source_group':tid,'source_url':f'https://clinicaltrials.gov/study/{tid}',
          'evidence':text,'claim':v['Statement'],'gold':{'Entailment':'consistent','Contradiction':'mismatch'}[v['Label']],
          'split':'external_test','label_basis':'published NLI4CT-P labels','original_metadata':v,'evidence_sha256':sha(text)})
    return rows
