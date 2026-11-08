from pathlib import Path
from collections import Counter
from runtime.configured_evaluation import run
from runtime.storage import read_sources

from runtime.paths import RESPONSES_ROOT, EVALUATIONS_ROOT

HERE = Path(__file__).resolve().parent
INPUT_FOLDER = RESPONSES_ROOT / 'Final_Batch_Type_1'
RESPONSE_FILES = [
    INPUT_FOLDER / 'responses_deepseek-flash.jsonl',
    INPUT_FOLDER / 'responses_gemini-3.5-flash-lite.jsonl',
    INPUT_FOLDER / 'responses_gemini-3.8-flash.jsonl',
    INPUT_FOLDER / 'responses_gpt-5.4-nano.jsonl',
    INPUT_FOLDER / 'responses_gpt-6.1-sol.jsonl',
]
RESPONSE_IDS = None

# Judge models.
EVALUATOR_MODELS = ['gpt-6.1-sol', 'gemini-3.8-flash', 'deepseek-flash']

RUBRIC_FILE = HERE / 'versions' / 'v4_17' / 'inputs' / 'evaluation_prompt_type1.md'
CHECKLIST_FILE = HERE / 'versions' / 'v4_17' / 'inputs' / 'checklist_type1.md'
CALIBRATION_FILE = HERE / 'gpt_judge_stability' / 'frozen_inputs' / 'calibration.md'
OUTPUT_FOLDER = EVALUATIONS_ROOT / 'Final_Batch_Type_1' / 'judge_comparison_v4_17'
MISSING_SCORE_TRIAL = OUTPUT_FOLDER / 'trial_20261102T211905.670197Z_251b2721'
DEEPSEEK_RETRY_TIMEOUT_SECONDS = 900
EVALUATION_VERSION = 'V4.17'
EVALUATION_REPEATS = 1
SCENARIO_COUNT = 5
GENERATION_REPEATS = 5
MAX_RESPONSES = None
PREVIEW_ONLY = False

def main(preview=None, new_trial=False):
    if MISSING_SCORE_TRIAL is not None:
        from runtime.missing_scores import run_missing
        return run_missing(MISSING_SCORE_TRIAL, preview=PREVIEW_ONLY if preview is None else preview,
                           new_trial=new_trial, deepseek_timeout_seconds=DEEPSEEK_RETRY_TIMEOUT_SECONDS)
    if RESPONSE_IDS is None:
        for path in RESPONSE_FILES:
            if not path.is_file():
                raise FileNotFoundError("Generate the new Response Agent batch before evaluation: " + str(path))
            sources, errors = read_sources(INPUT_FOLDER, source_files=[path])
            actual = Counter((s['record']['model_name'], s['record']['scenario_id'], s['record']['repeat_index']) for s in sources)
            model = path.stem.removeprefix('responses_')
            expected = Counter((model, f'scenario_{sid}', rep) for sid in range(1, SCENARIO_COUNT + 1) for rep in range(1, GENERATION_REPEATS + 1))
            if errors or actual != expected:
                raise ValueError("Require five successful generations for each of the five scenarios before evaluation: " + str(path))
    return run(
        response_files=RESPONSE_FILES, response_ids=RESPONSE_IDS, evaluator_models=EVALUATOR_MODELS,
        rubric_file=RUBRIC_FILE, checklist_file=CHECKLIST_FILE, calibration_file=CALIBRATION_FILE,
        output_folder=OUTPUT_FOLDER, repetitions=EVALUATION_REPEATS, max_responses=MAX_RESPONSES,
        evaluation_version=EVALUATION_VERSION, preview=PREVIEW_ONLY if preview is None else preview,
        new_trial=new_trial,
    )

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Evaluate the models and saved answers configured above.')
    parser.add_argument('--preview', action='store_true', default=PREVIEW_ONLY)
    parser.add_argument('--new-trial', action='store_true')
    args = parser.parse_args()
    result = main(preview=args.preview, new_trial=args.new_trial)
    if not args.preview and result['summary']['status'] not in ('complete', 'complete_with_review'):
        raise SystemExit(1)
