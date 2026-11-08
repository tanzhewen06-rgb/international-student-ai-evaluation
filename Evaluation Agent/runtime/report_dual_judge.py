"""Pair the same saved answers by judge; no model calls or score aggregation."""
from pathlib import Path
from html import escape
import csv
from runtime import portable_json as json
from versions.v4_8.report import DIMENSIONS,_rows

def write_comparison(outcomes,destination,manifest):
    folder=Path(destination);folder.mkdir(parents=True,exist_ok=True)
    all_rows=[]
    for outcome in outcomes:
        root=Path(outcome['output_dir'])
        m=json.loads((root/'manifest.json').read_text(encoding='utf-8-sig'))
        all_rows+=_rows(root/m['result_file'])+_rows(root/'needs_review.jsonl')+_rows(root/'errors.jsonl')
    lookup={}
    for row in all_rows:
        key=(row['target_model'],row['response_id'],row['evaluator_model'])
        if key in lookup:raise ValueError('Duplicate judge judgment in comparison.')
        lookup[key]=row
    judges=manifest['judges'];cohort=manifest['cohort'];flat=[];differences=[]
    md=['# '+manifest['evaluation_batch']+' · '+manifest['rubric_version']+' · 双评委对照','',
        'Prompt '+manifest['rubric_version']+f'；同一批{len(cohort)}条回答，两个评委独立评分。六维均为 0–10 分，无总分或合并分。',
        '分差 = Gemini − DeepSeek；绝对差达到 2 分标为 ★。已校验只表示程序一致性检查通过；暂用分保留数值并附原因。','']
    md.append('评委设置见各原始 manifest；V4.10/V4.11/V4.12 固定双方 temperature=0。跨评委分差只表示分歧，同一评委的重复稳定性另表统计。')
    if manifest.get('setup_attempts'):
        md.append('连接调试阶段另有失败尝试，未用来替代评分；其已记录用量与中断请求单独保存于 setup_attempts.json。')
    head=['回答模型','场景','生成遍次','Gemini状态','DeepSeek状态']+[v+' G / D / 差' for _,v in DIMENSIONS]
    md+=['| '+' | '.join(head)+' |','| '+' | '.join(['---']*len(head))+' |']
    html=['<!doctype html><meta charset="utf-8"><style>body{font:14px system-ui;margin:24px;padding:0 12px}table{border-collapse:collapse;width:100%;margin:16px 0}td,th{border:1px solid #ddd;padding:8px;text-align:left}td{vertical-align:top}p{line-height:1.6}.flag{background:#fff1bd}</style>',
        '<h1>'+escape(manifest['evaluation_batch'])+' · '+escape(manifest['rubric_version'])+' · 双评委对照</h1><p>'+escape(md[2])+'</p><p>'+escape(md[3])+'</p>',
        '<table><tr>'+''.join('<th>'+escape(x)+'</th>' for x in head)+'</tr>']
    def status(row):
        if row is None:return '未执行'
        if row.get('status')!='scored':return '待复核' if row.get('status')=='needs_review' else '请求失败'
        return '暂用' if row.get('score_status')=='provisional' else '已校验'
    def score(row,d):return row.get('dimensions',{}).get(d,{}).get('score') if row and row.get('status')=='scored' else None
    for source in cohort:
        rows=[lookup.get((source['target_model'],source['response_id'],j)) for j in judges]
        for row in rows:
            if row and row.get('source_sha256')!=source['source_sha256']:raise ValueError('Source hash changed during experiment.')
        cells=[source['target_model'],source['scenario_id'],str(source.get('repeat_index','—'))]+[status(r) for r in rows];highlight=False
        for d,name in DIMENSIONS:
            a,b=[score(r,d) for r in rows];delta=a-b if a is not None and b is not None else None
            flag=delta is not None and abs(delta)>=2;highlight|=flag
            cells.append(f'{a if a is not None else "—"} / {b if b is not None else "—"} / {delta if delta is not None else "—"}'+(' ★' if flag else ''))
            differences.append({'target_model':source['target_model'],'response_id':source['response_id'],'scenario_id':source['scenario_id'],
                'repeat_index':source.get('repeat_index'),'dimension':d,'gemini_score':a,'deepseek_score':b,'delta':delta,'flag':flag,'gemini_status':status(rows[0]),'deepseek_status':status(rows[1])})
        md.append('| '+' | '.join(cells)+' |')
        html.append('<tr'+(' class="flag"' if highlight else '')+'>'+''.join('<td>'+escape(x)+'</td>' for x in cells)+'</tr>')
        for j,row in zip(judges,rows):
            flat.append({'rubric_version':manifest['rubric_version'],'evaluation_round_id':manifest['evaluation_round_id'],'target_model':source['target_model'],'scenario_id':source['scenario_id'],'response_id':source['response_id'],
                'repeat_index':source.get('repeat_index'),'generation_run_id':source.get('generation_run_id'),'evaluator_model':j,'status':status(row),'score_status':row.get('score_status') if row else None,
                **{d:score(row,d) for d,_ in DIMENSIONS},'comments':{d:row.get('dimensions',{}).get(d,{}).get('comment') for d,_ in DIMENSIONS} if row else {},
                'quality_flags':row.get('quality_flags',[]) if row else [],'reason':row.get('reason',row.get('error')) if row else 'Not executed'})
    html.append('</table>');md+=['','## 短评',''];html.append('<h2>短评</h2>')
    for row in flat:
        text='；'.join(name+'：'+str(row['comments'].get(d) or '') for d,name in DIMENSIONS) if any(row[d] is not None for d,_ in DIMENSIONS) else row['reason'] or '未出分'
        if row['quality_flags']:text+='；暂用原因：'+json.dumps(row['quality_flags'],ensure_ascii=False)
        label=' · '.join([row['target_model'],row['scenario_id'],'repeat '+str(row.get('repeat_index','—')),row['evaluator_model'],row['status']])
        md+=['**'+label+'**  '+text,''];html.append('<p><b>'+escape(label)+'</b><br>'+escape(text)+'</p>')
    usage={}
    for judge in judges:
        attempts=[a for row in all_rows if row['evaluator_model']==judge for a in row.get('evaluation_attempts',[])]
        recorded=[a['usage'] for a in attempts if isinstance(a.get('usage'),dict)]
        totals={'request_count':len(attempts),'recorded_requests':len(recorded)}
        for k in ('input_tokens','cached_input_tokens','output_tokens','thinking_tokens','billable_output_tokens','total_tokens'):
            totals[k]=sum(u[k] for u in recorded) if recorded and all(type(u.get(k)) is int for u in recorded) else None
        usage[judge]=totals
    counts={j:{s:sum(row['evaluator_model']==j and row['status']==s for row in flat) for s in ('已校验','暂用','待复核','请求失败','未执行')} for j in judges}
    brief=json.dumps({'counts':counts,'differences_at_least_2':sum(d['flag'] for d in differences),'usage':usage},ensure_ascii=False,indent=2)
    md+=['','## 状态与用量','','```json',brief,'```'];html.append('<h2>状态与用量</h2><pre>'+escape(brief)+'</pre>')
    if manifest.get('setup_attempts'):
        (folder/'setup_attempts.json').write_text(json.dumps(manifest['setup_attempts'],ensure_ascii=False,indent=2),encoding='utf-8')
        html.append('<p>调试阶段另有失败尝试及一条中断请求，未参与分数对比；用量单独记录于 setup_attempts.json。</p>')
    (folder/'report.md').write_text('\n'.join(md)+'\n',encoding='utf-8');(folder/'report.html').write_text(''.join(html),encoding='utf-8')
    for filename,value in [('scores.json',flat),('differences.json',differences),('usage.json',usage),('summary.json',{'counts':counts,'differences_at_least_2':sum(d['flag'] for d in differences)})]:
        (folder/filename).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    with (folder/'scores.csv').open('w',encoding='utf-8-sig',newline='') as handle:
        w=csv.writer(handle);w.writerow(['Prompt版本','评估轮次','回答模型','场景','回答编号','评委','状态']+[name for _,name in DIMENSIONS]+[name+'短评' for _,name in DIMENSIONS])
        for row in flat:w.writerow([row['rubric_version'],row['evaluation_round_id'],row['target_model'],row['scenario_id'],row['response_id'],row['evaluator_model'],row['status']]+[row[d] for d,_ in DIMENSIONS]+[row['comments'].get(d) for d,_ in DIMENSIONS])
    return folder/'report.md',folder/'report.html'
