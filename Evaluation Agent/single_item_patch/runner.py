"""Reuse frozen evaluation code; maintain a separate, explicit score overlay."""
import copy
import csv
from datetime import datetime, timezone
import hashlib
from runtime import portable_json as json
from pathlib import Path
import time
import uuid

from runtime.paths import relocated_path
from runtime.agent import DIMENSIONS, load_rubric, prepare_task, judge_response
from runtime.calibration import load_calibration, prepare_calibration
from runtime.checklist import load_checklist, prepare_checklist
from runtime.models import load_model_layer
from runtime.scoring import load_scoring_contract, validate_checklist_contract
from runtime.storage import read_sources, append_record, utc_now
from versions.v4_12.audit import prepare_audit_instructions


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(relocated_path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def rows(path):
    path = Path(path)
    return [json.loads(s) for s in path.read_text(encoding="utf-8-sig").splitlines() if s.strip()] if path.exists() else []


def inside(root, path):
    path = relocated_path(path).resolve()
    if not path.is_relative_to(relocated_path(root).resolve()):
        raise ValueError("Path is outside the selected evaluation directory.")
    return path


def dimensions(value):
    if value == "all" or value == ["all"]:
        return list(DIMENSIONS)
    values = [value] if isinstance(value, str) else value
    aliases = {f"D{i}": d for i, d in enumerate(DIMENSIONS, 1)}
    result = [aliases.get(v.upper(), v) for v in values]
    if not result or len(set(result)) != len(result) or any(d not in DIMENSIONS for d in result):
        raise ValueError("Dimensions must be all, D1-D6, or canonical names; no duplicates.")
    return result


def base_rows(pair, manifest):
    result = {}
    for name in (manifest["result_file"], "needs_review.jsonl", "errors.jsonl"):
        for row in rows(inside(pair, pair/name)):
            rid = row["response_id"]
            if rid in result:
                raise ValueError("Duplicate original judgment; inspect the original logs.")
            result[rid] = row
    return result


def effective_pair(pair, manifest):
    """Flat per-dimension records, never represented as fresh full judgments."""
    original = base_rows(pair, manifest)
    result = {}
    for rid in manifest["selected_response_ids"]:
        row = original.get(rid, {})
        result[rid] = {
            "response_id": rid, "target_model": manifest["target_model"],
            "evaluator_model": manifest["evaluator_model"],
            "original_status": row.get("status", "not_executed"),
            "source_sha256": row.get("source_sha256"), "dimensions": {},
        }
        if row.get("status") == "scored":
            for d, score in row.get("dimensions", {}).items():
                result[rid]["dimensions"][d] = {
                    **copy.deepcopy(score), "provenance": "original",
                    "evaluation_id": row.get("evaluation_id"),
                    "score_status": score.get("score_status", row.get("score_status")),
                }
    for file in sorted((pair/"supplements").glob("patch_*/accepted_patch.json")):
        patch = read_json(file)
        if patch["parent_manifest_sha256"] != sha((pair/"manifest.json").read_bytes()):
            raise ValueError("A supplement belongs to a different parent manifest.")
        if patch["parent_evaluation_run_id"] != manifest["evaluation_run_id"]:
            raise ValueError("Supplement run mismatch.")
        target = result[patch["response_id"]]
        if target["source_sha256"] not in (None, patch["source_sha256"]):
            raise ValueError("Supplement source mismatch.")
        target["source_sha256"] = patch["source_sha256"]
        for d, score in patch["dimensions"].items():
            if d not in DIMENSIONS:
                raise ValueError("Unknown supplemented dimension.")
            target["dimensions"][d] = {**score, "provenance": str(file), "patch_id": patch["patch_id"]}
    for row in result.values():
        row["status"] = "complete" if len(row["dimensions"]) == 6 else "partial" if row["dimensions"] else "missing"
    return result


def prepare(agent_root, args):
    root = Path(agent_root).resolve()
    comparison = inside(root/"evaluations", root/"evaluations"/args.batch/"comparison"/args.run)
    cm = read_json(comparison/"manifest.json")
    if cm["evaluation_batch"] != args.batch or cm["rubric_version"] != "V4.12":
        raise ValueError("This patch supports the saved V4.12 batch only.")
    outcomes = [o for o in cm["outcomes"] if o["target_model"] == args.target and o["evaluator_model"] == args.judge]
    if len(outcomes) != 1:
        raise ValueError("Select exactly one original target/judge pair.")
    pair = inside(root/"evaluations"/args.batch, outcomes[0]["output_dir"])
    manifest = read_json(pair/"manifest.json")
    if (manifest["evaluation_round_id"] != cm["evaluation_round_id"] or
        manifest["evaluator_model"] != args.judge or manifest["target_model"] != args.target):
        raise ValueError("Original pair does not match the comparison manifest.")
    if not manifest.get("scoring_code_sha256"):
        raise ValueError("Original scoring-code hashes are required.")
    for relative, expected in manifest["scoring_code_sha256"].items():
        if sha(inside(root, root/relative).read_bytes()) != expected:
            raise ValueError("Scoring code changed since the original run: " + relative)
    response_root = root.parent/"Response Agent"
    if sha((response_root/"models.py").read_bytes()) != manifest["model_client_sha256"]:
        raise ValueError("Response Agent API client changed since the original run.")
    sources, issues = read_sources(response_root/"experiments"/args.batch, source_files=manifest["source_files"])
    if issues:
        raise ValueError("Original response source has input errors; inspect it first.")
    selected = [s for s in sources if s["record"]["response_id"] in manifest["selected_response_ids"]
                and s["record"]["model_name"] == args.target
                and (args.scenario is None or s["record"]["scenario_id"] == args.scenario)
                and (args.repeat is None or s["record"].get("repeat_index") == args.repeat)
                and (args.response_id is None or s["record"]["response_id"] == args.response_id)]
    if len(selected) != 1:
        raise ValueError(f"Selectors matched {len(selected)} answers; specify one exact answer.")
    source = selected[0]; record = source["record"]; rid = record["response_id"]
    cohort = [r for r in cm["cohort"] if r["response_id"] == rid and r["target_model"] == args.target]
    if len(cohort) != 1 or cohort[0]["source_sha256"] != source["source_sha256"]:
        raise ValueError("Original comparison cohort/source hash mismatch.")
    snapshot_paths = {"rubric": pair/"rubric.md", "checklist": inside(pair, pair/manifest["checklist_snapshot"]),
                      "calibration": inside(pair, pair/manifest["calibration_snapshot"])}
    snapshots = {k: p.read_bytes() for k, p in snapshot_paths.items()}
    for key, raw in snapshots.items():
        if sha(raw) != manifest[key+"_sha256"]:
            raise ValueError("Original snapshot changed: " + key)
    instructions, template, rubric_hash = load_rubric(snapshot_paths["rubric"])
    contract = load_scoring_contract(instructions)
    if contract["version"] != "V4.12":
        raise ValueError("Only V4.12 is supported.")
    checklist = load_checklist(snapshot_paths["checklist"])
    validate_checklist_contract(contract, checklist, DIMENSIONS)
    calibration = load_calibration(snapshot_paths["calibration"])
    effective = (prepare_audit_instructions(instructions, record, contract)
                 + prepare_checklist(checklist, record)["instructions"]
                 + prepare_calibration(calibration, record, contract))
    task = prepare_task(template, record)
    hashes = {"source_sha256": source["source_sha256"], "rubric_sha256": rubric_hash,
              "checklist_sha256": checklist["sha256"], "calibration_sha256": calibration["sha256"],
              "initial_task_sha256": sha(task.encode()), "initial_instructions_sha256": sha(effective.encode())}
    if hashes != manifest["initial_request_hashes"][rid] or hashes != cm["shared_initial_request_hashes"][rid]:
        raise ValueError("Prepared request differs from the original request.")
    call_fn, config = load_model_layer(response_root, args.judge, compact="V4.12")
    if config != manifest["evaluator_generation_config"]:
        raise ValueError("Judge generation settings changed since the original run.")
    chosen = dimensions(args.dimensions)
    existing = effective_pair(pair, manifest)[rid]
    if not args.allow_rejudge and not getattr(args, "refresh_only", False) and any(d in existing["dimensions"] for d in chosen):
        raise ValueError("A selected dimension already has a score. Use --allow-rejudge for an intentional new judgment.")
    return dict(root=root, comparison=comparison, comparison_manifest=cm, pair=pair, manifest=manifest,
                source=source, task=task, instructions=effective, contract=contract, hashes=hashes,
                dimensions=chosen, call_fn=call_fn, config=config, snapshots=snapshots,
                allow_rejudge=args.allow_rejudge, parent_manifest_sha256=sha((pair/"manifest.json").read_bytes()))


def describe(case):
    r = case["source"]["record"]
    return (f"{case['manifest']['evaluator_model']} -> {r['model_name']} | {r['scenario_id']} | repeat {r.get('repeat_index')}\n"
            f"Response: {r['response_id']}\nAccept: {', '.join(case['dimensions'])}\n"
            "Original saved prompt, checklist, reference, code, source and request hashes verified.\n"
            "One full six-dimension judgment; at most one standard repair. Only selected dimensions are accepted.")


def refresh_comparison(case, patch_id):
    """Dedicated combined exports; original reports/logs remain immutable."""
    cm = case["comparison_manifest"]
    lookup = {}
    for outcome in cm["outcomes"]:
        pair = inside(case["root"]/"evaluations"/cm["evaluation_batch"], outcome["output_dir"])
        manifest = read_json(pair/"manifest.json")
        for rid, row in effective_pair(pair, manifest).items():
            key = (row["target_model"], rid, row["evaluator_model"])
            if key in lookup:
                raise ValueError("Duplicate combined score record.")
            lookup[key] = row
    result = []
    for source in cm["cohort"]:
        for judge in cm["judges"]:
            row = copy.deepcopy(lookup[(source["target_model"], source["response_id"], judge)])
            if row["source_sha256"] not in (None, source["source_sha256"]):
                raise ValueError("Combined score/source mismatch.")
            row.update(scenario_id=source["scenario_id"], repeat_index=source.get("repeat_index"),
                       evaluation_round_id=cm["evaluation_round_id"])
            result.append(row)
    folder = case["comparison"]/"supplemented"/patch_id
    folder.mkdir(parents=True, exist_ok=False)
    write_json(folder/"effective_scores.json", result)
    with (folder/"effective_scores.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        header = ["target_model", "evaluator_model", "scenario_id", "repeat_index", "response_id", "status"]
        extra = [d+"_"+suffix for d in DIMENSIONS for suffix in ("comment", "score_status", "provenance")]
        writer = csv.DictWriter(handle, fieldnames=header+list(DIMENSIONS)+extra)
        writer.writeheader()
        for row in result:
            writer.writerow({**{k: row[k] for k in header},
                             **{d: row["dimensions"].get(d, {}).get("score") for d in DIMENSIONS},
                             **{d+"_"+s: row["dimensions"].get(d, {}).get(s) for d in DIMENSIONS for s in ("comment", "score_status", "provenance")}})
    counts = {s: sum(r["status"] == s for r in result) for s in ("complete", "partial", "missing")}
    write_json(folder/"summary.json", {"counts": counts, "parent_comparison": str(case["comparison"]),
                                     "created_at_utc": utc_now(), "patch_id": patch_id,
                                     "note": "Per-dimension overlay; full evidence stays in original/supplement judgment files. Usage is not recomputed."})
    return folder/"effective_scores.csv"


def execute(case, *, call_fn=None):
    pair = case["pair"]; manifest = case["manifest"]; r = case["source"]["record"]
    # Exclusive pair lock spans selection, API request, acceptance and exports.
    lock = pair/".single_item_patch.lock"
    try:
        with lock.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps({"pid": __import__("os").getpid(), "started": utc_now()}))
    except FileExistsError:
        raise ValueError("A patch is already running for this pair. If interrupted, inspect .single_item_patch.lock before removing it.") from None
    try:
        if sha((pair/"manifest.json").read_bytes()) != case["parent_manifest_sha256"]:
            raise ValueError("Original manifest changed after preparation.")
        existing = effective_pair(pair, manifest)[r["response_id"]]
        if not case["allow_rejudge"] and any(d in existing["dimensions"] for d in case["dimensions"]):
            raise ValueError("A selected score was already supplemented. No request sent.")
        patch_id = "patch_"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")+"_"+uuid.uuid4().hex[:8]
        folder = pair/"supplements"/patch_id
        folder.mkdir(parents=True, exist_ok=False)
        metadata = {**case["hashes"], "patch_id": patch_id, "timestamp_utc": utc_now(),
                    "parent_manifest_sha256": case["parent_manifest_sha256"],
                    "parent_evaluation_run_id": manifest["evaluation_run_id"],
                    "evaluation_round_id": manifest["evaluation_round_id"],
                    "response_id": r["response_id"], "target_model": manifest["target_model"],
                    "evaluator_model": manifest["evaluator_model"], "rubric_version": "V4.12",
                    "evaluator_generation_config": case["config"], "selected_dimensions": case["dimensions"],
                    "source_file": case["source"]["source_file"], "source_line": case["source"]["source_line"],
                    "source_metadata": {k: r.get(k) for k in ("scenario_id", "repeat_index", "run_id")},
                    "allow_rejudge": case["allow_rejudge"], "historical_score_reuse": False}
        write_json(folder/"manifest.json", metadata)
        for name, data in case["snapshots"].items():
            (folder/(name+".md")).write_bytes(data)
        (folder/"task.txt").write_text(case["task"], encoding="utf-8")
        (folder/"instructions.txt").write_text(case["instructions"], encoding="utf-8")
        attempts = []; started = time.perf_counter()
        try:
            judged = judge_response(manifest["evaluator_model"], case["task"], case["instructions"], r,
                                    call_fn or case["call_fn"], attempts, checklist_contract=None,
                                    scoring_contract=case["contract"])
        except Exception as exc:
            append_record(folder/"errors.jsonl", {**metadata, "status": "evaluation_error",
                          "error_type": type(exc).__name__, "api_status_code": getattr(exc, "status_code", None),
                          "error": "Model request failed. Inspect credentials/model access/network.",
                          "evaluation_attempts": attempts, "duration_seconds": time.perf_counter()-started})
            return {"folder": folder, "status": "evaluation_error"}
        evaluation = judged["evaluation"]
        append_record(folder/"judgment.jsonl", {**metadata, **evaluation, "raw_evaluation_text": judged["raw_text"],
                      "evaluation_attempts": attempts, "validation_notes": judged["notes"],
                      "usage": judged.get("usage"), "duration_seconds": time.perf_counter()-started})
        if judged["needs_review"]:
            return {"folder": folder, "status": "needs_review"}
        patch = {**metadata, "status": "scored", "dimensions": {
            d: {**evaluation["dimensions"][d], "score_status": evaluation["dimensions"][d].get("score_status", evaluation.get("score_status"))}
            for d in case["dimensions"]}}
        # Acceptance is atomic; an interrupted provider call never becomes a score.
        pending = folder/"accepted_patch.pending.json"
        write_json(pending, patch)
        pending.replace(folder/"accepted_patch.json")
        try:
            summary = refresh_comparison(case, patch_id)
        except Exception as exc:
            write_json(folder/"completion.json", {"status": "scored", "export_status": "failed",
                                                 "error_type": type(exc).__name__, "recovery": "Run --refresh-only; no new API call."})
            return {"folder": folder, "status": "scored", "export_pending": True}
        write_json(folder/"completion.json", {"status": "scored", "combined_scores": str(summary)})
        return {"folder": folder, "status": "scored", "summary": summary}
    finally:
        lock.unlink()
