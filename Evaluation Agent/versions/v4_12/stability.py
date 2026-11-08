"""Read-only repeatability comparison for the same judge and unchanged conditions."""
from pathlib import Path
from runtime import portable_json as json
from html import escape

CONDITIONS=('rubric_sha256','calibration_sha256','checklist_sha256','evaluator_generation_config','scoring_code_sha256','checklist_output_mode')
def rows(path):return [json.loads(l) for l in path.read_text(encoding='utf-8-sig').splitlines() if l.strip()] if path.is_file() else []

def write_stability(outcomes,destination):
    pairs=[];summaries={}
    for outcome in outcomes:
        folder=Path(outcome['output_dir']);m=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        current=rows(folder/m['result_file']);prior={}
        manifests=sorted(folder.parent.glob('run_*/manifest.json'),key=lambda p:p.stat().st_mtime,reverse=True)
        for mf in manifests:
            if mf.parent==folder:continue
            old=json.loads(mf.read_text(encoding='utf-8-sig'))
            if old.get('evaluator_model')!=m['evaluator_model'] or any(old.get(k)!=m.get(k) for k in CONDITIONS):continue
            if old.get('round_timestamp_utc','')>=m.get('round_timestamp_utc',''):continue
            for row in rows(mf.parent/old['result_file']):prior.setdefault(row['response_id'],(row,str(mf.parent)))
        for row in current:
            old=prior.get(row['response_id'])
            if old is None:continue
            before,run=old
            if any(row.get(k)!=before.get(k) for k in ('source_sha256','initial_task_sha256','initial_instructions_sha256')):continue
            for dim,value in row['dimensions'].items():
                previous=before.get('dimensions',{}).get(dim,{}).get('score')
                if type(previous) is not int:continue
                pairs.append({'evaluator_model':row['evaluator_model'],'target_model':row['target_model'],'response_id':row['response_id'],
                    'scenario_id':row['source_metadata']['scenario_id'],'dimension':dim,'previous_score':previous,'current_score':value['score'],
                    'delta':value['score']-previous,'previous_run':run,'current_status':row.get('score_status'),'previous_status':before.get('score_status'),
                    'repair_context_changed':len(row.get('evaluation_attempts',[]))!=len(before.get('evaluation_attempts',[]))})
    judges=list(dict.fromkeys(o['evaluator_model'] for o in outcomes))
    for judge in judges:
        selected=[p for p in pairs if p['evaluator_model']==judge];deltas=[abs(p['delta']) for p in selected]
        summaries[judge]={'status':'compared' if selected else 'insufficient_matching_history','answers':len({p['response_id'] for p in selected}),
            'dimensions':len(selected),'same':sum(x==0 for x in deltas),'within_1':sum(x<=1 for x in deltas),
            'changed_at_least_2':sum(x>=2 for x in deltas),'max_abs_delta':max(deltas) if deltas else None}
    result={'purpose':'Same judge, same answer, same prompt/reference/code/settings. Differences between two judges are not a stability test.',
        'summaries':summaries,'comparisons':pairs,'additional_api_calls':0}
    folder=Path(destination);(folder/'stability.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    md=['','## 同一评委重复稳定性','', '只比较同一评委、同一回答、相同版本/代码/参数的历史运行；不会增加 API 调用，也不合并两位评委分数。','',
        '| 评委 | 可比回答 | 可比维度 | 同分 | 差不超过1分 | 差至少2分 | 最大分差 |','| --- | --- | --- | --- | --- | --- | --- |']
    html=['<h2>同一评委重复稳定性</h2><p>'+escape(md[3])+'</p><table><tr><th>评委</th><th>可比回答</th><th>可比维度</th><th>同分</th><th>差不超过1分</th><th>差至少2分</th><th>最大分差</th></tr>']
    notes=[]
    for judge,s in summaries.items():
        cells=[judge]+[str(s[k]) if s[k] is not None else '—' for k in ('answers','dimensions','same','within_1','changed_at_least_2','max_abs_delta')]
        md.append('| '+' | '.join(cells)+' |');html.append('<tr>'+''.join('<td>'+escape(x)+'</td>' for x in cells)+'</tr>')
        if not s['dimensions']:
            note=judge+'：尚无同条件历史记录，暂不能判断重复稳定性。'
            notes.append(note)
    md+=['']+notes
    html.append('</table>');html.extend('<p>'+escape(note)+'</p>' for note in notes)
    with (folder/'report.md').open('a',encoding='utf-8') as h:h.write('\n'.join(md)+'\n')
    with (folder/'report.html').open('a',encoding='utf-8') as h:h.write(''.join(html))
    return folder/'stability.json'
