from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import hashlib
from runtime import portable_json as json
import os
import uuid

from gpt_judge_stability import client as gpt_client
from gpt_judge_stability.main import writable_path, rows, evaluate_pending
from runtime.agent import DIMENSIONS, load_rubric, prepare_task
from runtime.calibration import load_calibration, prepare_calibration
from runtime.checklist import load_checklist, prepare_checklist
from runtime.evaluator import _generation_round_order
from runtime.models import load_model_layer
from runtime.paths import AGENT_ROOT as EA, RESPONSE_AGENT_ROOT as RA, relocated_path, path_key
from runtime.scoring import load_scoring_contract, validate_checklist_contract
from runtime.storage import read_sources
from versions.v4_12.audit import prepare_audit_instructions

sha = lambda p: hashlib.sha256(relocated_path(p).read_bytes()).hexdigest()
sha_text = lambda s: hashlib.sha256(s.encode('utf-8')).hexdigest()

def read_json(path):
    return json.loads(relocated_path(path).read_text(encoding='utf-8'))

def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def prepare(*, response_files, response_ids, evaluator_models, rubric_file, checklist_file,
            calibration_file, repetitions, max_responses, evaluation_version):
    files = [Path(p).resolve() for p in response_files]
    judges = list(evaluator_models)
    if not files or len(files) != len(set(files)):
        raise ValueError('Select distinct response files.')
    if not judges or len(judges) != len(set(judges)):
        raise ValueError('Select distinct evaluator models.')
    if any(not (j in gpt_client.MODEL_CONFIGS or j.startswith(('gemini-', 'deepseek-'))) for j in judges):
        raise ValueError('Select a tested GPT, Gemini or DeepSeek judge model.')
    if type(repetitions) is not int or repetitions < 1:
        raise ValueError('EVALUATION_REPEATS must be a positive integer.')
    if max_responses is not None and (type(max_responses) is not int or max_responses < 1):
        raise ValueError('MAX_RESPONSES must be a positive integer or None.')
    requested = None if response_ids is None else set(response_ids)
    if requested is not None and (not requested or len(requested) != len(response_ids)):
        raise ValueError('RESPONSE_IDS must be None or a nonempty list of distinct IDs.')
    rubric_file, checklist_file, calibration_file = map(lambda p: Path(p).resolve(), (rubric_file, checklist_file, calibration_file))
    ins, template, rubric_hash = load_rubric(rubric_file)
    contract = load_scoring_contract(ins)
    if contract['version'] != 'V4.12':
        raise ValueError('This entry uses the V4.12-compatible numeric scoring contract.')
    checklist = load_checklist(checklist_file)
    calibration = load_calibration(calibration_file)
    if calibration is None:
        raise ValueError('Select the required calibration reference.')
    validate_checklist_contract(contract, checklist, DIMENSIONS)
    selected = []
    all_ids = set()
    for path in files:
        sources, errors = read_sources(path.parent, source_files=[path])
        if errors:
            raise ValueError('Resolve source input errors before scoring: ' + str(path))
        if len({s['record']['model_name'] for s in sources}) != 1:
            raise ValueError('Each response file must contain one response model.')
        candidates = _generation_round_order(sources)
        if requested is not None:
            candidates = [s for s in candidates if s['record']['response_id'] in requested]
        if max_responses is not None:
            candidates = candidates[:max_responses]
        for source in candidates:
            rid = source['record']['response_id']
            if rid in all_ids:
                raise ValueError('Duplicate response ID across selected files.')
            all_ids.add(rid)
            selected.append(source)
    if not selected or requested is not None and all_ids != requested:
        raise ValueError('Some selected IDs are absent or excluded by MAX_RESPONSES.')
    expected = {}
    cohort = []
    for source in selected:
        record = source['record']
        rid = record['response_id']
        instructions = prepare_audit_instructions(ins, record, contract) + prepare_checklist(checklist, record)['instructions'] + prepare_calibration(calibration, record, contract)
        expected[rid] = {'source_sha256': source['source_sha256'], 'rubric_sha256': rubric_hash,
                         'checklist_sha256': checklist['sha256'], 'calibration_sha256': calibration['sha256'],
                         'initial_task_sha256': sha_text(prepare_task(template, record)),
                         'initial_instructions_sha256': sha_text(instructions)}
        cohort.append({k: source[k] for k in ('source_file', 'source_line', 'source_sha256')} |
                      {'response_id': rid, 'scenario_id': record['scenario_id'], 'target_model': record['model_name'],
                       'repeat_index': record['repeat_index'], 'generation_run_id': record['run_id']})
    settings = {'revision': evaluation_version, 'evaluator_models': judges, 'judgment_repeats': repetitions,
                'cohort': cohort, 'expected_inputs': expected,
                'evaluation_version': evaluation_version, 'checklist_version': evaluation_version, 'numeric_protocol_version': contract['version'],
                'source_file_sha256': {str(p): sha(p) for p in files},
                'rubric_file': str(rubric_file), 'checklist_file': str(checklist_file), 'calibration_file': str(calibration_file),
                'scoring_files_sha256': {str(p): sha(p) for p in [EA / 'runtime/agent.py', EA / 'runtime/evaluator.py',
                    EA / 'runtime/scoring.py', EA / 'runtime/strict_scoring.py', EA / 'runtime/finalize_scoring.py',
                    EA / 'runtime/checklist.py', EA / 'runtime/calibration.py', EA / 'versions/v4_12/audit.py',
                    EA / 'versions/v4_12/judgment.py', EA / 'versions/v4_12/client.py',
                    EA / 'gpt_judge_stability/client.py', RA / 'models.py']}}
    return settings, selected

