from pathlib import Path
import time

import agent
import prompts
from storage import ExperimentStorage

HERE = Path(__file__).resolve().parent


# Response models.
MODEL_NAMES = ['deepseek-flash', 'gemini-3.5-flash-lite', 'gemini-3.8-flash', 'gpt-5.4-nano', 'gpt-6.1-sol']
BATCH_NAME = "Final_Batch_Type_1"
REPEAT_COUNT = 5
PERSONA_FILE = "international_student_counselor_prompt_en V2.md"
STUDENT_BACKGROUND_FILE = "international_student_background_prompt_en V1.md"
SCENARIO_FILE = "international_student_scenario_prompts V4.md"
PREVIEW_ONLY = False
_DEFAULT = object()
EXPERIMENTS_DIR = HERE.parent / "Sample Data" / "responses"
REQUIRE_EMPTY_MODEL_FILE = True


def _prompt_path(filename):
    path = Path(filename)
    return path if path.is_absolute() else prompts.PROMPTS_DIR / path


def main(model_name=None, batch_name=None, repeat_count=None, output_root=None, scenario_file=None,
         persona_file=None, student_background_file=_DEFAULT, preview=None):
    if model_name is None:
        if not MODEL_NAMES or len(set(MODEL_NAMES)) != len(MODEL_NAMES):
            raise ValueError("MODEL_NAMES must contain distinct full model IDs.")
        effective_preview = PREVIEW_ONLY if preview is None else preview
        if not effective_preview:
            models_to_check = MODEL_NAMES
            from models import check_credentials
            check_credentials(models_to_check)
            if REQUIRE_EMPTY_MODEL_FILE:
                folder = Path(EXPERIMENTS_DIR if output_root is None else output_root) / (BATCH_NAME if batch_name is None else batch_name)
                for selected_model in MODEL_NAMES:
                    existing = folder / f"responses_{selected_model}.jsonl"
                    if existing.exists() and existing.stat().st_size:
                        raise FileExistsError(f"This batch already has answers for {selected_model}; use a new batch or inspect the partial run before restarting.")
        outcomes = []
        for selected_model in MODEL_NAMES:
            outcome = main(
                model_name=selected_model, batch_name=batch_name,
                repeat_count=repeat_count, output_root=output_root,
                scenario_file=scenario_file, persona_file=persona_file,
                student_background_file=student_background_file, preview=preview,
            )
            outcomes.append(outcome)
            if outcome["failures"]:
                break
        return outcomes
    batch_name = BATCH_NAME if batch_name is None else batch_name
    repeat_count = REPEAT_COUNT if repeat_count is None else repeat_count
    output_root = EXPERIMENTS_DIR if output_root is None else output_root
    if type(repeat_count) is not int or repeat_count < 1:
        raise ValueError("repeat_count must be a positive integer.")

    scenario_path = _prompt_path(SCENARIO_FILE if scenario_file is None else scenario_file)
    persona_path = _prompt_path(PERSONA_FILE if persona_file is None else persona_file)
    background_file = STUDENT_BACKGROUND_FILE if student_background_file is _DEFAULT else student_background_file
    background_path = _prompt_path(background_file) if background_file is not None else None
    persona_prompt = prompts.load_persona_prompt(persona_path)
    student_background = prompts.load_student_background(background_path) if background_path is not None else None
    preview = PREVIEW_ONLY if preview is None else preview
    scenarios = prompts.load_scenarios(path=scenario_path)
    results = {}
    failures = 0
    records = ExperimentStorage(
        model_name, batch_name, persona_prompt, output_root, scenarios,
        scenario_file=scenario_path, persona_file=persona_path,
        student_background=student_background, student_background_file=background_path,
    )
    if preview:
        prepared = [agent.build_scenario_prompt(scenario, student_background) for scenario in scenarios.values()]
        print(f"Preview: {len(prepared) * repeat_count} requests | {model_name} | {batch_name}")
        print(f"Persona: {persona_path.name} | Background: {background_path.name if background_path else 'disabled'}")
        print(f"Scenario file: {scenario_path.name}")
        print("Preview complete. No API calls; no files written.")
        return {"preview": True, "selected": len(prepared) * repeat_count, "failures": 0,
                "response_file": records.response_file, "scenario_file": scenario_path.name,
                "persona_file": persona_path.name,
                "student_background_file": background_path.name if background_path else None,
                "user_prompts": prepared}
    if REQUIRE_EMPTY_MODEL_FILE and records.response_file.exists() and records.response_file.stat().st_size:
        raise FileExistsError("This model already has saved answers in the selected batch; no duplicate collection started.")
    with records:
        print(f"Persona: {persona_path.name} | Background: {background_path.name if background_path else 'disabled'}", flush=True)
        print(f"Scenario file: {scenario_path.name}", flush=True)
        total_requests = len(scenarios) * repeat_count
        print(f"Model: {records.model_name} | Batch: {batch_name} | Requests: {total_requests}", flush=True)

        for repeat_index in range(1, repeat_count + 1):
            for scenario_index, (scenario_name, scenario) in enumerate(scenarios.items(), 1):
                record = records.new_record(
                    scenario_index, scenario_name, scenario,
                    agent.build_scenario_prompt(scenario, student_background), repeat_index,
                )
                request_index = (repeat_index - 1) * len(scenarios) + scenario_index
                print(
                    f"[{request_index}/{total_requests}] Repeat {repeat_index}/{repeat_count} | "
                    f"Scenario {scenario_index}/{len(scenarios)} ...",
                    end=" ", flush=True,
                )
                response = None
                error = None
                start = time.perf_counter()
                try:
                    response = agent.run_agent(
                        model_name=records.model_name,
                        scenario=scenario,
                        system_prompt=persona_prompt,
                        student_background=student_background,
                    )
                except Exception as exc:
                    error = exc
                    failures += 1
                else:
                    results[record["response_id"]] = response
                records.save(record, response, error, time.perf_counter() - start)
                print("OK" if error is None else f"FAILED ({type(error).__name__})", flush=True)

    print(f"\nCompleted: {len(results)} successful requests, {failures} failed requests.")
    print(f"Records saved to: {records.response_file}")
    return {
        "run_id": records.run_id, "results": results,
        "failures": failures, "response_file": records.response_file,
        "scenario_file": scenario_path.name,
        "persona_file": persona_path.name,
        "student_background_file": background_path.name if background_path else None,
    }


if __name__ == "__main__":
    outcomes = main()
    if any(outcome["failures"] for outcome in outcomes):
        raise SystemExit(1)
