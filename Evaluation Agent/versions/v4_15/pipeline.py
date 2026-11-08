from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from runtime import portable_json as json
import os
import uuid

from gpt_judge_stability.main import writable_path
from gpt_judge_stability.client import MODEL as GPT_MODEL
from runtime.evaluator import _generation_round_order
from runtime.paths import RESPONSE_AGENT_ROOT
from runtime.storage import read_sources
from runtime.agent import DIMENSIONS
from .client import make_model
from .protocol import VERSION, FLOW_REVISION, STAGES, sha, sha_text, load_protocol, phase_request, parse_object, validate_phase, final_dimensions

HERE = Path(__file__).resolve().parent

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, path)

def prepare(arguments):
    files = [Path(p).resolve() for p in arguments['response_files']]
    judges = list(arguments['evaluator_models'])
    ids = arguments['response_ids']
    limit = arguments['max_responses']
    if not files or len(files) != len(set(files)) or not judges or len(judges) != len(set(judges)):
        raise ValueError('Select distinct response files and judge models.')
    if any(not (j == GPT_MODEL or j.startswith(('deepseek-', 'gemini-'))) for j in judges):
        raise ValueError('Select tested judge model IDs.')
    if type(arguments['repetitions']) is not int or arguments['repetitions'] < 1:
        raise ValueError('Evaluation repetitions must be a positive integer.')
    if limit is not None and (type(limit) is not int or limit < 1):
        raise ValueError('MAX_RESPONSES must be a positive integer or None.')
    requested = None if ids is None else set(ids)
    if requested is not None and (not requested or len(requested) != len(ids)):
        raise ValueError('RESPONSE_IDS must be None or distinct selected IDs.')
    protocol = load_protocol(arguments['rubric_file'], arguments['checklist_file'], arguments['calibration_file'])
    selected = []
    for file in files:
        sources, issues = read_sources(file.parent, source_files=[file])
        if issues:
            raise ValueError('Resolve response input errors before scoring.')
        if len({s['record']['model_name'] for s in sources}) != 1:
            raise ValueError('One response writer is required per source file.')
        chosen = [s for s in _generation_round_order(sources) if requested is None or s['record']['response_id'] in requested]
        selected.extend(chosen if limit is None else chosen[:limit])
    found = [s['record']['response_id'] for s in selected]
    if not selected or len(found) != len(set(found)) or requested is not None and set(found) != requested:
        raise ValueError('Selected response IDs are missing, duplicated or excluded by the per-file limit.')
    expected = {}
    cohort = []
    for source in selected:
        record = source['record']
        rid = record['response_id']
        if not rid or any(not c.isascii() or not (c.isalnum() or c in '-_') for c in rid):
            raise ValueError('Response IDs must use letters, numbers, hyphens or underscores.')
        if protocol['calibration'] and rid in protocol['calibration']['response_ids']:
            raise ValueError('Do not evaluate a labeled calibration answer as a test answer.')
        requests = {phase: phase_request(protocol, record, phase) for phase in STAGES}
        expected[rid] = {'source_sha256': source['source_sha256'], 'rubric_sha256': protocol['rubric_sha256'],
            'checklist_sha256': protocol['checklist']['sha256'], 'calibration_sha256': protocol['calibration']['sha256'],
            'phase_requests': {phase: {'input_sha256': sha_text(task), 'instructions_sha256': sha_text(instructions)} for phase, (task, instructions) in requests.items()}}
        cohort.append({k: source[k] for k in ('source_file', 'source_line', 'source_sha256')} |
                      {'response_id': rid, 'scenario_id': record['scenario_id'], 'target_model': record['model_name'], 'repeat_index': record['repeat_index']})
    settings = {'revision': VERSION, 'evaluation_version': VERSION, 'checklist_version': VERSION, 'numeric_protocol_version': VERSION,
        'workflow_revision': FLOW_REVISION, 'evaluation_order': protocol['contract']['dimension_order'],
        'evaluator_models': judges, 'judgment_repeats': arguments['repetitions'], 'cohort': cohort, 'expected_inputs': expected,
        'source_file_sha256': {str(p): sha(p) for p in files}, 'rubric_file': str(Path(arguments['rubric_file']).resolve()),
        'checklist_file': str(Path(arguments['checklist_file']).resolve()), 'calibration_sha256': protocol['calibration']['sha256'] if protocol['calibration'] else None,
        'code_sha256': {str(p): sha(p) for p in [HERE / 'pipeline.py', HERE / 'protocol.py', HERE / 'client.py', RESPONSE_AGENT_ROOT / 'models.py',
            RESPONSE_AGENT_ROOT.parent / 'Evaluation Agent' / 'runtime' / 'agent.py',
            RESPONSE_AGENT_ROOT.parent / 'Evaluation Agent' / 'runtime' / 'checklist.py',
            RESPONSE_AGENT_ROOT.parent / 'Evaluation Agent' / 'runtime' / 'calibration.py',
            RESPONSE_AGENT_ROOT.parent / 'Evaluation Agent' / 'runtime' / 'storage.py',
            RESPONSE_AGENT_ROOT.parent / 'Evaluation Agent' / 'gpt_judge_stability' / 'client.py',
            RESPONSE_AGENT_ROOT.parent / 'Evaluation Agent' / 'versions' / 'v4_12' / 'client.py']},
        'score_computation': 'D1_D6_min_rubric_normalized_checklist; other_dimensions_rubric_only',
        'max_attempts_per_stage': protocol['contract']['max_attempts_per_stage']}
    return settings, selected, protocol

