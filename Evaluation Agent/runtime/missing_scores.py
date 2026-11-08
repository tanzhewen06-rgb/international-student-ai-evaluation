"""Fill failed judgments using the original inputs and retain an explicit overlay."""
from contextlib import contextmanager
from datetime import datetime, timezone
from runtime import portable_json as json
from pathlib import Path
import uuid

from runtime import configured_evaluation as evaluation


def _key(row):
    return row['evaluator_model'], row['response_id'], row['judge_repeat_index']


def _verify(row, settings):
    expected = settings['expected_inputs'][row['response_id']]
    if any(row.get(k) != v for k, v in expected.items()):
        raise ValueError('A missing-score judgment has different original inputs.')


def _prepare(settings):
    prepared, _ = evaluation.prepare(
        response_files=list(settings['source_file_sha256']),
        response_ids=[r['response_id'] for r in settings['cohort']],
        evaluator_models=settings['evaluator_models'], rubric_file=settings['rubric_file'],
        checklist_file=settings['checklist_file'], calibration_file=settings['calibration_file'],
        repetitions=settings['judgment_repeats'], max_responses=None,
        evaluation_version=settings['revision'])
    if prepared != settings:
        raise ValueError('Inputs or scoring code changed since the original trial.')


def _collect(trial, manifest):
    trial = evaluation.writable_path(trial)
    _, originals = evaluation.collect(trial, manifest)
    settings = manifest['settings']
    expected = {(judge, r['response_id'], rep)
                for judge in settings['evaluator_models'] for r in settings['cohort']
                for rep in range(1, settings['judgment_repeats'] + 1)}
    if len(originals) != len(expected) or {_key(r) for r in originals} != expected:
        raise ValueError('Finish the original trial before supplementing failed judgments.')
    effective = {_key(r): r for r in originals}
    failed = {k for k, r in effective.items() if r['status'] != 'scored'}
    for row in originals:
        _verify(row, settings)
    attempts = []
    root = trial / 'supplements' / 'missing_scores'
    for path in sorted((root / 'runs').glob('*/*/run_*/manifest.json')):
        run = evaluation.read_json(path)
        journal = root / 'requests' / (run['evaluation_round_id'] + '.json')
        origin = run.get('missing_score_parent') or (evaluation.read_json(journal) if journal.is_file() else None)
        if not origin or origin['trial_manifest_sha256'] != evaluation.sha(trial / 'trial_manifest.json'):
            raise ValueError('A supplement belongs to a different original trial.')
        for row in evaluation.rows({'output_dir': str(path.parent)}):
            row = {**row, 'judge_repeat_index': origin['judge_repeat_index'],
                   'evaluation_version': settings['revision'], 'checklist_version': settings['revision'],
                   'numeric_protocol_version': row['rubric_version']}
            key = _key(row)
            if key not in failed:
                raise ValueError('A supplement attempts to replace an existing original score.')
            _verify(row, settings)
            if row.get('evaluator_generation_config') != manifest['provider_settings'][row['evaluator_model']]:
                raise ValueError('Supplement judge settings differ from the original trial.')
            attempts.append(row)
            if row['status'] == 'scored':
                if effective[key]['status'] == 'scored':
                    raise ValueError('Multiple successful supplements exist for one missing score.')
                effective[key] = {**row, 'supplement_parent_trial': str(trial),
                                  'supplement_result_folder': str(path.parent),
                                  'replaces_failed_evaluation_id': effective[key].get('evaluation_id')}
    return originals, effective, attempts


def _export(trial, manifest):
    originals, effective, attempts = _collect(trial, manifest)
    records = [effective[_key(r)] for r in originals]
    summary, cells = evaluation.summarize(records, manifest['settings'])
    summary.update(original_scored_judgments=sum(r['status'] == 'scored' for r in originals),
                   successful_supplements=sum('supplement_parent_trial' in r for r in records),
                   supplement_attempts=len(attempts), parent_trial=str(trial))
    root = trial / 'supplements' / 'missing_scores'
    evaluation.write_json(root / 'judgments_supplemented.json', records)
    evaluation.write_json(root / 'summary.json', {'summary': summary, 'dimension_groups': cells})
    (root / 'report.md').write_text(
        '# Missing-score supplements\n\n'
        f"Scored {summary['scored_judgments']}/{summary['planned_judgments']}; "
        f"remaining unscored {summary['unscored_judgments']}.\n\n"
        'Use judgments_supplemented.json for the combined dataset. Original judgments and error logs '
        'are unchanged. Each successful supplement replaces only its original missing judge-answer '
        'cell, with explicit provenance. Provisional scores retain their flags.\n', encoding='utf-8')
    return summary


