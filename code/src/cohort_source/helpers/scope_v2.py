import re

REG=re.compile(r'\bn\s*[:=]\s*(\d+(?:\s*,\s*\d+)*)(?=\s*\)?\s*(?:$|;))',re.I)

# Reader note: Use the outcome and measurement to return denominator text and its provenance. Mark unmatched category counts as unassigned.
def scope(o,r):
 if r['level']!='outcome':return r['denominator'],'structured_'+str(r['level'])
 c=r['category']; n=r['denominator']; m=REG.search(c); people=re.fullmatch(r'Participants:\s*(\d+)',n,re.I)
 if not people:return n,'unchanged'
 if m:
  vals=re.findall(r'\d+',m[1]);gids=[q['id'] for q in o['groups']]; titles=[q['title'] for q in o['groups']]; a=r['json_pointer'].split('/'); meas=o['classes'][int(a[6])]['categories'][int(a[8])]['measurements']; ids=[q['groupId'] for q in meas];
  if ids==gids and len(vals)==len(ids) and len(set(titles))==len(titles):return 'Outcome arm: '+people[1]+' participants; category n: '+vals[titles.index(r['group'])],'ordered_class_n'
  return 'Outcome arm: '+people[1]+' participants; category n not assigned','unassigned_class_n'
 if re.match(r'^Participant \d+\b',c,re.I) and re.search('per participant',o.get('description',''),re.I):return 'Outcome cohort: '+people[1]+' participants; estimate for one participant','individual_estimate'
 return n,'unchanged'
