# V4.15 dimension-ordered evaluation

Evaluation Prompt order: D2 empathy, D3 culture/autonomy, D4 clarity, D5 practicality, D6 factual reliability, D1 problem understanding. D2-D5 are completed without any Checklist input. Only D6 and D1 consult dimension-specific Checklist guidance within their own assessment.

Status: complete. Numeric judgments: 30/30. Recorded provider requests: 94.

D1 and D6 use min(rubric anchor, corresponding Checklist score). D2-D5 retain their independent rubric anchors and are not revised after later Checklist assessments. Scores are integers; an omission is not automatically a fabricated fact.

Each stage permits four attempts total. Successful stages are cached. Exhausted stages remain explicit failures; no zero or high score is invented. Auxiliary explanation/quotation problems are flagged rather than invalidating otherwise complete numeric structure.

Workflow revision: dimension_ordered. This replaces the earlier Checklist-first V4.15 flow; cache identities prevent its reuse. Keep different workflow conditions separate. These are pilot design rules, not calibrated ground-truth probabilities.

| Judge | Numeric records | D1 | D2 | D3 | D4 | D5 | D6 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| gpt-5.4-mini-2026-03-17 | 10 | 7.90 | 8.10 | 8.30 | 8.90 | 8.30 | 5.40 |
| gemini-3.8-flash | 10 | 8.00 | 10.00 | 10.00 | 10.00 | 10.00 | 7.40 |
| deepseek-flash | 10 | 7.30 | 8.60 | 8.20 | 9.00 | 8.70 | 5.60 |
