import re
from decimal import Decimal

def norm(s):return re.sub(r'\s+',' ',str(s)).strip()

def distinct(a,b):
    x,y=Decimal(a),Decimal(b)
    tol=max(Decimal(10)**x.as_tuple().exponent,Decimal(10)**y.as_tuple().exponent)/2
    return abs(x-y)>tol

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
