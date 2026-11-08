"""Evaluation workflow used by the small, editable main.py entry point."""

import hashlib
from datetime import datetime, timezone
from pathlib import Path
import re
import time
import uuid

from runtime.agent import canonical_hash, judge_response, load_rubric, prepare_task, DIMENSIONS
from versions.v4_3.audit import claim_review_spans, prepare_audit_instructions
from runtime.scoring import load_scoring_contract, validate_checklist_contract
from runtime.calibration import load_calibration, prepare_calibration
from runtime.checklist import load_checklist, prepare_checklist, load_integrated_checklist
from runtime.models import load_model_layer
from runtime.storage import append_record, evaluation_session, read_sources, utc_now


# Internal defaults. User-facing settings belong in main.py.
EVALUATOR_MODEL = "gpt-6.1-sol"
BATCH_NAME = "batch_001"
MAX_RECORDS = 2
SOURCE_MODEL = None  # Internal filter; main.py explicitly selects one response file.
from runtime.paths import AGENT_ROOT, RESPONSES_ROOT, EVALUATIONS_ROOT
HERE = AGENT_ROOT
RESPONSE_AGENT_DIR = HERE.parent / "Response Agent"
RUBRIC_PATH = HERE / "versions" / "v2" / "prompts" / "evaluation_agent_prompt_en V2.md"
OUTPUT_DIR = EVALUATIONS_ROOT


def _generation_round_order(sources):
    """Keep each source generation run in repeat 1..N, scenario 1..5 order."""
    file_order={}
    run_order={}
    for source in sorted(sources,key=lambda x:(x["source_file"],x["source_line"])):
        filename=source["source_file"]
        file_order.setdefault(filename,len(file_order))
        key=(filename,str(source["record"].get("run_id","")))
        run_order.setdefault(key,len(run_order))
    def key(source):
        r=source["record"];sid=str(r.get("scenario_id",""))
        scenario=int(sid.rsplit("_",1)[-1]) if sid.rsplit("_",1)[-1].isdigit() else 0
        repeat=r.get("repeat_index",0)
        return (file_order[source["source_file"]],run_order[(source["source_file"],str(r.get("run_id","")))],repeat if type(repeat) is int else 0,scenario,source["source_line"])
    return sorted(sources,key=key)


def _safe_name(value, label):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value):
        raise ValueError(f"{label} must contain only letters, numbers, dots, underscores or hyphens, and start with a letter or number.")
    return value