def collect(trial, manifest):
    trial = writable_path(trial)
    outcomes = list(manifest['outcomes'])
    known = {path_key(o['output_dir']) for o in outcomes}
    for path in (trial / 'runs').glob('*/*/run_*/manifest.json'):
        if path_key(path.parent) in known:
            continue
        run = read_json(path)
        rep = manifest['rounds'].get(run['evaluation_round_id'])
        if rep is not None:
            outcomes.append({'output_dir': str(path.parent), 'judge_repeat_index': rep})
    records = []
    seen = set()
    for outcome in outcomes:
        for row in rows(outcome):
            row['judge_repeat_index'] = outcome['judge_repeat_index']
            version = manifest.get('settings', {}).get('revision', manifest.get('revision'))
            if version:
                row['evaluation_version'] = version
                row['checklist_version'] = version
                row['numeric_protocol_version'] = row['rubric_version']
            key = (row['evaluator_model'], row['response_id'], row['judge_repeat_index'])
            if key in seen:
                raise ValueError('Duplicate judge, answer and repetition.')
            seen.add(key)
            records.append(row)
    return outcomes, records

def compatible(manifest, settings):
    if 'settings' in manifest:
        return manifest['settings'] == settings
    old = manifest.get('source_inputs', {})
    matches = (manifest.get('revision') == settings['revision'] and
            settings['evaluator_models'] == [manifest.get('model')] and
            old.get('judgment_repeats') == settings['judgment_repeats'] and
            old.get('expected_inputs') == settings['expected_inputs'] and
            old.get('source_file_sha256') == settings['source_file_sha256'])
    if matches:
        for outcome in manifest['outcomes']:
            run = read_json(Path(outcome['output_dir']) / 'manifest.json')
            if any(sha(EA / name) != digest for name, digest in run['scoring_code_sha256'].items()):
                return False
            if run.get('model_client_sha256') != sha(RA / 'models.py'):
                return False
        expected_provider = {**gpt_client.CONFIG, 'adapter_sha256': sha(EA / 'gpt_judge_stability/client.py')}
        if manifest.get('generation_config') != expected_provider:
            return False
    return matches

