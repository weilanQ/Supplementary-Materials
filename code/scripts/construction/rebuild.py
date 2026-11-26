"""Rebuild the study partitions from the archive's registry and public benchmark snapshots."""
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import argparse
import json
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / 'data/raw/construction'
sys.path.append(str(ROOT/'code/src/legacy'))
import registry_builder as registry
import public_builder, series_a, series_b, initial_builder, screen_builder, condition_builder
from fields import claim_parse, evidence, fetch, keyref, make_claim, meta, records, render, scope


def read(path):
    return json.loads(path.read_bytes())


def rows(path):
    return [json.loads(line) for line in path.read_bytes().splitlines() if line]


def fingerprint(records):
    # Sorting dictionary keys removes serializer differences. The sample order is preserved.
    data=json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(',',':')).encode()
    return sha256(data).hexdigest()


def emit(folder,name,records):
    data=b''.join((json.dumps(row,ensure_ascii=False)+'\n').encode() for row in records)
    (folder/(name+'.jsonl')).write_bytes(data)


def scoped(inputs,pairs,studies):
    """Re-render the frozen pair from its two source pointers and the denominator at the target's table level."""
    out=[]
    for row in inputs:
        key=pairs[row['pair_id']]
        outcomes=studies[row['source_group']]['resultsSection']['outcomeMeasuresModule']['outcomeMeasures']
        indices={key[k]['outcome_index'] for k in ('target','donor')}
        points={r['json_pointer']:r for i in indices for r in records(outcomes[i],i)}
        target=points[key['target']['json_pointer']]
        value=target['value'] if row['gold']=='consistent' else points[key['donor']['json_pointer']]['value']
        m=re.search(r'[CR](\d+)$',row['pair_id']); j=int(m[1])-1
        template=row.get('template',j)
        claim=make_claim(dict(target,denominator=scope(outcomes[target['outcome_index']],target)[0]),value,template)
        text=evidence(outcomes,indices);out.append(dict(row,claim=claim,evidence=text,evidence_sha256=registry.sha(text)))
    return out


def revised_registry(rows_in):
    """Apply the dated response-denominator amendments; keep all original IDs and labels."""
    final=[]
    sponsor=read(RAW/'virage_report.json')
    found=re.search(r'DoR\) was ([\d.]+) months \(n=(\d+)\) in the SoC control arm, while the median DoR in the VCN-01\+SoC treatment arm was doubled to ([\d.]+) months \(n=(\d+)',sponsor['source_excerpt'])
    control,n0,treated,n1=found.groups()
    def quoted(m):return 'Reported outcome arm: '+m[1]+' participants; responder analysis size not given in this table'
    for item in rows_in:
        row=dict(item);trial=row['source_group'];ev=row['evidence'];claim=row['claim']
        if row['pair_id']=='NCT05673811-R1':
            for val,count in ((control,n0),(treated,n1)):
                ev=ev.replace('Denominator: Participants: 48\nValue: '+val,'Denominator: Participants: '+count+'\nValue: '+val)
            ev=ev.replace('Time frame:','Source note: For this duration-of-response table, responder counts come from the sponsor report of the same two medians.\nTime frame:');claim=claim.replace('denominator "Participants: 48"',f'denominator "Participants: {n1}"')
        elif trial in ('NCT03665441','NCT05673811') and re.search(r'^Outcome \d+: Duration of Response',ev,re.M):
            ev='\n\n'.join(re.sub(r'(?m)^Denominator: Participants: (\d+)\s*$',lambda m:'Denominator: '+quoted(m),s) if re.match(r'Outcome \d+: Duration of Response',s) else s for s in ev.split('\n\n'))
            if '"Duration of Response (DoR)"' in claim:claim=re.sub(r'denominator "Participants: (\d+)"',lambda m:'denominator "'+quoted(m)+'"',claim)
        final.append(dict(row,claim=claim,evidence=ev,evidence_sha256=registry.sha(ev)))
    return final


