"""Audit registry row pointers, input pairs and candidate visibility without using predictions."""
from collections import Counter, defaultdict
from decimal import Decimal
import re
from collect import HERE, ARTIFACT, get, read, byid
from reproduce import source_table, dump, rc


def registry_row(study, pointer):
    path = pointer.split('/')
    outcome = study['resultsSection']['outcomeMeasuresModule']['outcomeMeasures'][int(path[4])]
    group_class = outcome['classes'][int(path[6])]
    category = group_class['categories'][int(path[8])]
    measure = category['measurements'][int(path[10])]
    group_id = measure['groupId']
    group = next(x['title'] for x in outcome['groups'] if x['id'] == group_id)
    denominators = []
    for obj in (category,group_class,outcome):
        counts = [f"{d['units']}: {v['value']}" for d in obj.get('denoms',[]) for v in d.get('counts',[]) if v['groupId']==group_id]
        if counts:
            denominators=counts
            break
    category_label='; '.join([str(group_class.get('title','')),str(category.get('title',''))]).strip('; ')
    return dict(group=group,endpoint=outcome['title'],statistic=outcome['paramType'],unit=outcome['unitOfMeasure'],time=outcome.get('timeFrame',''),population=outcome.get('populationDescription',''),category=' '.join(category_label.split()),denominator='; '.join(denominators),value=str(measure['value']))


def audit_sources():
    inputs=byid(read(HERE/'inputs.jsonl')); keys=read(HERE/'key.jsonl'); counters=Counter(); groups=defaultdict(list); eligible=[]
    for row in keys:
        study=get(HERE/'registry'/(row['trial']+'.json'));assert study['protocolSection']['identificationModule']['nctId']==row['trial']
        for name in ('target','donor'):
            reference=registry_row(study,row[name]['json_pointer']); assert all(rc.eq(reference[k],row[name][k]) for k in rc.IDENTITY+rc.CONDITIONS) and Decimal(reference['value'])==Decimal(row[name]['value'])
        item=inputs[row['id']];prefix=item['claim'].split(' (time frame:',1)[0]; pattern=(r'^The table gives ([0-9]+(?:\.[0-9]+)?) ' if prefix.startswith('The table gives ') else r' was ([0-9]+(?:\.[0-9]+)?) '+re.escape(row['target']['unit'])+r'$'); matches=re.findall(pattern,prefix);assert len(matches)==1;expected=row['target'] if row['gold']=='consistent' else row['donor'];assert Decimal(matches[0])==Decimal(expected['value']); groups[row['pair']].append((row,item))
        parsed=source_table(item['evidence']);visible=[r for r in parsed['records'] if all(rc.eq(r[k],row['target'][k]) for k in rc.IDENTITY+rc.CONDITIONS)] if parsed and parsed['complete'] else []
        counters['pointer_and_label_checked']+=1;counters['source_completely_parsed']+=int(bool(parsed and parsed['complete']));counters['compatible_target_visible']+=bool(visible);counters['target_value_unique']+=bool(visible) and {Decimal(r['value']) for r in visible}=={Decimal(row['target']['value'])}
    for pair,records in groups.items():
        assert len(records)==2 and {r['gold'] for r,x in records}=={'consistent','mismatch'};assert len({x['evidence'] for r,x in records})==1 and len({r['target']['json_pointer'] for r,x in records})==1
    s=get(HERE/'screen.json');prior=set(s['prior_known_links']);data={}
    for tid in s['selected']:
        hits=get(HERE/'pubmed'/(tid+'.json'))['esearchresult'];assert int(hits['count'])==len(hits['idlist']);links=set(s['selected_links'][tid])|{'pmid:'+k for k in hits['idlist']};assert not links&prior;prior.update(links);data[tid]=sorted(links)
    dump(ARTIFACT/'results/independent_source_audit.json',dict(statements=len(keys),pairs=len(groups),counts=counters,trial_links=data,linked_trials=sum(bool(v) for v in data.values())))

if __name__=='__main__':audit_sources()
