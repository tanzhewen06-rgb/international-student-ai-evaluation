from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict,Counter
from itertools import combinations
from statistics import mean,stdev
import sys,hashlib,uuid,argparse,importlib.util,os
from runtime import portable_json as json
HERE=Path(__file__).resolve().parent
EA=HERE.parent
if str(EA) not in sys.path:sys.path.insert(0,str(EA))
from runtime.agent import load_rubric,prepare_task,DIMENSIONS
from runtime.storage import read_sources
from runtime.scoring import load_scoring_contract,validate_checklist_contract
from runtime.checklist import load_checklist,prepare_checklist
from runtime.calibration import load_calibration,prepare_calibration
from versions.v4_12.audit import prepare_audit_instructions
from runtime.evaluator import evaluate_file
spec=importlib.util.spec_from_file_location('_frozen_gpt_judge_client',HERE/'client.py')
client=importlib.util.module_from_spec(spec);spec.loader.exec_module(client)
from runtime.paths import RESPONSES_ROOT, EVALUATIONS_ROOT, REFERENCE_DATA_ROOT, relocated_path, path_key
RA=EA.parent/'Response Agent'
BASELINES=REFERENCE_DATA_ROOT/'gpt_judge_stability'
INPUTS=HERE/'frozen_inputs'
OUTPUT=EVALUATIONS_ROOT/'gpt_judge_stability_batch007'
REPEAT_COUNT=3
sha=lambda p:hashlib.sha256(relocated_path(p).read_bytes()).hexdigest()
shatext=lambda s:hashlib.sha256(s.encode('utf-8')).hexdigest()

def writable_path(path):
    path=relocated_path(path).resolve()


    if os.name=='nt' and not str(path).startswith('\\\\?\\'):
        if str(path).startswith('\\\\'):return Path('\\\\?\\UNC\\'+str(path)[2:])
        return Path('\\\\?\\'+str(path))
    return path

def preflight():
    config=json.loads((BASELINES/'baseline.json').read_text(encoding='utf-8'))
    assert config['source_batch']=='batch_007' and config['prepared_inputs_matched_historical']==50
    assert client.MODEL==config['model'] and REPEAT_COUNT==config['judgment_repeats']==3
    for name,h in config['frozen_sha256'].items():
        if sha(INPUTS/name)!=h:raise ValueError('Frozen input changed: '+name)
    if sha(BASELINES/'baseline_scores.json')!=config['baseline_scores_sha256']:raise ValueError('Baseline scores changed.')
    for name,h in config['required_runtime_sha256'].items():
        if sha(EA/name)!=h:raise ValueError('Frozen scoring runtime changed: '+name)
    for path,h in config['source_file_sha256'].items():
        if sha(path)!=h:raise ValueError('An original batch_007 answer file changed: '+path)
    sources,errors=read_sources(RESPONSES_ROOT/'batch_007',source_files=list(config['source_file_sha256']))
    if errors or len(sources)!=50:raise ValueError('Require exactly 50 valid original answers.')
    byid={s['record']['response_id']:s for s in sources}
    if set(byid)!={r['response_id'] for r in config['cohort']}:raise ValueError('Original cohort differs.')
    ins,template,rh=load_rubric(INPUTS/'rubric.md');con=load_scoring_contract(ins)
    checklist=load_checklist(INPUTS/'checklist.md');cal=load_calibration(INPUTS/'calibration.md')
    validate_checklist_contract(con,checklist,DIMENSIONS)
    for row in config['cohort']:
        s=byid[row['response_id']];r=s['record']
        if r['model_name']!=row['target_model'] or r['repeat_index']!=row['repeat_index'] or r['scenario_id']!=row['scenario_id']:raise ValueError('Source metadata differs.')
        instructions=prepare_audit_instructions(ins,r,con)+prepare_checklist(checklist,r)['instructions']+prepare_calibration(cal,r,con)
        hashes={'source_sha256':s['source_sha256'],'rubric_sha256':rh,'checklist_sha256':checklist['sha256'],'calibration_sha256':cal['sha256'],
                'initial_task_sha256':shatext(prepare_task(template,r)),'initial_instructions_sha256':shatext(instructions)}
        if hashes!=config['expected_inputs'][r['response_id']]:raise ValueError('Initial grading inputs differ from batch_007: '+r['response_id'])
    return config,sources