def build(tmp):
    """Construct each partition in original order from the archived inputs; tmp holds the old registry layout."""
    load=lambda name:read(RAW/name)
    parents=load('legacy_exclusions.json');pub_ids=load('public_exclusions.json');all_public=set().union(*[set(v) for v in pub_ids.values()]);old_ids=set(parents['nct']);pmids={'pmid:'+v for v in parents['pmid']}
    gold=load('public_gold.json');trials=load('public_results.json');public=public_builder.build(gold,{k:{'Results':v} for k,v in trials.items()}); external={v[k] for v in gold.values() for k in ('Primary_id','Secondary_id') if v.get(k)}
    registry.BASE=tmp/'original';registry.DATA=registry.BASE/'data';(registry.DATA/'raw').mkdir(parents=True);(registry.BASE/'legacy_inputs').mkdir();shutil.copyfile(RAW/'registry_original.json',registry.DATA/'raw/ctgov_search.json');(registry.BASE/'legacy_inputs/v2_9_corpus_combined.json').write_text(json.dumps(parents['nct']+[{'pmid':v} for v in parents['pmid']]),encoding='utf8')
    print('Rebuilding original registry pairs and their rendered evidence',flush=True)
    registry.custom(external)
    original=load('registry_original.json')['studies'];a_candidates=load('registry_series_a.json')['studies'];b_candidates=load('registry_series_b.json')['studies']; by_trial=lambda s:{meta(x)[0]:x for x in s}
    keys={r['base_id']:{'target':r['record'],'donor':r['donor']} for r in rows(registry.DATA/'base_records.jsonl')}; original_map=by_trial(original)
    development=scoped(rows(registry.DATA/'registry_development.jsonl'),keys,original_map)
    retrospective=revised_registry(scoped(rows(registry.DATA/'registry_test.jsonl'),keys,original_map))
    dev={}
    for r in sorted(development,key=lambda x:registry.sha('row-probe-v1|'+x['id'])):dev.setdefault(r['source_group'],r)
    bymodel=lambda rs:[{k:r[k] for k in ('id','claim','evidence')} for r in rs]
    oldkeys=set().union(*(series_a.meta(s)[1] for s in original))|{t.lower() for t in old_ids|set(pub_ids['training'])|set(pub_ids['gold_test.json'])}|pmids
    a,akey=series_a.build(a_candidates,oldkeys);a=scoped(a,{r['pair']:r for r in akey},by_trial(a_candidates))
    prior=original+a_candidates;old_trials=old_ids|all_public|{meta(s)[0] for s in prior};old_org=set().union(*(meta(s)[1] for s in prior));old_refs=pmids|{'pmid:'+v for v in load('legacy_publication_ids.json')}|set().union(*(meta(s)[2] for s in prior));index=defaultdict(set); resultlinks=defaultdict(set)
    for tid,ls in load('registry_citations.json').items():
        for pm,citation,kind in ls:
            ref=keyref(pm,citation);index[tid].update(ref)
            if kind.lower() in ('result','derived'):resultlinks[tid].update(ref)
    b,bkey=series_b.build(b_candidates,old_trials.copy(),old_org.copy(),old_refs.copy(),index,resultlinks)
    print('Rebuilding the 698 screening decisions and main confirmation cohort',flush=True)
    candidates=load('registry_screen_1.json')['studies']+load('registry_screen_2.json')['studies'];allprev=prior+b_candidates
    ids=old_ids|all_public|{meta(s)[0] for s in allprev};org=set().union(*(meta(s)[1] for s in allprev));refs=pmids|set().union(*(meta(s)[2] for s in allprev))|set().union(*(index[t] for t in ids));screen,possible=screen_builder.build(candidates,ids,org,refs,index)
    eligible={tid for tid,reason in screen if reason=='screened'};previous_candidates={r['trial'] for r in possible};lookup=by_trial(candidates);main,key,exclusions=initial_builder.build(lookup,eligible-previous_candidates,previous_candidates,index)
    print('Rebuilding the condition test and the public sample',flush=True)
    condition_prior=load('condition_prior_cohorts.json');assert set(condition_prior['confirmation'])=={r['trial'] for r in key}
    previous=set(condition_prior['earlier'])|set(condition_prior['confirmation']); eligible_condition=eligible-previous;later=by_trial(load('registry_condition.json'));pm=load('condition_pubmed.json'); links={t:index[t]|(meta(later[t])[2] if t in later else set())|{'pmid:'+v for v in pm.get(t,[])} for t in previous|eligible_condition}
    c,ck=condition_builder.build(later,eligible_condition,links,set().union(*(links[t] for t in previous)),set().union(*(meta(later[t])[1] for t in previous if t in later)))
    return {'registry_development':development,'registry_retrospective':retrospective,'series_a':a,'series_b':b,'development_inputs':bymodel(dev.values()),'development_key':[{'id':r['id'],'trial':r['source_group'],'gold':r['gold']} for r in dev.values()],'main_inputs':bymodel(main),'main_key':key,'main_exclusions':exclusions,'screen':screen,'condition_inputs':c,'condition_key':ck,'public':public}


def run(destination):
    if destination.exists(): raise FileExistsError('Choose a new output directory: '+str(destination))
    with TemporaryDirectory(prefix='rebuild_',dir=destination.parent) as wd:
        stage=Path(wd); outputs=build(stage); expected=read(ROOT/'config/construction_outputs.json'); assert outputs.keys()==expected.keys()
        out=stage/'verified';out.mkdir()
        for name,records_ in outputs.items():
            item=expected[name]
            if len(records_)!=item['count'] or fingerprint(records_)!=item['sha256']:
                raise ValueError('Mismatch with the independently archived reference: '+name)
            emit(out,name,records_)
        out.replace(destination)
    print('Rebuilt and verified all historical partitions against archived references.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('destination',type=Path);run(p.parse_args().destination.resolve())
