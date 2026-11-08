from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, stdev
import argparse
import hashlib
from runtime import portable_json as json
import os
import uuid

from gpt_judge_stability import main as baseline
from runtime.agent import DIMENSIONS, load_rubric, prepare_task
from runtime.calibration import load_calibration, prepare_calibration
from runtime.checklist import load_checklist, prepare_checklist
from runtime.paths import AGENT_ROOT as EA, RESPONSE_AGENT_ROOT as RA, EVALUATIONS_ROOT
from runtime.scoring import load_scoring_contract, validate_checklist_contract
from versions.v4_12.audit import prepare_audit_instructions
from . import client
from .prompts import REVISION

HERE = Path(__file__).resolve().parent
OUTPUT = EVALUATIONS_ROOT / 'gpt_judge_v4_13_batch007'
REPEATS = 3
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
sha_text = lambda s: hashlib.sha256(s.encode('utf-8')).hexdigest()

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def preflight(suite='regression'):
    original, sources = baseline.preflight()
    revision = read_json(HERE / 'revision_manifest.json')
    if revision['revision'] != REVISION:
        raise ValueError('Unexpected review revision.')
    for name, digest in revision['files_sha256'].items():
        if sha(HERE / name) != digest:
            raise ValueError('Review revision changed: ' + name)
    if suite not in ('regression', 'complement', 'full'):
        raise ValueError('Unknown answer suite.')
    regression = set(revision['regression_response_ids'])
    all_ids = {s['record']['response_id'] for s in sources}
    if not regression <= all_ids or len(regression) != 10:
        raise ValueError('Invalid regression cohort.')
    selected_ids = regression if suite == 'regression' else all_ids - regression if suite == 'complement' else all_ids
    ins, template, rh = load_rubric(HERE / 'inputs/rubric_type1.md')
    contract = load_scoring_contract(ins)
    original_contract = load_scoring_contract(load_rubric(baseline.INPUTS / 'rubric.md')[0])
    if contract != original_contract:
        raise ValueError('V4.13 must preserve the entire original scoring contract.')
    checklist = load_checklist(baseline.INPUTS / 'checklist.md')
    calibration = load_calibration(baseline.INPUTS / 'calibration.md')
    validate_checklist_contract(contract, checklist, DIMENSIONS)
    selected = [s for s in sources if s['record']['response_id'] in selected_ids]
    cohort = [r for r in original['cohort'] if r['response_id'] in selected_ids]
    hashes = {}
    for source in selected:
        record = source['record']
        rid = record['response_id']
        instructions = prepare_audit_instructions(ins, record, contract) + prepare_checklist(checklist, record)['instructions'] + prepare_calibration(calibration, record, contract)
        hashes[rid] = {'source_sha256': source['source_sha256'], 'rubric_sha256': rh,
                       'checklist_sha256': checklist['sha256'], 'calibration_sha256': calibration['sha256'],
                       'initial_task_sha256': sha_text(prepare_task(template, record)),
                       'initial_instructions_sha256': sha_text(instructions)}
        old = original['expected_inputs'][rid]
        for field in ('source_sha256', 'checklist_sha256', 'calibration_sha256', 'initial_task_sha256'):
            if hashes[rid][field] != old[field]:
                raise ValueError('Saved answer, task, checklist or reference changed.')
        if hashes[rid]['initial_instructions_sha256'] == old['initial_instructions_sha256']:
            raise ValueError('The revised instructions were not applied.')
    config = {'revision': REVISION, 'suite': suite, 'cohort': cohort, 'expected_inputs': hashes,
              'source_file_sha256': original['source_file_sha256'], 'revision_manifest_sha256': sha(HERE / 'revision_manifest.json'),
              'historical_baseline_sha256': sha(baseline.BASELINES / 'baseline.json'),
              'output_language': 'English', 'judgment_repeats': REPEATS,
              'score_contract_changed': False, 'additional_answer_generation': False}
    return config, selected

def collect(trial, manifest):
    outcomes = list(manifest['outcomes'])
    known = {str(Path(o['output_dir'])) for o in outcomes}
    for path in (trial / 'runs').glob('v4_13/*/run_*/manifest.json'):
        if str(path.parent) in known:
            continue
        run = read_json(path)
        rep = manifest['rounds'].get(run['evaluation_round_id'])
        if rep is not None:
            outcomes.append({'output_dir': str(path.parent), 'judge_repeat_index': rep})
    records = []
    seen = set()
    for outcome in outcomes:
        for row in baseline.rows(outcome):
            row['judge_repeat_index'] = outcome['judge_repeat_index']
            key = (row['response_id'], row['judge_repeat_index'])
            if key in seen:
                raise ValueError('Duplicate answer and judge repetition.')
            seen.add(key)
            records.append(row)
    return outcomes, records

