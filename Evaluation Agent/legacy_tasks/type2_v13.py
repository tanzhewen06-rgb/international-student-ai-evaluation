from pathlib import Path
from datetime import datetime,timezone
import uuid,hashlib
from runtime import portable_json as json
from runtime.agent import DIMENSIONS,load_rubric,prepare_task
from runtime.scoring import load_scoring_contract,validate_checklist_contract
from runtime.checklist import load_checklist,prepare_checklist
from runtime.calibration import load_calibration,prepare_calibration
from runtime.storage import read_sources
from runtime.evaluator import evaluate_file,_generation_round_order
from runtime.report import write_reports
from runtime.report_dual_judge import write_comparison
from versions.v4_12.audit import prepare_audit_instructions
from versions.v4_12.stability import write_stability
from versions.v4_12.client import check_credentials


HERE=Path(__file__).resolve().parents[1]
from runtime.paths import RESPONSES_ROOT, EVALUATIONS_ROOT
EXPERIMENTS=RESPONSES_ROOT
RESPONSE_BATCH='batch_011'
# Type2 response models.
TARGET_MODELS=['gpt-5.4-nano', 'gemini-3.5-flash-lite']
RESPONSE_FILES=[EXPERIMENTS/RESPONSE_BATCH/f'responses_{model}.jsonl' for model in TARGET_MODELS]
RESPONSE_REPEATS=1
RUN_PURPOSE='type2_v1_3_conditional_reasoning_pilot'
SCENARIO_VERSION='V1.3'

RUBRIC_FILE=HERE/'versions'/'v4_12'/'prompts'/'evaluation_agent_prompt_en V4.12 Type2 V1.3.md'
CHECKLIST_FILE=HERE/'resources'/'checklists'/'type2_v1_3'/'international_student_scenario_Type2_checklist V1.3.md'
CALIBRATION_FILE=HERE/'resources'/'human_calibration'/'v3'/'evaluation_agent_human_calibration_principles V3.md'
# Type2 judges.
EVALUATOR_MODELS=['gemini-3.8-flash','deepseek-flash']
EVALUATION_BATCH='batch_011'
OUTPUT_FOLDER=EVALUATIONS_ROOT
MAX_RESPONSES=5*RESPONSE_REPEATS
PREVIEW_ONLY=False

