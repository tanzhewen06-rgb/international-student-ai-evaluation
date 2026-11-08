# GPT judge repeatability on batch 007

Status: complete_with_review. Attempted 150/150; scored 145; unscored 5; remaining 0.

The same 50 saved answers are judged independently three times. The original rubric, checklist, reference, score formula, provider settings and initial request hashes remain fixed.
An unscored record is retained for review, is never converted to zero and does not stop other answers. Re-running this entry resumes an incomplete trial without repeating attempted requests.

## Matched comparison

The comparison uses the same 50 answers for all judges. GPT is averaged within each answer before the overall mean. Provisional values remain labeled in the data. A partial subset does not represent all response models.

| Judge | Understanding | Empathy | Culture and autonomy | Clarity | Practicality | Reliability |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| gpt-5.4-mini-2026-03-17 | 7.79 | 8.22 | 8.03 | 9.00 | 7.44 | 5.21 |
| deepseek-flash | 7.46 | 8.50 | 7.96 | 8.70 | 7.38 | 5.16 |
| gemini-3.8-flash | 9.16 | 9.50 | 9.54 | 9.76 | 9.10 | 7.88 |

## Repeatability

Complete three-judgment answers: 47/50. Complete dimension triplets: 282/300.

| Metric | Count |
| --- | ---: |
| All three equal | 132 / 282 |
| All three within one point | 224 / 282 |
| Spread at least two points | 58 / 282 |
| Maximum spread | 6 |

## Review and provenance

Inspect raw issue interpretations and provisional flags before treating scores as accurate. Repeatability and agreement with other judges are separate from semantic validity.
The frozen historical prompt requests Chinese short comments. Original provider records retain their exact text for auditability; this summary and its labels are English. A different output-language instruction would require a separately identified grading condition.
Driver-only continuation updates are recorded in trial_manifest.json. They do not alter the shared scoring engine, provider adapter, initial prompts or existing judgments.
Detailed available scores are in three_judge_comparison.json. Three-repeat metrics are in stability_summary.json. Incomplete or review-required data are not presented as a complete numeric dataset.
