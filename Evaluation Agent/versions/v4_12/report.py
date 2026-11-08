"""Short score/comment reports, including a four-model comparison, without model calls."""
from pathlib import Path
from html import escape
from runtime import portable_json as json
import csv

DIMENSIONS=(('problem_understanding','理解'),('empathy_and_emotional_support','共情'),('cultural_respect_and_autonomy','尊重与自主'),('clarity_and_accessibility','清晰'),('reasonableness_and_practicality','实用'),('factual_reliability_and_faithfulness','事实可靠'))

def _rows(path):return [json.loads(l) for l in path.read_text(encoding='utf-8-sig').splitlines() if l.strip()] if path.is_file() else []

def write_compact(run_dir,destination=None):
    run_dir=Path(run_dir);m=json.loads((run_dir/'manifest.json').read_text(encoding='utf-8-sig'))
    rows=_rows(run_dir/m['result_file']);review=_rows(run_dir/'needs_review.jsonl');errors=_rows(run_dir/'errors.jsonl')
    return write_table(rows,review,errors,destination or run_dir,'V4.12 · '+m['evaluator_model']+' → '+m['target_model'])

def write_table(rows,review,errors,destination,title):
    folder=Path(destination);folder.mkdir(parents=True,exist_ok=True)
    head=['模型','场景','评分状态']+[v for _,v in DIMENSIONS]
    md=['# '+title,'',f'已有数值评分 {len(rows)} 条；待复核 {len(review)} 条；失败 {len(errors)} 条。六维独立 0–10 分，无总分。','', '| '+' | '.join(head)+' |','| '+' | '.join(['---']*len(head))+' |']
    html=['<!doctype html><meta charset="utf-8"><style>body{font:15px system-ui;max-width:1100px;margin:28px auto;padding:0 14px}table{border-collapse:collapse;width:100%}td,th{padding:8px;border:1px solid #ddd;text-align:left}p{line-height:1.6}</style><h1>'+escape(title)+'</h1><p>'+escape(md[2])+'</p><table><tr>'+''.join('<th>'+escape(h)+'</th>' for h in head)+'</tr>']
    provisional=sum(r.get('score_status')=='provisional' for r in rows)
    md.insert(3,f'其中暂用评分 {provisional} 条；均保留六维数值，可按评分状态筛选统计。来源与标记见原始结果。')
    html.append('<p>暂用评分 '+str(provisional)+' 条；均保留六维数值，可按状态筛选统计。</p>')
    comments=[]
    for r in rows:
        model=r['target_model'];scenario=r.get('source_metadata',{}).get('scenario_name','?')
        scores=[str(r['dimensions'][d]['score']) for d,_ in DIMENSIONS]
        md.append('| '+' | '.join([model,scenario,'暂用' if r.get('score_status')=='provisional' else '已校验']+scores)+' |')
        html.append('<tr>'+''.join('<td>'+escape(x)+'</td>' for x in [model,scenario,'暂用' if r.get('score_status')=='provisional' else '已校验']+scores)+'</tr>')
        text='；'.join(name+'：'+r['dimensions'][d]['comment'] for d,name in DIMENSIONS)
        comments.append((model+' · '+scenario,text))
    html.append('</table><h2>短评</h2>');md+=['','## 短评','']
    for label,text in comments:
        md += ['**'+label+'**  '+text,''];html.append('<p><b>'+escape(label)+'</b><br>'+escape(text)+'</p>')
    for r in review+errors:
        line=r.get('target_model','?')+' · '+r['response_id']+'：'+r.get('reason',r.get('error','未出分'))
        md+=['- '+line];html.append('<p>'+escape(line)+'</p>')
    usages=[a['usage'] for r in rows+review+errors for a in r.get('evaluation_attempts',[]) if isinstance(a.get('usage'),dict)]
    count=sum(len(r.get('evaluation_attempts',[])) for r in rows+review+errors)
    totals={'recorded_requests':len(usages),'request_count':count}
    for k in ('input_tokens','cached_input_tokens','output_tokens','thinking_tokens','total_tokens'):
        totals[k]=sum(u[k] for u in usages) if usages and all(type(u.get(k)) is int for u in usages) else None
    usage_text='用量记录：'+json.dumps(totals,ensure_ascii=False)
    md+=['',usage_text];html+=['<p>'+escape(usage_text)+'</p>']
    (folder/'report.md').write_text('\n'.join(md)+'\n',encoding='utf-8');(folder/'report.html').write_text(''.join(html),encoding='utf-8')
    (folder/'usage.json').write_text(json.dumps(totals,ensure_ascii=False,indent=2),encoding='utf-8')
    with (folder/'scores.csv').open('w',encoding='utf-8-sig',newline='') as handle:
        writer=csv.writer(handle)
        writer.writerow(['模型','场景','回答编号','评分状态']+[name for _,name in DIMENSIONS])
        for row in rows:
            writer.writerow([row['target_model'],row.get('source_metadata',{}).get('scenario_id',''),row['response_id'],row.get('score_status','validated')]+[row['dimensions'][d]['score'] for d,_ in DIMENSIONS])
    return folder/'report.md',folder/'report.html' 

def write_comparison(outcomes,destination):
    rows=[];review=[];errors=[]
    for result in outcomes:
        folder=Path(result['output_dir']);m=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        rows+=_rows(folder/m['result_file']);review+=_rows(folder/'needs_review.jsonl');errors+=_rows(folder/'errors.jsonl')
    return write_table(rows,review,errors,destination,'V4.12 · 先弱后强 · 每模型五条')
