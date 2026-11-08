# GPT judge repeatability on the original batch 007

Run Evaluation Agent/main.py. Its default task uses GPT-5.4 mini (gpt-5.4-mini-2026-03-17) on the original 50 batch_007 answers, with three independent judge repetitions: 150 planned initial judgments. It does not regenerate answers or call Gemini/DeepSeek. Their original 100 records are retained for comparison. Existing saved OpenAI credentials are reused only when the user starts a live run.

Use main.py --preview to verify inputs and see the remaining request count without reading credentials, making requests or writing trial files. Use main.py --mode type2_v13_pilot to select the separate Type2 V1.3 task. Its data and settings remain separate.

Exactly one incomplete/interrupted GPT trial resumes automatically. Every attempted answer/repetition pair is skipped, including a review-required record; valid scores are never collected again merely because another answer failed validation. Raw records remain unchanged. A completed trial requires an explicit --new-trial to start another. Locks block simultaneous execution.

The current first trial attempted 20 requests: 19 numeric judgments and one review-required judgment. Resume must show 130 remaining initial judgments. The unresolved record is kept for separate review, not assigned zero or given an invented D6 impact. A review-required record does not halt unrelated answers. A provider stop before all selected records were attempted still stops execution for inspection.

All rubric, checklist, source, reference, provider-configuration and shared scoring-engine hashes remain frozen. A driver-only continuation update is recorded explicitly in the existing trial manifest. Source record metadata and initial model inputs remain the original ones, including during partial-target continuation. There is no model or parameter fallback.

Reports are English. Raw provider JSON retains exact original text; the historical frozen rubric requested Chinese short comments. Altering that instruction would create a different grading condition and is not silently mixed into this repeatability test.

Status complete means all 150 numeric judgments exist. Status complete_with_review means all planned pairs were attempted but one or more records remain unscored. Stability uses only complete numeric triplets and always displays its denominator. Missing scores are never zero. Matched judge comparison uses the same available answers and averages GPT repetitions within each answer before the overall mean. Original provisional flags remain visible.

Outputs: report.md, stability_summary.json, matched_judge_means.json, three_judge_comparison.json and exact raw gpt_judgments.json. Scores measure declared judgments; repeatability and agreement do not establish semantic accuracy.
