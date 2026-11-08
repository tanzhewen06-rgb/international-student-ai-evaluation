# Evaluation V4.13

This revision addresses observed GPT judge false positives without changing the V4.12 scoring contract. It prioritizes whole-answer context, asserted facts versus possibilities, equivalent explanations, one issue per underlying defect and correct issue-kind/impact pairing. Generated explanations are English. There are no target means or prescribed scores.

The original batch_007 answers, frozen GPT trial, shared runtime, Type1 checklist, calibration principles, provider model/settings and deterministic score formula remain unchanged. Historical outputs are not rewritten. The revision is identified as V4.13 in its manifests and by its distinct rubric hash; the compatible numeric contract remains V4.12.

## Running

From the Evaluation Agent directory:

```powershell
..\.venv\Scripts\python.exe -B main.py --preview
..\.venv\Scripts\python.exe -B main.py
```

The default is GPT only, on 10 deliberately selected original answers, three judging repetitions each: 30 initial requests and at most one repair per request. This is not a fresh response-generation experiment. The five scenarios each contribute two answers; response models are not equally represented. The regression suite was selected because of observed errors or score changes, not as a representative sample.

Only the user launches actual API calls. Preview reads no credentials, makes no API calls and writes no outputs. Results go to a new `evaluations/gpt_judge_v4_13_batch007/regression/trial_*` directory. An interrupted trial resumes unattempted answer/repetition pairs. An unscored review record is retained, is never replaced with zero and does not block other answers. A fully attempted trial is not automatically rerun; `--new-trial` explicitly creates another trial.

After reviewing the regression results, the other 40 answers are available with `--suite complement` (120 initial requests). `--suite full` deliberately evaluates all 50 again (150 initial requests); do not run all suites without accounting for the repeated answers. Each suite is separately identified. The complement is a disjoint answer set, not independently collected blind data.

The old entry remains available as `--mode gpt_batch007_stability`. The existing Type2 V1.3 pilot entry is unchanged. `inputs/rubric_type2_v13.md` contains the same common review protocol for later consistent activation; it is not currently routed into a paid run. The protocol is provider-independent and must be shared across judges when a final revised judging condition is adopted.

## Verification and limits

Offline tests check all input hashes, unchanged scoring contracts/task templates, English instructions, cohort separation, integer scoring, exact-duplicate merging, valid classification repair, unresolved validation failures and interrupted-run continuation. Mock outputs exercise software behavior; they are not evidence that a model now understands the examples correctly.

The shared validator merges only exact duplicates. Broader semantic deduplication is an instruction to the judge, not an automatic synonym-based score edit. Existing supported issues, severity floors and conservative repair rules remain active. A D5-only unsupported factual issue remains invalid; the program never invents a D6 impact to satisfy validation.

Recheck the demonstrated false positives AND the genuine errors they previously obscured. Lower spread or a higher mean alone does not establish a better judge. Compare semantic findings and complete-triplet stability on the same saved answer IDs. Because English output and decision-check instructions both changed, a difference from the old trial cannot be attributed solely to one of them. Keep the old and revised conditions labeled separately in research reporting.

The test design follows the principle of retaining observed failure cases and evaluating revisions explicitly: [OpenAI evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices).