def stage(name, state, path, model, call, task, instructions, validator, maximum, count):
    work = state['stages'].setdefault(name, {'attempts': []})
    if 'result' in work:
        return work['result'], work['quality_flags']
    for cached in work['attempts']:
        response = cached.get('response')
        if not isinstance(response, dict) or not response.get('text'):
            continue
        reported = response.get('provider_model')
        if isinstance(reported, str) and reported.removeprefix('models/') != model:
            continue
        if response.get('provider_status') not in (None, 'completed'):
            continue
        try:
            value, parse_flags = parse_object(response['text'])
            result, flags = validator(value)
            work.update(result=result, quality_flags=parse_flags + flags)
            write_json(path, state)
            return result, work['quality_flags']
        except (ValueError, TypeError, KeyError):
            pass
    while len(work['attempts']) < maximum:
        diagnostic = work.get('last_error')
        repair = '' if not diagnostic else '\n\nRepair only the diagnosed stage structure. Return the complete required object. Do not invent evidence or a preferred score. Diagnostic: ' + diagnostic
        actual_instructions = instructions + repair
        attempt = {'stage': name, 'attempt': len(work['attempts']) + 1, 'status': 'started', 'model': model,
            'input': task, 'instructions': actual_instructions, 'input_sha256': sha_text(task), 'instructions_sha256': sha_text(actual_instructions)}
        work['attempts'].append(attempt)
        write_json(path, state)
        try:
            response = call(model, task, actual_instructions, name, count)
            response = response if isinstance(response, dict) else {'text': response}
            attempt.update(status='received', response=response)
            write_json(path, state)
            reported = response.get('provider_model')
            if isinstance(reported, str) and reported.removeprefix('models/') != model:
                raise ValueError('Provider reported a different judge model.')
            if response.get('provider_status') not in (None, 'completed'):
                raise ValueError('Provider returned an incomplete stage response.')
            value, parse_flags = parse_object(response['text'])
            result, flags = validator(value)
            work.update(result=result, quality_flags=parse_flags + flags)
            attempt['status'] = 'accepted'
            write_json(path, state)
            return result, work['quality_flags']
        except Exception as exc:
            attempt.update(status='invalid' if isinstance(exc, (ValueError, TypeError, KeyError)) else 'request_error', error_type=type(exc).__name__)
            work['last_error'] = str(exc)[:500] if isinstance(exc, (ValueError, TypeError, KeyError)) else 'Provider request failed: ' + type(exc).__name__
            attempt['diagnostic'] = work['last_error']
            write_json(path, state)
        except BaseException as exc:
            attempt.update(status='interrupted', error_type=type(exc).__name__)
            write_json(path, state)
            raise
    return None, []