def rows(outcome):
    folder=relocated_path(outcome['output_dir']);m=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    return [json.loads(l) for p in [folder/m['result_file'],folder/'errors.jsonl',folder/'needs_review.jsonl'] if p.is_file() for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]

def collect_outcomes(trial,manifest):
    trial=writable_path(trial)
    outcomes=list(manifest['outcomes'])
    known={path_key(o['output_dir']) for o in outcomes}
    for p in (trial/'runs').glob('gpt_judge_batch007/*/run_*/manifest.json'):
        if path_key(p.parent) in known:continue
        rm=json.loads(p.read_text(encoding='utf-8'))
        repeat=manifest.get('rounds',{}).get(rm['evaluation_round_id'])
        if repeat is not None:
            outcomes.append({'output_dir':str(p.parent),'judge_repeat_index':repeat})
            known.add(path_key(p.parent))
    return outcomes

def collect_records(trial,manifest):
    records=[];seen=set()
    for outcome in collect_outcomes(trial,manifest):
        for row in rows(outcome):
            row['judge_repeat_index']=outcome['judge_repeat_index']
            key=(row['judge_repeat_index'],row['response_id'])
            if key in seen:raise ValueError('Duplicate judgment for one answer and judge repetition.')
            seen.add(key);records.append(row)
    return records

