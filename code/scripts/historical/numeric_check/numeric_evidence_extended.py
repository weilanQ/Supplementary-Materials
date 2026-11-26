"""Check point estimates in the full original text, preserving signs and comparison boundaries."""
import re
from decimal import Decimal, InvalidOperation

MAGNITUDE = r'(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?|\.\d+)'
NUMBER = re.compile(r'(?<![\w.])(?P<value>[+\-−]?' + MAGNITUDE + r')(?![\w]|\.\d)')
LITERAL = re.compile(r'[+\-−]?' + MAGNITUDE)
BOUND_BEFORE = re.compile(r'(?:[<>≤≥≠≈~]\s*=?|[≤≥<>]\s+or\s+equal\s+to|\b(?:at least|at most|more than|less than|greater than|fewer than|up to|approximately|about|over|under|below|above))\s*$',re.I)
RANGE_BEFORE = re.compile(r'\d\s*(?:[-–—]|\bto)\s*$',re.I)
RANGE_AFTER = re.compile(r'^\s*(?:[-–—]|\bto\b)\s*[+\-−]?\d',re.I)

# Additional language forms examined after the confirmation experiment.
SIGNED = r'[+\-−]?' + MAGNITUDE
SUFFIX_BOUND = re.compile(r'^\s+or\s+(?:more|fewer|less|higher|lower|greater)\b', re.I)
BETWEEN = re.compile(r'\bbetween\s+(' + SIGNED + r')\s+and\s+(' + SIGNED + r')(?![\w]|\.\d)', re.I)

def point(value):
    text=str(value).strip()
    if not LITERAL.fullmatch(text):return None
    try:return Decimal(text.replace('−','-').replace(',',''))
    except InvalidOperation:return None

def occurs_in_spans(value,text,spans):
    wanted=point(value)
    if wanted is None:return False
    endpoints = {match.span(i) for match in BETWEEN.finditer(text) for i in (1, 2)}
    for token in NUMBER.finditer(text):
        start,end=token.span('value')
        if not any(lo<=start and end<=hi for lo,hi in spans):continue
        before,after=text[:start],text[end:]
        if (start, end) in endpoints or SUFFIX_BOUND.match(after):
            continue
        if BOUND_BEFORE.search(before) or RANGE_BEFORE.search(before) or RANGE_AFTER.match(after):continue
        if before and before[-1] in '+-−' or before.rstrip().endswith(('−','+','-')):continue
        if point(token['value'])==wanted:return True
    return False