def _run_type2_v13(preview=None):
    preview=PREVIEW_ONLY if preview is None else preview
    if len(RESPONSE_FILES)!=len(set(Path(p).resolve() for p in RESPONSE_FILES)):raise ValueError('Duplicate source file.')
    if len(EVALUATOR_MODELS)!=2 or len(set(EVALUATOR_MODELS))!=2:raise ValueError('Select two distinct judges.')
    instructions,template,rubric_hash=load_rubric(RUBRIC_FILE);contract=load_scoring_contract(instructions)
    checklist=load_checklist(CHECKLIST_FILE);validate_checklist_contract(contract,checklist,DIMENSIONS)
    reference=load_calibration(CALIBRATION_FILE)
    if reference is None:raise ValueError('Human calibration reference is required.')
    expected={f'scenario_{i}' for i in range(1,6)};cohort=[];expected_inputs={}
    for path in RESPONSE_FILES:
        path=Path(path);sources,issues=read_sources(path.parent,source_files=[path])
        if issues:raise ValueError('Input errors must be resolved before paid scoring.')
        selected=_generation_round_order(sources)
        expected_pairs={(repeat,sid) for repeat in range(1,RESPONSE_REPEATS+1) for sid in expected}
        actual_pairs=[(s['record']['repeat_index'],s['record']['scenario_id']) for s in selected]
        if len(selected)!=MAX_RESPONSES or len(actual_pairs)!=len(set(actual_pairs)) or set(actual_pairs)!=expected_pairs:
            raise ValueError(f'Each model must supply exactly {RESPONSE_REPEATS} complete repetition(s) of five scenarios ({MAX_RESPONSES} successful answers), without extra rows: '+str(path))
        if len({s['record']['run_id'] for s in selected})!=1:
            raise ValueError('Do not mix separate generation runs for one model: '+str(path))
        if any(s['record']['batch_name']!=RESPONSE_BATCH or s['record']['model_name'] not in TARGET_MODELS or path.name!=f"responses_{s['record']['model_name']}.jsonl" for s in selected):
            raise ValueError('Saved model/batch metadata does not match the selected input: '+str(path))
        for source in selected:
            record=source['record']
            if record.get('scenario_version')!=SCENARIO_VERSION:raise ValueError('Expected Type2 V1.3 saved answers; run the current Response Agent first.')
            prepare_task(template,record);prepare_checklist(checklist,record);prepare_calibration(reference,record,contract)
            effective=prepare_audit_instructions(instructions,record,contract)+prepare_checklist(checklist,record)['instructions']+prepare_calibration(reference,record,contract)
            expected_inputs[record['response_id']]={'source_sha256':source['source_sha256'],'rubric_sha256':rubric_hash,'checklist_sha256':checklist['sha256'],'calibration_sha256':reference['sha256'],
                'initial_task_sha256':hashlib.sha256(prepare_task(template,record).encode('utf-8')).hexdigest(),'initial_instructions_sha256':hashlib.sha256(effective.encode('utf-8')).hexdigest()}
            cohort.append({k:source[k] for k in ('source_file','source_line','source_sha256')}|{'response_id':record['response_id'],'scenario_id':record['scenario_id'],'target_model':record['model_name'],'repeat_index':record['repeat_index'],'generation_run_id':record['run_id']})
    if not preview:check_credentials(HERE.parent/'Response Agent',EVALUATOR_MODELS)
    print(f'{EVALUATION_BATCH} | prompt {contract["version"]} | {len(TARGET_MODELS)} target models x 5 scenarios x {RESPONSE_REPEATS} repeats x {len(EVALUATOR_MODELS)} judges = {len(cohort)*len(EVALUATOR_MODELS)} judgments',flush=True)
    print('Type2 V1.3: read batch_011 answers; run Response Agent first. Evaluation does not generate answers.',flush=True)
    print(f'Rubric: {RUBRIC_FILE.name} | SHA256: {rubric_hash}',flush=True)
    print('Results go to a new timestamped run; previous rounds remain available.',flush=True)
    round_id=str(uuid.uuid4());stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    outcomes=[]
    for judge in EVALUATOR_MODELS:
        for path in RESPONSE_FILES:
            result=evaluate_file(response_file=path,rubric_file=RUBRIC_FILE,checklist_file=CHECKLIST_FILE,calibration_file=CALIBRATION_FILE,
                evaluator_model=judge,output_dir=OUTPUT_FOLDER,max_responses=MAX_RESPONSES,preview=preview,
                evaluation_batch=EVALUATION_BATCH,round_id=round_id,round_stamp=stamp,allow_historical_fallback=False,expected_inputs=expected_inputs)
            outcomes.append(result)
            if not preview:
                for report in write_reports(result['output_dir']):print('Report: '+str(report),flush=True)

            if result['failed']:break
    if not preview and outcomes:
        destination=OUTPUT_FOLDER/EVALUATION_BATCH/'comparison'/('run_'+stamp+'_'+contract['version']+'_'+round_id[:8])
        destination.mkdir(parents=True,exist_ok=False)
        manifest={'evaluation_batch':EVALUATION_BATCH,'run_purpose':RUN_PURPOSE,'scenario_version':SCENARIO_VERSION,'scenario_type':contract.get('scenario_type','Type1'),'rubric_version':contract['version'],'rubric_sha256':rubric_hash,
            'checklist_sha256':checklist['sha256'],'calibration_sha256':reference['sha256'],'evaluation_round_id':round_id,
            'judges':EVALUATOR_MODELS,'cohort':cohort,'outcomes':outcomes,'independent_judges':True,'historical_score_reuse':False,
            'checklist_output_mode':'original_items','api_execution':'human_initiated','score_aggregation':'none','difference_flag_threshold':2,
            'shared_initial_request_hashes':expected_inputs,'stability_policy':'compare_same_judge_same_conditions_only','main_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        (destination/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
        for report in write_comparison(outcomes,destination,manifest):print('Combined report: '+str(report),flush=True)
        print('Stability data: '+str(write_stability(outcomes,destination)),flush=True)
    return outcomes