@contextmanager
def _locked(trial, root):
    root.mkdir(parents=True, exist_ok=True)
    lock = root / '.missing_scores.lock'
    with lock.open('x', encoding='utf-8') as handle:
        import os
        handle.write(json.dumps({'pid': os.getpid()}))
    try:
        if (trial / '.trial.lock').exists() or list((root / 'runs').glob('*/*/run_*/.run.lock')):
            raise RuntimeError('The original trial or a supplement is still active.')
        yield
    finally:
        lock.unlink()


def run_missing(trial_folder, *, preview=False, new_trial=False, deepseek_timeout_seconds=300):
    if new_trial:
        raise ValueError('Missing-score recovery does not start a new full trial.')
    trial = evaluation.writable_path(trial_folder)
    manifest = evaluation.read_json(trial / 'trial_manifest.json')
    if manifest['status'] not in ('complete', 'complete_with_review') or (trial / '.trial.lock').exists():
        raise ValueError('The original trial must be finished and unlocked.')
    settings = manifest['settings']
    _, effective, _ = _collect(trial, manifest)
    pending = [key for key, row in effective.items() if row['status'] != 'scored']
    if pending:
        _prepare(settings)
    print(f"{settings['revision']} | Missing judgments: {len(pending)} | Existing scores are skipped", flush=True)
    for judge, rid, rep in pending:
        print(f'{judge} | {rid} | judge repeat {rep}', flush=True)
    if any(key[0].startswith('deepseek-') for key in pending):
        print(f'DeepSeek request timeout: {deepseek_timeout_seconds} seconds. Fresh requests only.', flush=True)
    if preview:
        print('Preview only: no credentials, API requests or output writes.', flush=True)
        return {'preview': True, 'selected': len(pending), 'pending': pending}
    if not pending:
        print('All judgments are already scored. No requests or exports repeated.', flush=True)
        return {'trial': str(trial), 'summary': evaluation.summarize(list(effective.values()), settings)[0]}
    root = trial / 'supplements' / 'missing_scores'
    with _locked(trial, root):
        _, effective, _ = _collect(trial, manifest)
        pending = [key for key, row in effective.items() if row['status'] != 'scored']
        summary = _export(trial, manifest)
        for judge in settings['evaluator_models']:
            tasks = [key for key in pending if key[0] == judge]
            if not tasks:
                continue
            call, generation = evaluation.provider(judge)
            if generation != manifest['provider_settings'][judge]:
                raise ValueError('Judge settings changed; no supplement request was sent.')
            if judge.startswith('deepseek-'):
                from runtime.deepseek_recovery import make_model
                call, generation = make_model(judge, generation, root / 'provider_diagnostics', deepseek_timeout_seconds)
            for rep in sorted({key[2] for key in tasks}):
                for source_file in settings['source_file_sha256']:
                    ids = {key[1] for key in tasks if key[2] == rep and effective[key]['source_file'] == source_file}
                    if not ids:
                        continue
                    _prepare(settings)
                    round_id = str(uuid.uuid4())
                    origin = {'trial_manifest_sha256': evaluation.sha(trial / 'trial_manifest.json'),
                              'judge_repeat_index': rep,
                              'transport_timeout_seconds': deepseek_timeout_seconds if judge.startswith('deepseek-') else 300}
                    (root / 'requests').mkdir(exist_ok=True)
                    evaluation.write_json(root / 'requests' / (round_id + '.json'), origin)
                    result = evaluation.evaluate_pending(
                        source_file, ids, rubric_file=Path(settings['rubric_file']), evaluator_model=judge,
                        output_dir=root / 'runs', response_agent_dir=evaluation.RA, call_fn=call,
                        generation_config=generation, checklist_file=Path(settings['checklist_file']),
                        calibration_file=Path(settings['calibration_file']),
                        evaluation_batch=settings['revision'].lower().replace('.', '_'),
                        round_id=round_id,
                        round_stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ'),
                        allow_historical_fallback=False, expected_inputs=settings['expected_inputs'])
                    path = Path(result['output_dir']) / 'manifest.json'
                    metadata = evaluation.read_json(path)
                    metadata['missing_score_parent'] = origin
                    evaluation.write_json(path, metadata)
                    summary = _export(trial, manifest)
        print(f"Scored {summary['scored_judgments']}/{summary['planned_judgments']}; "
              f"missing {summary['unscored_judgments']}", flush=True)
        print('Combined results: ' + str(root / 'judgments_supplemented.json'), flush=True)
        return {'trial': str(trial), 'summary': summary}