def assess(source, model, repeat, protocol, settings, provider, trial):
    record = source['record']
    rid = record['response_id']
    folder = trial / 'attempts' / model / ('repetition_' + str(repeat))
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (rid + '.json')
    identity = {'response_id': rid, 'judge': model, 'judge_repeat_index': repeat,
                'inputs': settings['expected_inputs'][rid], 'provider_settings': provider[1], 'code_sha256': settings['code_sha256']}
    state = read_json(path) if path.exists() else {'identity': identity, 'stages': {}}
    if state['identity'] != identity:
        raise ValueError('An attempt cache belongs to different inputs or provider settings.')
    if 'record' in state:
        return state['record']
    maximum = settings['max_attempts_per_stage']
    n = len(protocol['orders'][record['scenario_id']])
    results = {}
    flags = []
    failed = None
    for phase in STAGES:
        task, instructions = phase_request(protocol, record, phase)
        assessed, phase_flags = stage(phase, state, path, model, provider[0], task, instructions,
            lambda v: validate_phase(v, protocol, record, phase), maximum, n)
        if assessed is None:
            failed = phase
            break
        results[phase] = assessed
        flags.extend(phase_flags)
    base = {**settings['expected_inputs'][rid], 'schema_version': '2.0', 'rubric_version': VERSION, 'evaluation_version': VERSION,
        'checklist_version': VERSION, 'numeric_protocol_version': VERSION, 'response_id': rid, 'evaluator_model': model,
        'target_model': record['model_name'], 'judge_repeat_index': repeat, 'source_file': source['source_file'],
        'source_line': source['source_line'], 'source_metadata': {k: record.get(k) for k in ('batch_name', 'scenario_id', 'scenario_name', 'repeat_index', 'run_id', 'scenario_sha256')},
        'evaluator_generation_config': provider[1], 'score_computation': settings['score_computation'],
        'workflow_revision': FLOW_REVISION, 'evaluation_order': settings['evaluation_order']}
    attempts = [a for name in STAGES for a in state['stages'].get(name, {}).get('attempts', [])]
    if failed:
        result = {**base, 'status': 'needs_review', 'score_status': 'unscored', 'failed_stage': failed,
            'reason': state['stages'][failed].get('last_error', 'Stage incomplete.'), 'evaluation_attempts': attempts,
            'partial_assessments': results, 'trace_file': str(path)}
    else:
        dims = final_dimensions(results, flags)
        understanding, factual = results['understanding']['checklist'], results['factual']['checklist']
        findings = {cid: {'status': 'met' if item['met'] and factual['findings'][cid]['met'] else 'unmet',
            'understanding_met': item['met'], 'reliability_met': factual['findings'][cid]['met'],
            'assessments': {'D1': item, 'D6': factual['findings'][cid]}} for cid, item in understanding['findings'].items()}
        accounting = {'item_count': n, 'unmet_counts': {'D1': understanding['unmet_count'], 'D6': factual['unmet_count']},
            'checklist_scores': {'D1': understanding['checklist_score'], 'D6': factual['checklist_score']}}
        result = {**base, 'status': 'scored', 'score_status': 'provisional' if flags else 'validated', 'dimensions': dims,
            'checklist_findings': findings, 'checklist_accounting': accounting, 'dimension_assessments': results,
            'quality_flags': flags, 'issues': [], 'evaluation_attempts': attempts, 'trace_file': str(path)}
    state['record'] = result
    write_json(path, state)
    return result