def summarize(records, settings):
    n = len(settings['cohort']) * len(settings['evaluator_models']) * settings['judgment_repeats']
    scored = [r for r in records if r['status'] == 'scored']
    grouped = defaultdict(list)
    for row in scored:
        grouped[(row['evaluator_model'], row['response_id'])].append(row)
    cells = []
    for (judge, rid), rr in grouped.items():
        rr.sort(key=lambda r: r['judge_repeat_index'])
        if len(rr) != settings['judgment_repeats']:
            continue
        for d in DIMENSIONS:
            values = [r['dimensions'][d]['score'] for r in rr]
            cells.append({'evaluator_model': judge, 'response_id': rid, 'dimension': d,
                          'scores': values, 'range': max(values) - min(values)})
    status = 'complete' if len(scored) == n else 'complete_with_review' if len(records) == n else 'incomplete'
    return {'status': status, 'revision': settings['revision'], 'planned_judgments': n,
            'saved_judgments': len(records), 'scored_judgments': len(scored),
            'unscored_judgments': len(records) - len(scored), 'remaining_initial_judgments': n - len(records),
            'score_status': dict(Counter(r.get('score_status', 'unscored') for r in records)),
            'complete_dimension_groups': len(cells), 'all_repeats_equal': sum(c['range'] == 0 for c in cells),
            'max_spread': max((c['range'] for c in cells), default=None)}, cells

def provider(model):
    if model in gpt_client.MODEL_CONFIGS:
        gpt_client.check_credentials(RA)
        return gpt_client.make_model(RA,model)
    from versions.v4_12.client import check_credentials
    check_credentials(RA, [model])
    return load_model_layer(RA, model, compact='V4.12')

