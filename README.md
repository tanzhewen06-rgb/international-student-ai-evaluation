> Publication copy: see PUBLICATION_NOTES.md for path portability and provenance.

# AI Persona Analysis

English | [简体中文](README.zh-CN.md)

Programs, versioned prompts, and experiment data are stored separately:

```text
AI Persona Analysis/
├── Response Agent/             # Answer generation code and prompts
├── Evaluation Agent/           # Evaluation code, versioned prompts and references
└── Sample Data/
    ├── responses/              # Saved answers, grouped by original batch
    ├── evaluations/            # Judge outputs, trials, supplements and reports
    ├── analysis/               # Saved offline analyses
    ├── reference_data/         # Frozen baseline metadata and scores
```

`Sample Data` contains actual saved model outputs, including historical pilot
batches. Its name does not mean that its contents are fabricated examples.
Batch names, response IDs, scores, prompt snapshots, and original manifests are
preserved. Markdown prompts and input references needed by the programs stay
with their respective agents.

## Setup

Use Python 3.13 and install `Response Agent/requirements.txt` in your own virtual
environment. Both agents share that model client layer.

Supply `OPENAI_API_KEY`, `GEMINI_API_KEY`, and `DEEPSEEK_API_KEY` through the
environment. On Windows, the existing `Response Agent/setup_keys.py` can store
OpenAI and Gemini keys in Windows Credential Manager; DeepSeek can use its
environment variable. Never place credentials in source files.

Run each agent from its own directory, or select its `main.py` in your editor.
Settings remain at the top of each `main.py`. Paths are derived from the project
location, so the two agent folders and `Sample Data` should remain siblings.

## Offline preview

From `Response Agent`, run:

```console
python -B -c "import main; main.main(preview=True)"
```

From `Evaluation Agent`, run:

```console
python -B main.py --preview
```

These previews do not call a model or write experiment results.

## Existing results and new experiments

The current configuration selects `Final_Batch_Type_1`: five response models,
five scenarios, and five generations per scenario (125 answers). The completed
combined evaluation contains 375 judge records, including five provisional
records. The effective dataset is
`Sample Data/evaluations/Final_Batch_Type_1/judge_comparison_v4_17/trial_20261102T211905.670197Z_251b2721/supplements/missing_scores/judgments_supplemented.json`.
The original trial contains three unsuccessful judgments; use the supplemented
dataset for the completed result, rather than concatenating all logs.

The default evaluation entry point still selects that trial's missing-score
recovery. Since it is complete, it reports zero missing judgments without making
requests or rewriting exports.

To run a new experiment, select a new batch in both agents, update their input
and output selections, and set `MISSING_SCORE_TRIAL = None` in Evaluation Agent.
Generation refuses to append to an existing nonempty model answer file.
Starting a model/API run is a separate user action.

Historical manifests retain historical code hashes. Local paths now use project-relative references.
The path adapter resolves moved files for reading without rewriting provenance.
Frozen trial continuation still requires matching original input and code
fingerprints; the reorganized code is not an identical replay environment.
Historical GPT-stability and frozen single-item preflight checks may therefore
stop on a code-fingerprint difference. Local archives are excluded from this publication copy.

## Sharing

The root ignore file excludes credentials, virtual environments, caches,
archived local backups, and local editor settings. Active programs, prompts,
and `Sample Data` experiment results remain eligible for version control.
No repository has been created or uploaded by this reorganization, and no
publication license is implied.
