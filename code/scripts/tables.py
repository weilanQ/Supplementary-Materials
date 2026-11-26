from score import *

def make():
    scores=get(OUT/'metrics.json'); failures=get(OUT/'failure.json');s=[r'\input{independent_table.tex}',r'\begin{table}[!htbp]\centering\small',r'\caption{Judgments and cost on two sets of 80 statements. Cover, Right and Wrong count definite answers. Gains, losses and trial-paired intervals (percentage points) compare with Direct within each set. Abstentions count as errors in accuracy. Tokens include input and output. Seconds sum logged request times.}\label{tab:primary}',r'\setlength{\tabcolsep}{1.1pt}\begin{tabular}{@{}lrrrrrrrrr@{}}\toprule',r'Method & Cover & Right & Wrong & Acc.\,\% & Gain/loss & 95\% CI & Calls & Tokens & Sec.\\\midrule'];
    for name,model in [('Qwen','qwen2.5_7b'),('Llama','llama3.1_8b')]:
        s.append(r'\multicolumn{10}{@{}l}{Initial trials, '+name+r'}\\');
        for x in scores:
            if x['model']!=model:continue
            a,b=x['ci'];ci=f'[{a:g},{b:g}]';s.append(f"{x['method']} & {x['answered']} & {x['correct']} & {x['wrong']} & {x['accuracy']:.1f} & {x['fixed']}/{x['lost']} & {ci} & {x['calls']} & {x['tokens']:,} & {x['seconds']:.0f}"+r'\\')
        if name=='Qwen':s.append(r'\midrule')
    s.extend([r'\independentrows',r'\bottomrule\end{tabular}\end{table}']);(OUT/'comparison.tex').write_text('\n'.join(s),encoding='utf8');s=[r'\begin{table}[!htbp]\centering\small\caption{Where verification stopped on the initial 80 statements per model. Each block assigns one first stopping point per statement. The row selector tests completeness before validating individual quotations. A reply can have additional errors after its first stopping point.}\label{tab:stage}',r'\begin{tabular}{@{}lrr@{}}\toprule Stage & Qwen & Llama\\\midrule'];
    blocks=[('Original Joint','original_first',[('Transport, truncation, JSON, schema or invalid point','syntax'),('Missing identity field','missing_identity'),('Quoted passage absent from the statement','quote_not_found'),('Value outside quoted span','value_not_quoted'),('Incomplete or empty extraction','incomplete'),('No compatible source row','no_compatible_row'),('Conflicting candidate values','candidate_conflict'),('Definite decision','decided')]),('Row selection','selection_stage',[('Truncated JSON','truncated'),('Incomplete or empty relation list','incomplete'),('Invalid value quotation','invalid_value_quote'),('Invalid condition quotation','invalid_condition_quote'),('Selection unresolved after validation','selection_unresolved'),('Definite decision','decided')])];
    for heading,block,stages in blocks:
        s.append(r'\multicolumn{3}{@{}l}{'+heading+r'}\\'); cols=[failures[x][block] for x in failures];assert all(sum(c.get(k,0) for _,k in stages)==80 for c in cols)
        for caption,k in stages:s.append(f'{caption} & {cols[0].get(k,0)} & {cols[1].get(k,0)}'+r'\\')
        s.append(r'\midrule')
    s=s[:-1]+[r'\bottomrule\end{tabular}\end{table}'];(OUT/'stages.tex').write_text('\n'.join(s),encoding='utf8')
if __name__=='__main__': make()
