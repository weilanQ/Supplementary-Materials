from collect import ARTIFACT, get


def write_table():
    results = ARTIFACT / 'results'
    summary = get(results / 'independent_metrics.json')
    parts = []
    for name in ('Qwen', 'Llama'):
        heading = r'\midrule\multicolumn{10}{@{}l}{Independent trials, ' + name + r'}\\'
        parts.append(heading)
        for row in summary:
            if row['model'].lower().startswith(name.lower()) and row['method'] != 'Ambiguity first + Direct':
                lo, hi = row['ci']
                cols = [row['method'], str(row['answered']), str(row['correct']), str(row['wrong']),
                        f"{row['accuracy']:.1f}", f"{row['fixed']}/{row['lost']}", f'[{lo:g},{hi:g}]',
                        str(row['calls']), f"{row['tokens']:,}", f"{row['seconds']:.0f}"]
                parts.append(' & '.join(cols) + r'\\')
    (results/'independent_table.tex').write_text('\\newcommand{\\independentrows}{%\n'+'\n'.join(parts)+'%\n}\n',encoding='utf8')

if __name__=='__main__': write_table()