def summarize(trial, manifest):
    _, records = collect(trial, manifest)
    grouped = defaultdict(list)
    for row in records:
        if row['status'] == 'scored':
            grouped[row['response_id']].append(row)
    cells = []
    for rid, rows in grouped.items():
        rows.sort(key=lambda r: r['judge_repeat_index'])
        if len(rows) != REPEATS:
            continue
        for dimension in DIMENSIONS:
            values = [r['dimensions'][dimension]['score'] for r in rows]
            cells.append({'response_id': rid, 'dimension': dimension, 'scores': values,
                          'range': max(values) - min(values), 'sample_sd': stdev(values),
                          'all_validated': all(r.get('score_status') == 'validated' for r in rows)})
    expected = len(manifest['source_inputs']['cohort']) * REPEATS
    scored = sum(r['status'] == 'scored' for r in records)
    status = 'complete' if scored == expected else 'complete_with_review' if len(records) == expected else 'incomplete'
    stats = {'status': status, 'revision': REVISION, 'suite': manifest['source_inputs']['suite'],
             'planned_judgments': expected, 'saved_judgments': len(records), 'scored_judgments': scored,
             'unscored_judgments': len(records) - scored, 'remaining_initial_judgments': expected - len(records),
             'complete_triplicate_answers': len(cells) // 6, 'complete_dimension_triplets': len(cells),
             'all_three_same': sum(c['range'] == 0 for c in cells),
             'all_three_within_1': sum(c['range'] <= 1 for c in cells),
             'spread_at_least_2': sum(c['range'] >= 2 for c in cells),
             'max_spread': max((c['range'] for c in cells), default=None),
             'mean_within_answer_sample_sd': mean(c['sample_sd'] for c in cells) if cells else None,
             'score_status': dict(Counter(r.get('score_status', 'unscored') for r in records)),
             'logged_requests': sum(len(r.get('evaluation_attempts', [])) for r in records)}
    write_json(trial / 'gpt_judgments.json', records)
    write_json(trial / 'stability_summary.json', {'summary': stats, 'dimension_triplets': cells})
    lines = ['# GPT judge: V4.13 on saved batch 007 answers', '',
             f'Revision: {REVISION}. Suite: {stats["suite"]}. Status: {status}.', '',
             f'Attempted {len(records)}/{expected}; scored {scored}; unscored {len(records)-scored}; remaining {expected-len(records)}.', '',
             'Same original answers, task, checklist, scoring contract, reference and provider settings; revised evaluation instructions and English output. This is a new judging condition. Do not merge its raw records into the frozen historical trial.', '',
             f'Complete three-score answers: {len(cells)//6}. Complete dimension triplets: {len(cells)}.', '',
             '| Measure | Count |', '| --- | ---: |',
             f'| Three identical scores | {stats["all_three_same"]} |',
             f'| All scores within one point | {stats["all_three_within_1"]} |',
             f'| Spread at least two points | {stats["spread_at_least_2"]} |',
             f'| Largest spread | {stats["max_spread"]} |', '',
             'Stability uses only complete triplets. Missing scores are not zeros. Provisional records remain labeled. Check semantic correctness as well as repeatability; automated validation cannot establish either by itself.', '',
             'The regression suite deliberately targets previously observed problems. Its results are not representative of all models or scenarios. The complement suite contains the other 40 saved answers; it is not an independently collected blind dataset. Revised English instructions are another changed condition, so an observed improvement cannot be attributed solely to the decision checks.', '',
             'No answer generation or historical-score reuse is performed. Launching this entry without --preview makes paid model calls.']
    (trial / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return stats

def main(preview=False, suite='regression', new_trial=False, output_root=None, call_fn=None, generation_config=None):
    config, sources = preflight(suite)
    output = baseline.writable_path(output_root or OUTPUT) / suite
    actual_config = {**client.CONFIG, 'adapter_sha256': sha(baseline.HERE / 'client.py')}
    if call_fn is not None:
        if generation_config is None:
            raise ValueError('Offline test calls must declare their generation settings.')
        actual_config = generation_config
    candidates = sorted(output.glob('trial_*/trial_manifest.json'))
    trial = None
    manifest = None
    if candidates and not new_trial:
        incomplete = [(p.parent, read_json(p)) for p in candidates if read_json(p)['status'] in ('incomplete', 'interrupted', 'running')]
        if len(incomplete) > 1:
            raise ValueError('Multiple unfinished trials; inspect them before resuming.')
        trial, manifest = incomplete[0] if incomplete else (candidates[-1].parent, read_json(candidates[-1]))
        if manifest['source_inputs'] != config or manifest['generation_config'] != actual_config:
            raise ValueError('The existing trial has different inputs or provider settings.')
        if (trial / '.trial.lock').exists() or list((trial / 'runs').glob('v4_13/*/run_*/.run.lock')):
            raise RuntimeError('A run lock exists; inspect the active process before continuing.')
        manifest['outcomes'], records = collect(trial, manifest)
    else:
        records = []
    expected = {(r['response_id'], rep) for r in config['cohort'] for rep in range(1, REPEATS + 1)}
    done = {(r['response_id'], r['judge_repeat_index']) for r in records}
    if not done <= expected:
        raise ValueError('Unexpected saved answer or repetition.')
    for row in records:
        if any(row.get(k) != v for k, v in config['expected_inputs'][row['response_id']].items()):
            raise ValueError('Saved judgment does not match this revision.')
        if row['evaluator_model'] != client.MODEL or row['evaluator_generation_config'] != actual_config:
            raise ValueError('Saved judgment uses different provider settings.')
    remaining = len(expected - done)
    print(f'{REVISION} | {suite} | {len(sources)} saved answers x {REPEATS} repeats = {len(expected)} initial judgments | remaining {remaining} | {client.MODEL}', flush=True)
    if preview:
        print('Preview only: no credentials read, no API calls, no files written.', flush=True)
        return {'preview': True, 'answers': len(sources), 'repeats': REPEATS, 'selected': len(expected), 'remaining_initial_judgments': remaining}
    if not remaining:
        print('This trial is already attempted. Inspect its report; use --new-trial only to intentionally repeat it.', flush=True)
        return {'trial': str(trial), 'summary': summarize(trial, manifest)}
    if call_fn is None:
        client.check_credentials(RA)
        call_fn, provider_config = client.make_model(RA)
        if provider_config != actual_config:
            raise ValueError('Provider configuration changed.')
    if trial is None:
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        trial = output / ('trial_' + stamp + '_' + uuid.uuid4().hex[:8])
        trial.mkdir(parents=True, exist_ok=False)
        manifest = {'revision': REVISION, 'model': client.MODEL, 'source_inputs': config,
                    'generation_config': actual_config, 'created_at_utc': stamp, 'status': 'running',
                    'outcomes': [], 'rounds': {}, 'api_execution': 'human_initiated'}
    save = lambda: write_json(trial / 'trial_manifest.json', manifest)
    lock = trial / '.trial.lock'
    with lock.open('x', encoding='utf-8') as handle:
        handle.write(json.dumps({'pid': os.getpid()}))
    manifest['status'] = 'running'
    save()
    try:
        stopped = False
        for rep in range(1, REPEATS + 1):
            round_id = next((rid for rid, n in manifest['rounds'].items() if n == rep), str(uuid.uuid4()))
            manifest['rounds'][round_id] = rep
            save()
            for path in config['source_file_sha256']:
                ids = {r['response_id'] for r in config['cohort'] if r['source_file'] == path}
                pending = {rid for rid in ids if (rid, rep) not in done}
                if not pending:
                    continue
                if preflight(suite)[0] != config:
                    raise ValueError('Judging inputs changed during execution.')
                print(f'Judge repetition {rep}/{REPEATS} | {Path(path).name} | {len(pending)} pending', flush=True)
                result = baseline.evaluate_pending(path, pending, rubric_file=HERE / 'inputs/rubric_type1.md',
                    evaluator_model=client.MODEL, output_dir=trial / 'runs', response_agent_dir=RA,
                    call_fn=call_fn, generation_config=actual_config, checklist_file=baseline.INPUTS / 'checklist.md',
                    calibration_file=baseline.INPUTS / 'calibration.md', evaluation_batch='v4_13',
                    round_id=round_id, round_stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ'),
                    allow_historical_fallback=False, expected_inputs=config['expected_inputs'])
                result['judge_repeat_index'] = rep
                manifest['outcomes'].append(result)
                save()
                for row in baseline.rows(result):
                    done.add((row['response_id'], rep))
                if result['scored'] + result['needs_review'] + result['failed'] < len(pending):
                    stopped = True
                    break
            if stopped:
                break
        stats = summarize(trial, manifest)
        manifest['status'] = stats['status']
        save()
    except BaseException:
        manifest['status'] = 'interrupted'
        save()
        raise
    finally:
        lock.unlink(missing_ok=True)
    print('Results: ' + str(trial), flush=True)
    return {'trial': str(trial), 'summary': stats}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='V4.13: GPT judges saved answers; without --preview this makes API calls.')
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--suite', choices=['regression', 'complement', 'full'], default='regression')
    parser.add_argument('--new-trial', action='store_true')
    args = parser.parse_args()
    result = main(preview=args.preview, suite=args.suite, new_trial=args.new_trial)
    if not args.preview and result['summary']['status'] not in ('complete', 'complete_with_review'):
        raise SystemExit(1)