def save_results(trial, manifest, records):
    settings = manifest['settings']
    expected = len(settings['cohort']) * len(settings['evaluator_models']) * settings['judgment_repeats']
    scored = [r for r in records if r['status'] == 'scored']
    status = 'complete' if len(scored) == expected else 'complete_with_review' if len(records) == expected else 'incomplete'
    attempts = [a for p in (trial / 'attempts').glob('*/*/*.json') for stage_state in read_json(p)['stages'].values() for a in stage_state['attempts']]
    summary = {'status': status, 'revision': VERSION, 'planned_judgments': expected, 'saved_judgments': len(records),
        'scored_judgments': len(scored), 'unscored_judgments': len(records) - len(scored),
        'remaining_initial_judgments': expected - len(records), 'provider_requests': len(attempts),
        'interrupted_or_unknown_requests': sum(a['status'] in ('started', 'interrupted') for a in attempts),
        'score_status': dict(Counter(r['score_status'] for r in records))}
    by_judge = {}
    for judge in settings['evaluator_models']:
        rows = [r for r in scored if r['evaluator_model'] == judge]
        by_judge[judge] = {'numeric_records': len(rows), 'means': {d: mean(r['dimensions'][d]['score'] for r in rows) if rows else None for d in DIMENSIONS}}
    write_json(trial / 'judgments.json', records)
    write_json(trial / 'summary.json', {'summary': summary, 'judges': by_judge})
    lines = ['# V4.15 dimension-ordered evaluation', '',
        'Evaluation Prompt order: D2 empathy, D3 culture/autonomy, D4 clarity, D5 practicality, D6 factual reliability, D1 problem understanding. D2-D5 are completed without any Checklist input. Only D6 and D1 consult dimension-specific Checklist guidance within their own assessment.', '',
        f'Status: {status}. Numeric judgments: {len(scored)}/{expected}. Recorded provider requests: {summary["provider_requests"]}.', '',
        'D1 and D6 use min(rubric anchor, corresponding Checklist score). D2-D5 retain their independent rubric anchors and are not revised after later Checklist assessments. Scores are integers; an omission is not automatically a fabricated fact.', '',
        'Each stage permits four attempts total. Successful stages are cached. Exhausted stages remain explicit failures; no zero or high score is invented. Auxiliary explanation/quotation problems are flagged rather than invalidating otherwise complete numeric structure.', '',
        'Workflow revision: dimension_ordered. This replaces the earlier Checklist-first V4.15 flow; cache identities prevent its reuse. Keep different workflow conditions separate. These are pilot design rules, not calibrated ground-truth probabilities.', '',
        '| Judge | Numeric records | ' + ' | '.join('D' + str(i) for i in range(1, 7)) + ' |',
        '| --- | ---: | ' + ' | '.join(['---:'] * 6) + ' |']
    for judge, data in by_judge.items():
        lines.append('| ' + judge + f' | {data["numeric_records"]} | ' + ' | '.join(f'{data["means"][d]:.2f}' if data['means'][d] is not None else 'NA' for d in DIMENSIONS) + ' |')
    (trial / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return summary

def run(*, response_files, response_ids, evaluator_models, rubric_file, checklist_file, calibration_file,
        output_folder, repetitions=1, max_responses=None, evaluation_version=VERSION, preview=False, new_trial=False, providers=None):
    if evaluation_version != VERSION:
        raise ValueError('Select the V4.15 protocol and version together.')
    arguments = dict(response_files=response_files, response_ids=response_ids, evaluator_models=evaluator_models,
        rubric_file=rubric_file, checklist_file=checklist_file, calibration_file=calibration_file,
        repetitions=repetitions, max_responses=max_responses)
    settings, selected, protocol = prepare(arguments)
    output = writable_path(output_folder)
    resolved = Path(output_folder).resolve()
    if any(Path(p).parent == resolved or Path(p).parent in resolved.parents for p in settings['source_file_sha256']):
        raise ValueError('Output must be separate from response input folders.')
    matches = []
    if not new_trial:
        matches = [(p.parent, read_json(p)) for p in sorted(output.glob('trial_*/trial_manifest.json')) if read_json(p).get('settings') == settings]
    unfinished = [pair for pair in matches if pair[1]['status'] in ('running', 'interrupted', 'incomplete')]
    if len(unfinished) > 1:
        raise ValueError('Inspect multiple unfinished matching trials before continuing.')
    trial, manifest = unfinished[0] if unfinished else matches[-1] if matches else (None, None)
    if trial is not None and (trial / '.trial.lock').exists():
        raise RuntimeError('A matching trial has an active or unresolved lock.')
    records = []
    cached_states = {}
    if trial is not None:
        allowed = {(j, s['record']['response_id'], repeat) for j in evaluator_models for s in selected for repeat in range(1, repetitions + 1)}
        for p in (trial / 'attempts').glob('*/*/*.json'):
            state = read_json(p)
            identity = state['identity']
            key = (identity['judge'], identity['response_id'], identity['judge_repeat_index'])
            if (key not in allowed or identity['inputs'] != settings['expected_inputs'][key[1]]
                    or identity['code_sha256'] != settings['code_sha256']
                    or identity['provider_settings'] != manifest['provider_settings'][key[0]]):
                raise ValueError('A cached assessment does not match this trial.')
            cached_states[key] = state
            if 'record' in state:
                row = state['record']
                if (row['evaluator_model'], row['response_id'], row['judge_repeat_index']) != key or any(row.get(k) != v for k, v in identity['inputs'].items()):
                    raise ValueError('A saved judgment does not match its assessment identity.')
                records.append(row)
    total = len(selected) * len(evaluator_models) * repetitions
    done = {(r['evaluator_model'], r['response_id'], r['judge_repeat_index']) for r in records}
    if len(done) != len(records):
        raise ValueError('Duplicate completed assessment.')
    remaining = total - len(done)
    pending = {(j, s['record']['response_id'], repeat) for j in evaluator_models for s in selected for repeat in range(1, repetitions + 1)} - done
    ordinary_requests = sum('result' not in cached_states.get(key, {}).get('stages', {}).get(phase, {}) for key in pending for phase in STAGES)
    print(f'{evaluation_version} | Judges: {", ".join(evaluator_models)} | {len(selected)} saved answers x {len(evaluator_models)} judges x {repetitions} repeats = {total} tasks | remaining {remaining}', flush=True)
    print('Response files: ' + ', '.join(str(p) for p in response_files), flush=True)
    if preview:
        print('Preview only: no credentials, API requests or output writes.', flush=True)
        return {'preview': True, 'answers': len(selected), 'judges': list(evaluator_models), 'selected': total,
                'remaining_initial_judgments': remaining, 'normal_provider_requests': ordinary_requests, 'max_attempts_per_stage': 4,
                'workflow_revision': FLOW_REVISION, 'evaluation_order': settings['evaluation_order']}
    if not remaining:
        print('These exact tasks are already attempted. No requests repeated.', flush=True)
        summary = save_results(trial, manifest, records)
        if manifest['status'] != summary['status']:
            manifest['status'] = summary['status']
            write_json(trial / 'trial_manifest.json', manifest)
        return {'trial': str(trial), 'summary': summary}
    providers = providers if providers is not None else {j: make_model(j) for j in evaluator_models}
    if set(providers) != set(evaluator_models):
        raise ValueError('Provider models do not match the configured judge list.')
    provider_settings = {j: pair[1] for j, pair in providers.items()}
    if trial is None:
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        trial = output / ('trial_' + stamp + '_' + uuid.uuid4().hex[:8])
        trial.mkdir(parents=True, exist_ok=False)
        manifest = {'revision': VERSION, 'settings': settings, 'provider_settings': provider_settings, 'status': 'running',
                    'created_at_utc': stamp, 'api_execution': 'human_initiated'}
    elif manifest['provider_settings'] != provider_settings:
        raise ValueError('Provider settings changed during a trial.')
    lock = trial / '.trial.lock'
    with lock.open('x', encoding='utf-8') as handle:
        handle.write(json.dumps({'pid': os.getpid()}))
    manifest['status'] = 'running'
    write_json(trial / 'trial_manifest.json', manifest)
    try:
        for repeat in range(1, repetitions + 1):
            for judge in evaluator_models:
                print(f'Evaluator: {judge}', flush=True)
                print(f'Round: {repeat}', flush=True)
                for source in selected:
                    key = (judge, source['record']['response_id'], repeat)
                    if key in done:
                        continue
                    if prepare(arguments)[0] != settings:
                        raise ValueError('Inputs or protocol code changed during evaluation.')
                    print(f'[{selected.index(source) + 1}/{len(selected)}] Generation {str(source["record"].get("run_id", "unknown"))[:8]} | Repeat {source["record"].get("repeat_index", "?")}/{max((s["record"].get("repeat_index", 0) for s in selected), default=0) or "?"} | Scenario {source["record"]["scenario_id"].rsplit("_", 1)[-1]}/5 | {source["record"]["response_id"]} ...', end=' ', flush=True)
                    result = assess(source, judge, repeat, protocol, settings, providers[judge], trial)
                    records.append(result)
                    done.add(key)
                    summary = save_results(trial, manifest, records)
                    print('OK' if result['status'] == 'scored' else 'NEEDS REVIEW (' + str(result.get('reason', 'unresolved evidence or score consistency')) + ')', flush=True)
        summary = save_results(trial, manifest, records)
        print(f'Completed: {summary["scored_judgments"]} scored, {summary["unscored_judgments"]} need review, 0 failed. Input issues: 0.', flush=True)
        manifest['status'] = summary['status']
        write_json(trial / 'trial_manifest.json', manifest)
    except BaseException:
        manifest['status'] = 'interrupted'
        write_json(trial / 'trial_manifest.json', manifest)
        save_results(trial, manifest, records)
        raise
    finally:
        lock.unlink(missing_ok=True)
    return {'trial': str(trial), 'summary': summary}
