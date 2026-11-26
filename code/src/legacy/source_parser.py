"""Parse documented result-table text grammars; never reads registry JSON or labels.

Unsupported source layouts fall back to the pinned LLM extractor. This table
parser is distinct from the JSON traversal used to construct evaluation labels.
"""
import re
from numeric_evidence import point

# Reader note: Convert a rendered outcome table into records with spans in the original text. An unrecognized heading returns None.
def parse_table(text):
    lines=text.splitlines(keepends=True);offset=0;header={};row=None;records=[]
    header_names={'Description':'description','Time frame':'time','Analysis population':'population','Statistic':'statistic','Unit of measure':'unit'}
    row_names={'Group':'group','Category':'category','Denominator':'denominator','Value':'value'}
    positions=[];recognized=bool(re.search(r'^Outcome \d+: ',text,re.M))
    if not recognized:return None
    for line in lines:
        raw=line.rstrip('\r\n');m=re.match(r'^Outcome \d+: (.+)$',raw)
        if m:
            header={'endpoint':m[1],'time':'','population':'','statistic':'','unit':''};positions=[{'start':offset,'end':offset+len(raw),'quote':raw}];row=None
        elif ': ' in raw:
            key,val=raw.split(': ',1)
            if key in header_names:
                header[header_names[key]]=val;positions.append({'start':offset,'end':offset+len(raw),'quote':raw})
            elif key=='Group':
                row={**header,'group':val,'category':'','denominator':'','spans':list(positions)}
                row['spans'].append({'start':offset,'end':offset+len(raw),'quote':raw})
            elif key in row_names and row is not None:
                row[row_names[key]]=val;row['spans'].append({'start':offset,'end':offset+len(raw),'quote':raw})
                if key=='Value':
                    if point(val) is None:return None
                    records.append(row);row=None
        offset+=len(line)
    if not records:return None
    return {'records':records,'complete':True,'parser':'registry-table-text-v1'}
