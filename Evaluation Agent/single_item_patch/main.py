"""Single saved-answer check with selected-dimension output."""
from pathlib import Path
import argparse
import sys

# Edit these settings, then run this file. No edits to the normal main.py.
BATCH = "batch_007"
COMPARISON_RUN = "judge_comparison_v4_15/trial_20261102T042920.013441Z_04b24a18"
TARGET_MODEL = "deepseek-flash"
JUDGE_MODEL = ["gpt-5.4-mini-2026-03-17", "gemini-3.8-flash", "deepseek-flash"]
SCENARIO_ID = "scenario_1"
REPEAT_INDEX = 1
RESPONSE_ID = "ced1e5122ec147799e1890b1b724698c"
DIMENSIONS = ["D6"]
ALLOW_REJUDGE = True
CURRENT_RUBRIC_FILE = "versions/v4_17/inputs/evaluation_prompt_type1.md"
CHECKLIST_FILE = "versions/v4_17/inputs/checklist_type1.md"
CALIBRATION_FILE = "gpt_judge_stability/frozen_inputs/calibration.md"
RECHECK_OUTPUT_FOLDER = "evaluations/batch_007/single_item_checks_v4_17"
EVALUATION_VERSION = "V4.17"

sys.dont_write_bytecode = True
AGENT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT_ROOT))
from runtime.paths import RESPONSES_ROOT, EVALUATIONS_ROOT


def current_prompt_check(args):
    from runtime import portable_json as json
    from runtime import configured_evaluation as evaluator
    from runner import dimensions

    if args.refresh_only:
        raise ValueError("Current-prompt checks are saved independently; inspect the saved selected_dimensions.json.")
    if not args.response_id:
        raise ValueError("Select one exact RESPONSE_ID for a current-prompt check.")
    judges = [args.judge] if isinstance(args.judge, str) else list(args.judge)
    chosen = dimensions(args.dimensions)
    arguments = dict(
        response_files=[RESPONSES_ROOT / args.batch / ("responses_" + args.target + ".jsonl")],
        response_ids=[args.response_id], evaluator_models=judges,
        rubric_file=AGENT_ROOT / CURRENT_RUBRIC_FILE, checklist_file=AGENT_ROOT / CHECKLIST_FILE,
        calibration_file=AGENT_ROOT / CALIBRATION_FILE, output_folder=EVALUATIONS_ROOT.parent / RECHECK_OUTPUT_FOLDER,
        repetitions=1, max_responses=None, evaluation_version=EVALUATION_VERSION)
    prepared, selected = evaluator.prepare(**{k: v for k, v in arguments.items() if k != "output_folder"})
    record = selected[0]["record"]
    if record["scenario_id"] != args.scenario or record["repeat_index"] != args.repeat:
        raise ValueError("The exact answer does not match the scenario or generation repetition.")
    original_file = EVALUATIONS_ROOT / args.batch / args.run / "judgments.json"
    originals = [r for r in json.loads(original_file.read_text(encoding="utf-8"))
                 if r["response_id"] == args.response_id and r["evaluator_model"] in judges]
    baselines = {r["evaluator_model"]: r for r in originals}
    if len(originals) != len(judges) or set(baselines) != set(judges) or any(r["source_sha256"] != selected[0]["source_sha256"] for r in originals):
        raise ValueError("Baseline judgments do not match the selected saved answer and judges.")
    if not args.allow_rejudge and any(r["status"] == "scored" and any(d in r["dimensions"] for d in chosen) for r in originals):
        raise ValueError("A selected score exists; enable ALLOW_REJUDGE for an independent check.")
    print(f"{', '.join(judges)} -> {args.target} | {args.scenario} | repeat {args.repeat}", flush=True)
    print("Response: " + args.response_id + "\nAccept: " + ", ".join(chosen), flush=True)
    print("One saved answer, one judgment per selected judge. Full six-dimension judgments are retained; only selected dimensions are used in this check.", flush=True)
    result = evaluator.run(**arguments, preview=args.preview)
    if args.preview:
        return 0
    trial = Path(result["trial"])
    full_file = trial / ("gpt_judgments.json" if len(judges) == 1 and judges[0].startswith("gpt-") else "judgments.json")
    rows = json.loads(full_file.read_text(encoding="utf-8"))
    if len(rows) != len(judges) or {r["evaluator_model"] for r in rows} != set(judges):
        raise ValueError("A single-answer check requires one judgment per selected judge.")
    views = []
    for row in rows:
        baseline = baselines[row["evaluator_model"]]
        views.append({"status": row["status"], "response_id": args.response_id, "evaluator_model": row["evaluator_model"],
            "selected_dimensions": chosen, "baseline_trial": str(original_file.parent),
            "baseline_dimensions": {d: baseline.get("dimensions", {}).get(d) for d in chosen},
            "dimensions": {d: row["dimensions"][d] for d in chosen} if row["status"] == "scored" else {},
            "checklist_findings": row.get("checklist_findings", {}), "reason": row.get("reason"),
            "source_sha256": row["source_sha256"], "rubric_sha256": row["rubric_sha256"],
            "full_judgment_file": str(full_file), "note": "Independent current-prompt check; original scores are unchanged."})
    view = views[0] if len(views) == 1 else {"status": result["summary"]["status"], "response_id": args.response_id,
        "selected_dimensions": chosen, "judges": judges, "judgments": views, "full_judgment_file": str(full_file)}
    output = trial / "selected_dimensions.json"
    evaluator.write_json(output, view)
    print("Selected result: " + str(output), flush=True)
    print("Status: " + result["summary"]["status"], flush=True)
    return 0 if all(row["status"] == "scored" for row in rows) else 1


def main(argv=None):
    from runner import prepare, execute, describe, refresh_comparison
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true", help="Check inputs; no API calls or writes")
    parser.add_argument("--refresh-only", action="store_true", help="Rebuild supplemented exports without API calls")
    parser.add_argument("--batch", default=BATCH)
    parser.add_argument("--run", default=COMPARISON_RUN)
    parser.add_argument("--target", default=TARGET_MODEL)
    parser.add_argument("--judge", default=JUDGE_MODEL)
    parser.add_argument("--scenario", default=SCENARIO_ID)
    parser.add_argument("--repeat", type=int, default=REPEAT_INDEX)
    parser.add_argument("--response-id", default=RESPONSE_ID)
    parser.add_argument("--dimensions", nargs="+", default=DIMENSIONS)
    parser.add_argument("--allow-rejudge", action="store_true", default=ALLOW_REJUDGE)
    args = parser.parse_args(argv)
    if CURRENT_RUBRIC_FILE is not None:
        return current_prompt_check(args)
    if not isinstance(args.judge, str):
        if len(args.judge) != 1:
            raise ValueError("Frozen original-run supplements require one judge; select --judge explicitly.")
        args.judge = args.judge[0]
    case = prepare(AGENT_ROOT, args)
    print(describe(case), flush=True)
    if args.preview:
        print("Preview complete. No API calls; no files written.")
        return 0
    if args.refresh_only:
        from datetime import datetime, timezone
        name = "refresh_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        print("Combined scores: " + str(refresh_comparison(case, name)))
        return 0
    result = execute(case)
    print("Supplement: " + str(result["folder"]), flush=True)
    print("Status: " + result["status"], flush=True)
    if result.get("summary"):
        print("Combined scores: " + str(result["summary"]), flush=True)
    if result.get("export_pending"):
        print("Score safely saved. Export failed; run --refresh-only to rebuild it without another API call.")
    return 0 if result["status"] == "scored" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, FileNotFoundError) as exc:
        print("Stopped: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