def run(*, response_files, response_ids, evaluator_models, rubric_file, checklist_file, calibration_file,
        output_folder, repetitions=3, max_responses=None, evaluation_version='V4.14', preview=False,
        new_trial=False, providers=None):
    arguments = dict(response_files=response_files, response_ids=response_ids, evaluator_models=evaluator_models,
                     rubric_file=rubric_file, checklist_file=checklist_file, calibration_file=calibration_file,
                     repetitions=repetitions, max_responses=max_responses, evaluation_version=evaluation_version)
    settings, selected = prepare(**arguments)
    resolved_output = Path(output_folder).resolve()
    if any(Path(p).parent == resolved_output or Path(p).parent in resolved_output.parents for p in settings['source_file_sha256']):
        raise ValueError('The output folder must be separate from response source folders.')
    output = writable_path(output_folder)
    candidates = []
    if not new_trial:
        for path in sorted(output.glob('trial_*/trial_manifest.json')):
            manifest = read_json(path)
            if compatible(manifest, settings):
                candidates.append((path.parent, manifest))
    unfinished = [pair for pair in candidates if pair[1]['status'] in ('running', 'interrupted', 'incomplete')]
    if len(unfinished) > 1:
        raise ValueError('Multiple matching unfinished runs; inspect them before continuing.')
    trial, manifest = unfinished[0] if unfinished else candidates[-1] if candidates else (None, None)
    records = []
    if trial is not None:
        if (trial / '.trial.lock').exists() or list((trial / 'runs').glob('*/*/run_*/.run.lock')):
            raise RuntimeError('A matching run is active or has an unresolved lock.')
        outcomes, records = collect(trial, manifest)
        for row in records:
            if any(row.get(k) != v for k, v in settings['expected_inputs'][row['response_id']].items()):
                raise ValueError('A saved judgment has different scoring inputs.')
    expected = {(judge, r['response_id'], rep) for judge in evaluator_models for r in settings['cohort'] for rep in range(1, repetitions + 1)}
    done = {(r['evaluator_model'], r['response_id'], r['judge_repeat_index']) for r in records}
    if not done <= expected:
        raise ValueError('The run contains unexpected judge/answer/repetition pairs.')
    remaining = len(expected - done)
    print(f'{evaluation_version} | Judges: {", ".join(evaluator_models)} | {len(selected)} saved answers x {len(evaluator_models)} judges x {repetitions} repeats = {len(expected)} tasks | remaining {remaining}', flush=True)
    print('Response files: ' + ', '.join(str(p) for p in response_files), flush=True)
    if preview:
        print('Preview only: no credentials, API requests or output writes.', flush=True)
        return {'preview': True, 'answers': len(selected), 'judges': list(evaluator_models), 'selected': len(expected), 'remaining_initial_judgments': remaining}
    if not remaining:
        print('These exact tasks are already attempted. No requests repeated.', flush=True)
        return {'trial': str(trial), 'summary': summarize(records, settings)[0]}
    providers = providers if providers is not None else {judge: provider(judge) for judge in evaluator_models}
    if set(providers) != set(evaluator_models):
        raise ValueError('Provider models do not match EVALUATOR_MODELS.')
    provider_settings = {judge: pair[1] for judge, pair in providers.items()}
    if trial is None:
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        trial = output / ('trial_' + stamp + '_' + uuid.uuid4().hex[:8])
        trial.mkdir(parents=True, exist_ok=False)
        manifest = {'revision': evaluation_version, 'settings': settings, 'status': 'running',
                    'created_at_utc': stamp, 'provider_settings': provider_settings, 'outcomes': [], 'rounds': {}}
    else:
        prior = manifest.get('provider_settings', {manifest.get('model'): manifest.get('generation_config')})
        if prior != provider_settings:
            raise ValueError('Provider settings changed during the unfinished run.')
        manifest['outcomes'] = outcomes
    save = lambda: write_json(trial / 'trial_manifest.json', manifest)
    lock = trial / '.trial.lock'
    with lock.open('x', encoding='utf-8') as handle:
        handle.write(json.dumps({'pid': os.getpid()}))
    manifest['status'] = 'running'
    save()
    try:
        stopped = False
        for rep in range(1, repetitions + 1):
            round_id = next((rid for rid, value in manifest['rounds'].items() if value == rep), str(uuid.uuid4()))
            manifest['rounds'][round_id] = rep
            save()
            for judge in evaluator_models:
                for path in settings['source_file_sha256']:
                    ids = {r['response_id'] for r in settings['cohort'] if r['source_file'] == path}
                    pending = {rid for rid in ids if (judge, rid, rep) not in done}
                    if not pending:
                        continue
                    if prepare(**arguments)[0] != settings:
                        raise ValueError('Configured inputs changed during execution.')
                    call, generation = providers[judge]
                    result = evaluate_pending(path, pending, rubric_file=Path(rubric_file), evaluator_model=judge,
                        output_dir=trial / 'runs', response_agent_dir=RA, call_fn=call, generation_config=generation,
                        checklist_file=Path(checklist_file), calibration_file=Path(calibration_file), evaluation_batch=evaluation_version.lower().replace('.', '_'),
                        round_id=round_id, round_stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ'),
                        allow_historical_fallback=False, expected_inputs=settings['expected_inputs'])
                    run_manifest = Path(result['output_dir']) / 'manifest.json'
                    run_metadata = read_json(run_manifest)
                    run_metadata.update(evaluation_version=evaluation_version, checklist_version=evaluation_version, numeric_protocol_version=run_metadata['rubric_version'])
                    write_json(run_manifest, run_metadata)
                    result['judge_repeat_index'] = rep
                    manifest['outcomes'].append(result)
                    save()
                    for row in rows(result):
                        done.add((row['evaluator_model'], row['response_id'], rep))
                    if result['scored'] + result['needs_review'] + result['failed'] < len(pending):
                        stopped = True
                        break
                if stopped:
                    break
            if stopped:
                break
        _, records = collect(trial, manifest)
        summary, cells = summarize(records, settings)
        manifest['status'] = summary['status']
        save()
        write_json(trial / 'gpt_judgments.json' if len(evaluator_models) == 1 and evaluator_models[0] == gpt_client.MODEL else trial / 'judgments.json', records)
        write_json(trial / 'stability_summary.json', {'summary': summary, 'dimension_groups': cells})
        report = ['# Configured evaluation', '', f'Version: {evaluation_version}. Status: {summary["status"]}.', '',
                  f'Judges: {", ".join(evaluator_models)}. Answers: {len(selected)}. Repetitions: {repetitions}.', '',
                  f'Attempted {len(records)}/{len(expected)}; scored {summary["scored_judgments"]}; unscored {summary["unscored_judgments"]}.', '',
                  'Review flags and missing scores remain visible. Missing scores are not zeros. Repeatability does not establish semantic accuracy.']
        (trial / 'report.md').write_text('\n'.join(report) + '\n', encoding='utf-8')
    except BaseException:
        manifest['status'] = 'interrupted'
        save()
        raise
    finally:
        lock.unlink(missing_ok=True)
    return {'trial': str(trial), 'summary': summary}
