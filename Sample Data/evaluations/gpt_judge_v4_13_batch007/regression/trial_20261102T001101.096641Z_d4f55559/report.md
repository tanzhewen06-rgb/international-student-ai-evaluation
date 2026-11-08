# Configured evaluation

Version: V4.13. Status: complete_with_review.

Judges: gpt-5.4-mini-2026-03-17. Answers: 6. Repetitions: 3.

Attempted 18/18; scored 8; unscored 10.

Review flags and missing scores remain visible. Missing scores are not zeros. Repeatability does not establish semantic accuracy.

## Context review

Same judge model, separate draft and context-review calls. The reviewer receives allegations without initial numeric anchors, checklist booleans, severity levels or dimension impacts. It can retain, reject, revise, merge or flag them as uncertain and must also search for real omitted defects.

Recorded provider requests: 46. Phase counts: {"draft": 18, "review": 18, "review_repair": 10}.
Review decisions: {"revise": 17, "reject": 27, "keep": 13, "merge": 3}.

Full initial inputs are in prepared_inputs. Every actual draft/review request, response and input hash is retained in review_traces. Draft and reviewed scores can be compared there; model decisions are not human accuracy labels.

Unresolved review uncertainty, unmatched evidence or unresolved schema/impact errors remain unscored after bounded review repair. No draft score or fabricated D6 penalty is substituted. This is a changed judging condition; keep it separate from earlier one-pass V4.13 records.
