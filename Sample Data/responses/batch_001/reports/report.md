# Batch 001: Data Status

This batch contains existing saved responses converted to compact JSONL v2.
Conversion made no model requests and produced no evaluation scores.

| Response model | Saved answers | JSONL objects | Bytes before | Bytes after |
| --- | ---: | ---: | ---: | ---: |
| gemini-3.8-flash | 25 | 26 | 555,117 | 134,700 |
| gpt-6.1-sol | 25 | 26 | 533,169 | 113,425 |

Each file has one metadata header and 25 response rows. All five scenario
snapshots and the persona are stored in the header; responses reference their
saved scenario. Complete logical records match the originals exactly, including
response text, prompts, IDs, timestamps, durations, settings and error fields.

The duplicate legacy-format archive was removed after all 50 complete logical
response records were verified identical to the active compact records. The active
batch keeps the original filenames, so Evaluation Agent/main.py continues to select
the same saved answers.

Evaluation results belong in Evaluation Agent/evaluations, in a separate folder
for each evaluator, target and independent execution. The empty evaluations.jsonl
in this batch is a legacy placeholder and does not record scoring progress.