def run_evaluations(*, model_name=EVALUATOR_MODEL, batch_name=BATCH_NAME,
                    limit=MAX_RECORDS, source_model=SOURCE_MODEL, dry_run=False,
                    response_agent_dir=None, rubric_path=None, output_dir=None,
                    call_fn=None, generation_config=None, source_files=None,
                    round_id=None, round_stamp=None, checklist_path=None, calibration_path=None, allow_historical_fallback=True, expected_inputs=None):
    _safe_name(batch_name, "Batch name")
    _safe_name(model_name, "Evaluator model")
    if source_model is not None:
        _safe_name(source_model, "Source model")
    if limit is not None and (type(limit) is not int or limit < 1):
        raise ValueError("Limit must be a positive integer, or None for all valid rows in this round.")
    response_dir = Path(response_agent_dir or RESPONSE_AGENT_DIR).resolve()
    prompt_path = Path(rubric_path or RUBRIC_PATH).resolve()
    output_root = Path(output_dir or OUTPUT_DIR).resolve()
    instructions, task_template, rubric_hash = load_rubric(prompt_path)
    scoring_contract = load_scoring_contract(instructions)
    source_batch = (RESPONSES_ROOT if response_agent_dir is None or response_dir == RESPONSE_AGENT_DIR.resolve() else response_dir / "experiments") / batch_name
    sources, issues = read_sources(source_batch, source_model, source_files)
    if scoring_contract["version"] in ("V4.3", "V4.4", "V4.5", "V4.6", "V4.7", "V4.8", "V4.9", "V4.10", "V4.11", "V4.12"):
        sources=_generation_round_order(sources)
    target_names = {source["record"].get("model_name") for source in sources}
    if not target_names:
        paths = source_files if source_files is not None else source_batch.glob("responses_*.jsonl")
        target_names = {Path(path).stem.removeprefix("responses_") for path in paths}
    if len(target_names) != 1:
        raise ValueError("Select one response file containing answers from exactly one target model.")
    target_model = _safe_name(next(iter(target_names)), "Target model recorded in the response file")
    selected = sources if limit is None else sources[:limit]
    integrated = load_integrated_checklist(instructions)
    if integrated is not None and checklist_path is not None:
        raise ValueError("This rubric already contains its checklist; set CHECKLIST_FILE to None to avoid duplicate instructions.")
    checklist_path = Path(checklist_path).resolve() if checklist_path is not None else None
    checklist = load_checklist(checklist_path) if checklist_path is not None else None
    validate_checklist_contract(scoring_contract, checklist, DIMENSIONS)
    calibration = load_calibration(calibration_path)
    if scoring_contract["calibration_required"] and calibration is None:
        raise ValueError("Evaluation V4 requires CALIBRATION_FILE with the user's human-rating Markdown.")
    if scoring_contract["version"]=="V4.12":
        from versions.v4_12.audit import prepare_audit_instructions as prepare_current_audit
    elif scoring_contract["version"]=="V4.11":
        from versions.v4_11.audit import prepare_audit_instructions as prepare_current_audit
    elif scoring_contract["version"]=="V4.10":
        from versions.v4_10.audit import prepare_audit_instructions as prepare_current_audit
    elif scoring_contract["version"]=="V4.9":
        from versions.v4_9.audit import prepare_audit_instructions as prepare_current_audit
    else:
        prepare_current_audit=prepare_audit_instructions
    applied_rubrics={source["record"]["response_id"]:prepare_current_audit(instructions,source["record"],scoring_contract) for source in selected}
    applied_calibrations = {source["record"]["response_id"]: prepare_calibration(calibration, source["record"], scoring_contract) for source in selected}
    applied_checklists = {
        source["record"]["response_id"]: prepare_checklist(checklist, source["record"])
        for source in selected
    } if checklist is not None else {}
    if integrated is not None:
        applied_checklists = {
            source["record"]["response_id"]: {
                "scenario_id": source["record"].get("scenario_id"),
                "scenario_sha256": source["record"].get("scenario_sha256"),
                "instructions_sha256": integrated["sha256"], "instructions": "",
            } for source in selected
        }
    checklist_hash = integrated["sha256"] if integrated is not None else checklist["sha256"] if checklist is not None else None
    checklist_mode = "integrated" if integrated is not None else "external" if checklist is not None else "none"
    checklist_label = "Integrated Checklist V2" if integrated is not None else checklist_path.name if checklist_path is not None else None
    prepared_inputs={}
    for source in selected:
        record=source['record'];rid=record['response_id']
        prepared=applied_rubrics[rid]+applied_checklists.get(rid,{}).get('instructions','')+applied_calibrations.get(rid,'')
        prepared_inputs[rid]={'source_sha256':source['source_sha256'],'rubric_sha256':rubric_hash,'checklist_sha256':checklist_hash,'calibration_sha256':calibration['sha256'] if calibration else None,
            'initial_task_sha256':hashlib.sha256(prepare_task(task_template,record).encode('utf-8')).hexdigest(),'initial_instructions_sha256':hashlib.sha256(prepared.encode('utf-8')).hexdigest()}
        if expected_inputs is not None and expected_inputs.get(rid)!=prepared_inputs[rid]:raise ValueError('Initial grading input changed after shared preflight; stop before model calls.')
    if call_fn is None:
        call_fn, actual_config = load_model_layer(response_dir, model_name, compact=scoring_contract["version"] if scoring_contract["version"] in ("V4.7","V4.8", "V4.9", "V4.10", "V4.11", "V4.12") else scoring_contract["version"]=="V4.6")
        if generation_config is not None and generation_config != actual_config:
            raise ValueError("Generation settings must match the reused model client.")
        generation_config = actual_config
    elif generation_config is None:
        generation_config = {}
    # Changes to the rubric, client, settings or scoring code create a separate scope.
    code_hashes = {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                   for name in ('runtime/agent.py', 'runtime/calibration.py', 'runtime/checklist.py', 'runtime/evaluator.py', 'runtime/finalize_scoring.py', 'runtime/models.py', 'runtime/paths.py', 'runtime/report.py', 'runtime/report_dual_judge.py', 'runtime/scoring.py', 'runtime/storage.py', 'runtime/strict_scoring.py', 'versions/v4_12/audit.py', 'versions/v4_12/client.py', 'versions/v4_12/judgment.py', 'versions/v4_12/report.py', 'versions/v4_12/stability.py', 'versions/v4_11/audit.py', 'versions/v4_11/client.py', 'versions/v4_11/judgment.py', 'versions/v4_11/report.py', 'versions/v4_11/stability.py', 'versions/v4_10/audit.py', 'versions/v4_10/client.py', 'versions/v4_10/judgment.py', 'versions/v4_10/report.py', 'versions/v4_10/stability.py', 'versions/v4_2/audit.py', 'versions/v4_3/audit.py', 'versions/v4_6/client.py', 'versions/v4_6/judgment.py', 'versions/v4_6/report.py', 'versions/v4_7/client.py', 'versions/v4_7/judgment.py', 'versions/v4_7/recovery.py', 'versions/v4_7/report.py', 'versions/v4_8/client.py', 'versions/v4_8/judgment.py', 'versions/v4_8/report.py', 'versions/v4_9/audit.py', 'versions/v4_9/client.py', 'versions/v4_9/judgment.py', 'versions/v4_9/report.py')}
    client_path = response_dir / "models.py"
    client_hash = hashlib.sha256(client_path.read_bytes()).hexdigest() if client_path.is_file() else None
    conditions = {
        "scenario_type": scoring_contract.get("scenario_type", "Type1"),
        "schema_version": "1.8" if scoring_contract["version"] in ("V4.11","V4.12") else "1.7" if scoring_contract["version"]=="V4.10" else "1.6" if scoring_contract["version"]=="V4.9" else "1.5" if scoring_contract["version"]=="V4.8" else "1.4" if scoring_contract["version"]=="V4.7" else "1.3" if scoring_contract["version"]=="V4.6" else "1.2" if scoring_contract["version"]  in ("V4.2", "V4.3", "V4.4", "V4.5", "V4.6", "V4.7", "V4.8", "V4.9", "V4.10", "V4.11", "V4.12") else "1.1" if scoring_contract["version"] == "V4.1" else "1.0", "rubric_version": scoring_contract["version"], "evaluator_model": model_name, "target_model": target_model,
        "evaluator_generation_config": generation_config,
        "checklist_output_mode": "original_items" if scoring_contract["version"] in ("V4.9","V4.10", "V4.11", "V4.12") else "legacy",
        "allow_historical_fallback": allow_historical_fallback,
        "rubric_sha256": rubric_hash, "scoring_code_sha256": code_hashes,
        "score_scale": {"min": scoring_contract["score_min"], "max": scoring_contract["score_max"]},
        "calibration_sha256": calibration["sha256"] if calibration else None,
        "score_computation": "program_minimum_from_anchor_and_audit" if scoring_contract["version"]  in ("V4.2", "V4.3", "V4.4", "V4.5", "V4.6", "V4.7", "V4.8", "V4.9", "V4.10", "V4.11", "V4.12") else "judge_declared",
        "checklist_sha256": checklist_hash, "checklist_mode": checklist_mode,
        "model_client_sha256": client_hash,
    }
    scope_hash = canonical_hash(conditions)
    round_id = str(uuid.uuid4()) if round_id is None else _safe_name(round_id, "Round ID")
    round_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") if round_stamp is None else _safe_name(round_stamp, "Round timestamp")
    run_id = str(uuid.uuid4())
    pair_name = f"{model_name}_on_{target_model}"
    pair_folder = pair_name + "_with_checklist" if checklist_mode != "none" else pair_name
    folder = output_root / batch_name / pair_folder / f"run_{round_stamp}_{round_id[:8]}"
    # Evaluation outputs are always separate from the source experiment batch.
    if folder == source_batch or source_batch in folder.parents:
        raise ValueError("Evaluation output must not be inside the source batch.")
    if source_files is not None:
        for file in source_files:
            source_parent = Path(file).resolve().parent
            if folder == source_parent or source_parent in folder.parents:
                raise ValueError("Evaluation output must be separate from the input files' folders.")
    result_file = folder / f"evaluations_{pair_name}.jsonl"
    manifest = {
        **conditions, "evaluation_round_id": round_id, "evaluation_run_id": run_id,
        "round_timestamp_utc": round_stamp, "max_responses": limit,
        "result_file": result_file.name,
        "selected_response_ids": [source["record"]["response_id"] for source in selected],
        "source_files": sorted({source["source_file"] for source in sources}),
        "calibration_file": calibration["path"].name if calibration else None,
        "calibration_source_path": str(calibration["path"]) if calibration else None,
        "calibration_snapshot": "calibration.md" if calibration else None,
        "checklist_file": checklist_label,
        "checklist_snapshot": "checklist.md" if checklist_mode != "none" else None,
        "checklist_source_path": str(prompt_path) if integrated is not None else str(checklist_path) if checklist_path is not None else None,
        "background_input": "saved_snapshot" if "{{student_background}}" in task_template else "saved_user_message",
        "applied_checklists": {
            response_id: {"scenario_id": supplement["scenario_id"],
                          "scenario_sha256": supplement["scenario_sha256"],
                          "instructions_sha256": supplement["instructions_sha256"]}
            for response_id, supplement in applied_checklists.items()
        },
    }
    if calibration and calibration.get('mode')=='one_short_example_per_scenario':
        manifest.update(calibration_mode=calibration['mode'],calibration_source_sha256=calibration['source_sha256'],
                        applied_calibration_examples={source['record']['response_id']:calibration['examples'][source['record']['scenario_id']]['example_id'] for source in selected})
    if calibration and calibration.get('mode')=='principles_only':manifest.update(calibration_mode='principles_only',calibration_source_sha256=calibration['source_sha256'])
    manifest['initial_request_hashes']=prepared_inputs
    print(f"Evaluator: {model_name} | Target: {target_model} | Batch: {batch_name}", flush=True)
    print(f"Round: {round_id}", flush=True)
    print(f"Checklist: {checklist_label or 'disabled'}", flush=True)
    print(f"Valid inputs: {len(sources)} | Input issues: {len(issues)} | Selected this round: {len(selected)}", flush=True)
    print(f"Results file: {result_file}", flush=True)
    summary = {"selected": len(selected), "scored": 0, "needs_review": 0, "failed": 0,
               "input_issues": len(issues), "output_dir": str(folder), "dry_run": dry_run,
               "evaluation_round_id": round_id, "evaluation_run_id": run_id,
               "evaluator_model": model_name, "target_model": target_model,
               "result_file": str(result_file), "checklist_sha256": checklist_hash}
    if dry_run:
        for source in selected:
            record = source["record"]
            task = prepare_task(task_template, record)
            supplement = applied_checklists.get(record["response_id"])
            judge_instructions = applied_rubrics[record["response_id"]] + (supplement["instructions"] if supplement else "") + applied_calibrations.get(record["response_id"], "")
            if calibration is not None and applied_calibrations[record["response_id"]] not in judge_instructions:
                raise ValueError("Human reference was not included in the prepared request.")
            print(f"  {record['response_id']} | {record.get('model_name', '?')} | {record.get('scenario_id', '?')}")
        print("Preview complete. No API calls; no files written.")
        return summary
    if not selected and not issues:
        print("No valid inputs selected. No API calls; no files written.")
        return summary

    consecutive_failures = 0
    with evaluation_session(folder, prompt_path, rubric_hash, manifest,
                            checklist_path=checklist_path, checklist_hash=checklist_hash,
                            checklist_text=integrated["text"] if integrated is not None else None,
                            calibration_path=calibration["path"] if calibration else None,
                            calibration_hash=calibration["sha256"] if calibration else None):
        for issue in issues:
            append_record(folder / "errors.jsonl", {**issue, "evaluator_model": model_name,
                          "target_model": target_model, "evaluation_round_id": round_id,
                          "evaluation_run_id": run_id, "timestamp_utc": utc_now()})
        for index, source in enumerate(selected, 1):
            record = source["record"]
            metadata = {
                **prepared_inputs[record["response_id"]],
                "schema_version": conditions["schema_version"], "rubric_version": scoring_contract["version"], "evaluation_id": str(uuid.uuid4()),
                "evaluation_run_id": run_id, "evaluation_round_id": round_id, "timestamp_utc": utc_now(),
                "response_id": record["response_id"], "evaluator_model": model_name,
                "target_model": target_model,
                "evaluator_generation_config": generation_config, "rubric_sha256": rubric_hash,
                "evaluation_scope_sha256": scope_hash, "source_file": source["source_file"],
                "checklist_sha256": checklist_hash, "checklist_mode": checklist_mode,
                "score_scale": conditions["score_scale"],
                "score_computation": conditions["score_computation"],
                "calibration_sha256": calibration["sha256"] if calibration else None,
                "calibration_file": calibration["path"].name if calibration else None,
                "checklist_instructions_sha256": applied_checklists.get(record["response_id"], {}).get("instructions_sha256"),
                "source_line": source["source_line"], "source_sha256": source["source_sha256"],
                "source_metadata": {name: record.get(name) for name in (
                    "model_name", "generation_config", "run_id", "batch_name", "scenario_id",
                    "scenario_name", "scenario_version", "scenario_sha256", "persona_id",
                    "persona_version", "persona_sha256", "repeat_index",
                    "student_background_file", "student_background_version", "student_background_sha256")},
            }
            if scoring_contract["version"]  in ("V4.2", "V4.3", "V4.4", "V4.5", "V4.6", "V4.7", "V4.8", "V4.9", "V4.10", "V4.11", "V4.12"):
                metadata["claim_review_spans"]=claim_review_spans(record["response_text"])
                metadata["rubric_instructions_sha256"]=hashlib.sha256(applied_rubrics[record["response_id"]].encode("utf-8")).hexdigest()
            if scoring_contract["version"] in ("V4.3", "V4.4", "V4.5", "V4.6", "V4.7", "V4.8", "V4.9", "V4.10", "V4.11", "V4.12"):
                repeat=record.get("repeat_index","?")
                total_repeats=max((x["record"].get("repeat_index",0) for x in selected if type(x["record"].get("repeat_index")) is int),default=0)
                scenario=record.get("scenario_id","?").rsplit("_",1)[-1]
                run_label=str(record.get("run_id","unknown"))[:8]
                print(f"[{index}/{len(selected)}] Generation {run_label} | Repeat {repeat}/{total_repeats or '?'} | Scenario {scenario}/5 | {record['response_id']} ...",end=" ",flush=True)
            else:
                print(f"[{index}/{len(selected)}] {record['response_id']} ...", end=" ", flush=True)
            start = time.perf_counter()
            raw_text = None
            normalization_log = []
            attempt_log = []
            try:
                task = prepare_task(task_template, record)
                supplement = applied_checklists.get(record["response_id"])
                judge_instructions = applied_rubrics[record["response_id"]] + (supplement["instructions"] if supplement else "") + applied_calibrations.get(record["response_id"], "")
                judged = judge_response(model_name, task, judge_instructions, record, call_fn, attempt_log,
                                        checklist_contract=integrated, scoring_contract=scoring_contract)
                if allow_historical_fallback and scoring_contract['version'] in ('V4.7','V4.8') and judged['needs_review']:
                    from versions.v4_7.recovery import previous_compatible_score
                    fallback=previous_compatible_score(output_root,record,scoring_contract,model_name,calibration)
                    if fallback is not None:
                        judged['evaluation']=fallback;judged['needs_review']=False
                raw_text = judged["raw_text"]
                normalization_log = judged["notes"]
                evaluation = judged["evaluation"]
            except Exception as exc:
                # Provider error text may contain request details. Store types/status only.
                last_attempt = attempt_log[-1] if attempt_log else {}
                raw_text = last_attempt.get("raw_evaluation_text")
                error = str(exc) if last_attempt.get("stage") in ("validation_error", "evidence_mismatch") else "Model request failed; check credentials, model access and network."
                failure = {**metadata, "status": "evaluation_error", "error_type": type(exc).__name__,
                           "error": error, "api_status_code": getattr(exc, "status_code", None),
                           "raw_evaluation_text": raw_text, "evaluation_attempts": attempt_log,
                           "duration_seconds": time.perf_counter() - start}
                append_record(folder / "errors.jsonl", failure)
                summary["failed"] += 1
                consecutive_failures += 1
                print(f"FAILED ({type(exc).__name__}: {error})", flush=True)
            else:
                metadata["duration_seconds"] = time.perf_counter() - start
                if "usage" in judged:metadata["usage"]=judged["usage"]
                metadata["validation_notes"] = normalization_log
                metadata["evaluation_attempts"] = attempt_log
                if evaluation["status"] == "not_evaluable":
                    append_record(folder / "errors.jsonl", {**metadata, **evaluation, "raw_evaluation_text": raw_text})
                    summary["failed"] += 1
                    consecutive_failures += 1
                    print("NOT EVALUABLE", flush=True)
                elif judged["needs_review"]:
                    review = {**metadata, **evaluation, "status": "needs_review",
                              "evidence_issues": judged["evidence_issues"], "raw_evaluation_text": raw_text}
                    append_record(folder / "needs_review.jsonl", review)
                    summary["needs_review"] += 1
                    consecutive_failures = 0
                    print("NEEDS REVIEW (" + str(evaluation.get("reason", "unresolved evidence or score consistency")) + ")", flush=True)
                else:
                    append_record(result_file, {**metadata, **evaluation, "raw_evaluation_text": raw_text})
                    summary["scored"] += 1
                    consecutive_failures = 0
                    print("OK", flush=True)
            if consecutive_failures >= 3:
                print("Stopped after three consecutive failures. Inspect errors.jsonl before continuing.", flush=True)
                break
    print(f"Completed: {summary['scored']} scored, {summary['needs_review']} need review, {summary['failed']} failed. Input issues: {len(issues)}.")
    return summary


def evaluate_file(*, response_file, rubric_file, evaluator_model, output_dir,
                   max_responses=None, preview=False, response_agent_dir=None,
                   call_fn=None, generation_config=None, checklist_file=None, calibration_file=None,
                   evaluation_batch=None, round_id=None, round_stamp=None, allow_historical_fallback=True, expected_inputs=None):
    """Run one manually configured evaluator against one target's response file."""
    if not isinstance(response_file, (str, Path)):
        raise ValueError("Set RESPONSE_FILE to one file path, not a list.")
    file = Path(response_file).resolve()
    batch_name = file.parent.name
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", batch_name):
        batch_name = "selected_files"
    return run_evaluations(
        model_name=evaluator_model, batch_name=evaluation_batch or batch_name,
        limit=max_responses, dry_run=preview, source_files=[file],
        response_agent_dir=response_agent_dir, rubric_path=rubric_file,
        output_dir=output_dir, call_fn=call_fn, generation_config=generation_config,
        checklist_path=checklist_file, calibration_path=calibration_file,
        round_id=round_id, round_stamp=round_stamp, allow_historical_fallback=allow_historical_fallback, expected_inputs=expected_inputs,
    )