def summarize(trial):
    trial=writable_path(trial)
    manifest=json.loads((trial/'trial_manifest.json').read_text(encoding='utf-8'))
    allrows=collect_records(trial,manifest)
    byid=defaultdict(list)
    for row in allrows:
        if row['status']=='scored':byid[row['response_id']].append(row)
    cells=[];available=[];checkcells=[]
    baseline=json.loads((BASELINES/'baseline_scores.json').read_text(encoding='utf-8'))
    for rid,rr in byid.items():
        rr.sort(key=lambda r:r['judge_repeat_index'])
        for key in ('source_sha256','initial_task_sha256','initial_instructions_sha256','evaluator_generation_config','rubric_sha256','checklist_sha256','calibration_sha256'):
            if any(row[key]!=rr[0][key] for row in rr):raise ValueError('Repeated judgments have different scoring inputs or settings.')
        previous=[r for r in baseline if r['response_id']==rid]
        for dim in DIMENSIONS:
            values=[r['dimensions'][dim]['score'] for r in rr]
            cell={'response_id':rid,'target_model':rr[0]['target_model'],'scenario_id':rr[0]['source_metadata']['scenario_id'],
                'dimension':dim,'scores':values,'judge_repeat_indices':[r['judge_repeat_index'] for r in rr],'n':len(values),
                'mean':mean(values),'sample_sd':stdev(values) if len(values)>1 else None,'range':max(values)-min(values),
                'all_validated':all(r.get('score_status')=='validated' for r in rr)}
            available.append({**cell,'baseline_scores':{r['evaluator_model']:r.get(dim) for r in previous},
                'baseline_score_status':{r['evaluator_model']:r.get('score_status') for r in previous}})
            if len(values)==3:cells.append(cell)
        if len(rr)==3:
            for cid in rr[0]['checklist_findings']:
                values=[r['checklist_findings'][cid]['status'] for r in rr]
                checkcells.append({'response_id':rid,'id':cid,'statuses':values,'all_equal':len(set(values))==1})
    expected={(rep,c['response_id']) for rep in range(1,4) for c in manifest['source_inputs']['cohort']}
    actual={(r['judge_repeat_index'],r['response_id']) for r in allrows}
    if actual-expected:raise ValueError('Saved trial includes unexpected answer/repetition pairs.')
    execution_complete=actual==expected
    scored=sum(r['status']=='scored' for r in allrows)
    numeric_complete=execution_complete and scored==150
    status='complete' if numeric_complete else 'complete_with_review' if execution_complete else 'incomplete'
    large=[c for c in cells if c['range']>=2]
    stats={'status':status,'execution_complete':execution_complete,'numeric_complete':numeric_complete,'planned_judgments':150,
        'saved_judgments':len(allrows),'scored_judgments':scored,'unscored_judgments':len(allrows)-scored,
        'remaining_initial_judgments':len(expected-actual),'answers_with_any_numeric_score':len(byid),'complete_triplicate_answers':len(cells)//6,
        'complete_dimension_triplets':len(cells),'all_three_same':sum(c['range']==0 for c in cells),'all_three_within_1':sum(c['range']<=1 for c in cells),
        'spread_at_least_2':len(large),'max_spread':max((c['range'] for c in cells),default=None),
        'mean_within_answer_sample_sd':mean(c['sample_sd'] for c in cells) if cells else None,
        'fully_validated_triplets':sum(c['all_validated'] for c in cells),'checklist_triplets':len(checkcells),
        'checklist_all_three_same':sum(c['all_equal'] for c in checkcells),'score_status':dict(Counter(r.get('score_status','unscored') for r in allrows)),
        'logged_requests':sum(len(r.get('evaluation_attempts',[])) for r in allrows),
        'records_requiring_repair':sum(len(r.get('evaluation_attempts',[]))>1 for r in allrows),
        'meaning':'Stability uses only complete three-judgment answer/dimension groups. Agreement is not proof of semantic correctness. Unscored records are not zero.'}
    matched={rid for rid in byid}
    comparisons={}
    if matched:
        comparisons[client.MODEL]={dim:mean(c['mean'] for c in available if c['dimension']==dim) for dim in DIMENSIONS}
        for judge in sorted({r['evaluator_model'] for r in baseline}):
            comparisons[judge]={dim:mean(r[dim] for r in baseline if r['evaluator_model']==judge and r['response_id'] in matched) for dim in DIMENSIONS}
    (trial/'stability_summary.json').write_text(json.dumps({'summary':stats,'dimension_triplets':cells,'large_spreads':large,'checklist_triplets':checkcells},ensure_ascii=False,indent=2),encoding='utf-8')
    (trial/'three_judge_comparison.json').write_text(json.dumps(available,ensure_ascii=False,indent=2),encoding='utf-8')
    (trial/'matched_judge_means.json').write_text(json.dumps({'matched_answers':len(matched),'judge_means':comparisons,'provisional_values_retained':True},ensure_ascii=False,indent=2),encoding='utf-8')
    (trial/'gpt_judgments.json').write_text(json.dumps(allrows,ensure_ascii=False,indent=2),encoding='utf-8')
    md=['# GPT judge repeatability on batch 007','',f"Status: {status}. Attempted {len(allrows)}/150; scored {scored}; unscored {len(allrows)-scored}; remaining {stats['remaining_initial_judgments']}.",'',
        'The same 50 saved answers are judged independently three times. The original rubric, checklist, reference, score formula, provider settings and initial request hashes remain fixed.',
        'An unscored record is retained for review, is never converted to zero and does not stop other answers. Re-running this entry resumes an incomplete trial without repeating attempted requests.','',
        '## Matched comparison','',f'The comparison uses the same {len(matched)} answers for all judges. GPT is averaged within each answer before the overall mean. Provisional values remain labeled in the data. A partial subset does not represent all response models.','',
        '| Judge | Understanding | Empathy | Culture and autonomy | Clarity | Practicality | Reliability |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for judge,values in comparisons.items():md.append('| '+judge+' | '+' | '.join(f'{values[d]:.2f}' for d in DIMENSIONS)+' |')
    md+=['','## Repeatability','',f"Complete three-judgment answers: {stats['complete_triplicate_answers']}/50. Complete dimension triplets: {len(cells)}/300."]
    if cells:
        md+=['','| Metric | Count |','| --- | ---: |',f"| All three equal | {stats['all_three_same']} / {len(cells)} |",f"| All three within one point | {stats['all_three_within_1']} / {len(cells)} |",f"| Spread at least two points | {len(large)} / {len(cells)} |",f"| Maximum spread | {stats['max_spread']} |"]
    else:md+=['','Repeatability is not available yet. No answer has three completed numeric judgments; zero counts here are not an agreement estimate.']
    md+=['','## Review and provenance','',
        'Inspect raw issue interpretations and provisional flags before treating scores as accurate. Repeatability and agreement with other judges are separate from semantic validity.',
        'The frozen historical prompt requests Chinese short comments. Original provider records retain their exact text for auditability; this summary and its labels are English. A different output-language instruction would require a separately identified grading condition.',
        'Driver-only continuation updates are recorded in trial_manifest.json. They do not alter the shared scoring engine, provider adapter, initial prompts or existing judgments.',
        'Detailed available scores are in three_judge_comparison.json. Three-repeat metrics are in stability_summary.json. Incomplete or review-required data are not presented as a complete numeric dataset.']
    (trial/'report.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    return stats

def evaluate_pending(path,pending,**kwargs):
    import runtime.evaluator as pipeline
    reader=pipeline.read_sources
    def selected_sources(*args,**kw):
        selected,issues=reader(*args,**kw)
        existing={s['record']['response_id'] for s in selected}
        if not pending<=existing:raise ValueError('Pending answers are absent from the original source file.')
        return [s for s in selected if s['record']['response_id'] in pending],issues
    pipeline.read_sources=selected_sources
    try:return evaluate_file(response_file=path,max_responses=len(pending),**kwargs)
    finally:pipeline.read_sources=reader

def main(preview=False,output_root=None,call_fn=None,generation_config=None,new_trial=False):
    config,sources=preflight()
    output=writable_path(output_root or OUTPUT)
    expected_config={**client.CONFIG,'adapter_sha256':sha(HERE/'client.py')}
    if call_fn is not None:
        if generation_config is None:raise ValueError('A test call must declare its generation configuration.')
        expected_config=generation_config
    existing=list(output.glob('trial_*/trial_manifest.json'))
    selected=None
    if existing and not new_trial:
        incomplete=[]
        for p in existing:
            m=json.loads(p.read_text(encoding='utf-8'))
            if m['status'] in ('incomplete','interrupted'):incomplete.append((p.parent,m))
        if len(incomplete)!=1:raise FileExistsError('Inspect existing trials before intentionally starting another with --new-trial. Exactly one incomplete trial is required for automatic resume.')
        selected=incomplete[0]
    code_paths=[p for folder in [EA/'runtime',EA/'versions/v4_12',EA/'versions/v4_11',EA/'versions/v4_10',EA/'versions/v4_3',EA/'versions/v4_2'] for p in folder.glob('*.py')]+[HERE/'main.py',HERE/'client.py']
    current_code={str(p):sha(p) for p in code_paths}
    if selected:
        trial,manifest=selected
        if (trial/'.trial.lock').exists() or list((trial/'runs').glob('gpt_judge_batch007/*/run_*/.run.lock')):raise RuntimeError('A trial lock exists; inspect the active or interrupted process before resuming.')
        if manifest['source_inputs']!=config or manifest['model']!=client.MODEL or manifest['judge_repeats']!=3:raise ValueError('Frozen trial inputs or model changed; do not mix grading conditions.')
        if manifest['generation_config']!=expected_config:raise ValueError('Provider settings changed since the incomplete trial.')
        changed=[]
        for name,h in manifest['trial_code_sha256'].items():
            if sha(name)!=h:
                if Path(name).resolve()!=Path(__file__).resolve():raise ValueError('Shared scoring engine or adapter changed: '+name)
                changed.append({'path':name,'before_sha256':h,'after_sha256':sha(name)})
        manifest['outcomes']=collect_outcomes(trial,manifest)
        allrows=collect_records(trial,manifest)
        for row in allrows:
            expected=config['expected_inputs'].get(row['response_id'])
            if expected is None or any(row.get(k)!=v for k,v in expected.items()):raise ValueError('A saved judgment does not match the frozen historical request.')
            if row['evaluator_model']!=client.MODEL or row['evaluator_generation_config']!=expected_config:raise ValueError('A saved judgment has another model or settings.')
        done={(r['judge_repeat_index'],r['response_id']) for r in allrows}
    else:
        trial=None;manifest=None;allrows=[];done=set();changed=[]
    expected={(rep,c['response_id']) for rep in range(1,4) for c in config['cohort']}
    if done-expected:raise ValueError('Unexpected saved answer/repetition pair.')
    remaining=len(expected-done)
    print(f'Frozen batch_007: 50 answers, 3 judge repeats, 150 planned initial judgments. Remaining: {remaining}. Model: {client.MODEL}',flush=True)
    if preview:
        print('Preview only: no credentials read, no API calls, no files written.',flush=True)
        return {'preview':True,'answers':50,'repeats':3,'selected':150,'remaining_initial_judgments':remaining,'resuming':bool(selected)}
    if call_fn is None:
        client.check_credentials(RA);call_fn,actual_config=client.make_model(RA)
        if actual_config!=expected_config:raise ValueError('Provider configuration changed during preflight.')
    if trial is None:
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        trial=output/('trial_'+stamp+'_'+uuid.uuid4().hex[:8]);trial.mkdir(parents=True,exist_ok=False)
        manifest={'purpose':'gpt_judge_repeatability_on_unchanged_batch007','model':client.MODEL,'judge_repeats':3,'planned_initial_judgments':150,'status':'running','outcomes':[],'rounds':{},
            'generation_config':expected_config,'source_inputs':config,'trial_code_sha256':current_code,'created_at_utc':stamp,'additional_answer_generation':False}
    if changed:manifest.setdefault('driver_updates',[]).append({'timestamp_utc':datetime.now(timezone.utc).isoformat(),'reason':'Resume remaining requests and continue after review-required records; scoring inputs and engine unchanged.','changes':changed})
    manifest['trial_code_sha256']=current_code
    manifest['status']='running'
    def save():(trial/'trial_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    lock=trial/'.trial.lock'
    with lock.open('x',encoding='utf-8') as handle:handle.write(json.dumps({'pid':os.getpid(),'started_at_utc':datetime.now(timezone.utc).isoformat()}))
    stopped=False;save()
    try:
        for repeat in range(1,4):
            round_stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
            round_id=next((rid for rid,n in manifest['rounds'].items() if n==repeat),str(uuid.uuid4()))
            manifest['rounds'][round_id]=repeat;save()
            for path in config['source_file_sha256']:
                ids={c['response_id'] for c in config['cohort'] if c['source_file']==path}
                pending={rid for rid in ids if (repeat,rid) not in done}
                if not pending:continue
                preflight()
                if any(sha(p)!=h for p,h in current_code.items()):raise ValueError('Trial code changed while running.')
                print(f'GPT judge repeat {repeat}/3 | {Path(path).name} | pending {len(pending)}',flush=True)
                outcome=evaluate_pending(path,pending,rubric_file=INPUTS/'rubric.md',evaluator_model=client.MODEL,output_dir=trial/'runs',response_agent_dir=RA,
                    call_fn=call_fn,generation_config=expected_config,checklist_file=INPUTS/'checklist.md',calibration_file=INPUTS/'calibration.md',evaluation_batch='gpt_judge_batch007',
                    round_id=round_id,round_stamp=round_stamp,allow_historical_fallback=False,expected_inputs=config['expected_inputs'])
                outcome['judge_repeat_index']=repeat;manifest['outcomes'].append(outcome);save()
                for row in rows(outcome):done.add((repeat,row['response_id']))
                attempted=outcome['scored']+outcome['needs_review']+outcome['failed']
                if attempted<len(pending):stopped=True;break
            if stopped:break
        allrows=collect_records(trial,manifest)
        if stopped:manifest['status']='incomplete'
        elif all(r['status']=='scored' for r in allrows) and len(done)==150:manifest['status']='complete'
        elif len(done)==150:manifest['status']='complete_with_review'
        else:manifest['status']='incomplete'
        save()
    except BaseException:
        manifest['status']='interrupted';save();raise
    finally:
        if lock.exists():lock.unlink()
        stats=summarize(trial)
        print('Results: '+str(trial),flush=True)
    return {'trial':str(trial),'summary':stats}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='GPT judge trial on frozen batch_007 answers; running without --preview makes API calls.')
    parser.add_argument('--preview',action='store_true');parser.add_argument('--new-trial',action='store_true')
    parser.add_argument('--summarize',type=Path)
    args=parser.parse_args()
    if args.summarize:print(json.dumps(summarize(args.summarize),ensure_ascii=False,indent=2))
    else:
        result=main(preview=args.preview,new_trial=args.new_trial)
        if not args.preview and result['summary']['status'] not in ('complete','complete_with_review'):raise SystemExit(1)
