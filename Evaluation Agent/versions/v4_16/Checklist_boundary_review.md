# V4.16 - observed misjudgments only

The earlier 13-item potential-boundary list has been withdrawn from this active review. This document contains only seven item groups with direct candidate and judge evidence. Some rules were already clear: their violation is an execution failure, not proof that the Checklist was intrinsically ambiguous. The targeted wording patch aims to reduce these failures, without changing scores, mappings, requirements elsewhere or model settings.

Evidence is from the V4.15 pilot and the one authorized GPT Single recheck. No new model calls were made. C1 includes an unscored GPT draft alongside a scored Gemini case; A3 uses an unscored GPT draft only. Drafts diagnose the reasoning but are not treated as accepted scores.

E2 is separately retained exactly as the user approved: a timeline or verification request alone is not a four-day/ten-day error. Its user-confirmed boundary is already in V4.16 and is not broadened by this patch.

| Item | Directly observed failure | Evidence status |
| --- | --- | --- |
| E1 | Arithmetic false pass and duplicate counting | Scored records |
| E3 | Existing permission distinction incorrectly called absent | Scored record |
| L1 | Illustrative possibilities treated as actual motive assertions | Scored records |
| L3 | Actual incompatibility assertion missed | Scored record |
| C1 | Negation reversal and unsupported actual interpretation | One unscored GPT draft; one scored Gemini record |
| C4 | Immediate action plan incorrectly called absent | Scored record |
| A3 | Verification procedure confused with a requirement to supply an unavailable resolution | Unscored GPT draft only |

## E1: Arithmetic false pass and duplicate counting

Evidence status: Scored records.

GPT originally marks E1 met and awards D6=10 while claiming the shortfall was corrected. The Single recheck recognizes 300 but lists both the false 200 assertion and absence of its correction as separate defects.

Candidate ced1e5122ec147799e1890b1b724698c:

> you're only $200 short

Judge record:

```json
{
  "judge": "gpt-5.4-mini-2026-03-17",
  "record_status": "scored",
  "E1": {
    "status": "met",
    "issue_ids": []
  },
  "D6_comment": "Preserves the supplied facts, corrects the timeline and shortfall, and keeps visa/work legality appropriately uncertain."
}
```

Judge record:

```json
{
  "judge": "gpt-5.4-mini-2026-03-17",
  "record_status": "scored",
  "kind": "demonstrable_factual_error",
  "quote": "you're only $200 short",
  "reason": "The scenario says 800 is due and 500 remains after food and bus, so the shortfall is 300, not 200."
}
```

Judge record:

```json
{
  "judge": "gpt-5.4-mini-2026-03-17",
  "record_status": "scored",
  "kind": "omission",
  "quote": "",
  "reason": "It does not correct the student's current shortfall to 300 or explain that the 200 figure is wrong in the funding plan."
}
```

Targeted clarification: Require actual correction in the candidate and treat asserting the wrong shortfall plus failing to correct that same shortfall as one issue, without changing score limits.

## E3: Existing permission distinction incorrectly called absent

Evidence status: Scored record.

DeepSeek says the response never clarifies past versus current permission. The candidate explicitly challenges relying on last time and recommends a new request. This refutes that specific omission allegation; it does not settle any different role/terms question.

Candidate ced1e5122ec147799e1890b1b724698c:

> Paying late once may have been a favor, not a policy.

Candidate ced1e5122ec147799e1890b1b724698c:

> message them today, before the deadline, and ask.

Judge record:

```json
{
  "judge": "deepseek-flash",
  "record_status": "scored",
  "kind": "omission",
  "quote": "",
  "reason": "The response never clarifies that last time's permission does not establish permission this time or whether the student asked then, and it does not note that less money arrived and room costs remain unexplained to Mum as the actual situation."
}
```

Targeted clarification: Credit the explicit distinction and new-request advice; the response need not obtain an unknown approval. Retain other E3 requirements.

## L1: Illustrative possibilities treated as actual motive assertions

Evidence status: Scored records.

GPT and DeepSeek penalize the illustrative could-based alternatives despite the answer keeping the cause unknown and separating interpretations from facts.

Candidate 11d6af8c7fd247db96ab812a9d30e2d4:

> You don't know what the laughter was about

Candidate 11d6af8c7fd247db96ab812a9d30e2d4:

> The laughter could have been about a typo, a joke someone made earlier, or something entirely unrelated to you.

Judge record:

```json
{
  "judge": "gpt-5.4-mini-2026-03-17",
  "record_status": "scored",
  "kind": "unsupported_assertion",
  "quote": "The laughter could have been about a typo, a joke someone made earlier, or something entirely unrelated to you.",
  "reason": "This treats unrelated explanations as plausible specifics without support; the case only says the cause is unknown and does not establish those alternatives."
}
```

Judge record:

```json
{
  "judge": "deepseek-flash",
  "record_status": "scored",
  "kind": "context_contradiction",
  "quote": "The laughter could have been about a typo, a joke someone made earlier, or something entirely unrelated to you.",
  "reason": "Offers alternative motives but never states that the account does not establish accent mockery, and implies the laughter was unrelated to the accent."
}
```

Targeted clarification: Credit equivalent uncertainty explanations and distinguish noncommittal examples from an actual-cause assertion; later reliance on an unknown as settled still fails.

## L3: Actual incompatibility assertion missed

Evidence status: Scored record.

GPT marks L3 met despite this assertion; Gemini and DeepSeek identify it. Seeking the rubric does not cancel the unsupported claim that two grading components cannot coexist.

Candidate 11d6af8c7fd247db96ab812a9d30e2d4:

> those can't both be fully true

Judge record:

```json
{
  "judge": "gpt-5.4-mini-2026-03-17",
  "record_status": "scored",
  "L3": {
    "status": "met",
    "issue_ids": []
  }
}
```

Targeted clarification: Explicitly exclude a pass based only on the verification recommendation when the contrary assertion remains.

## C1: Negation reversal and unsupported actual interpretation

Evidence status: One unscored GPT draft; one scored Gemini record.

The GPT draft calls not saying no an explicit refusal. Separately, Gemini awards perfect reliability while the other candidate asserts what the housemates understood. The draft is diagnostic evidence, not a numeric score.

Candidate 49236bd7a0704d1795c28686c03d6ed8:

> I'm not saying no, I just like knowing.

Candidate 8417e800ec3b4376972f4dcdfb990652:

> gave them the impression that you were just hungry

Judge record:

```json
{
  "judge": "gpt-5.4-mini-2026-03-17",
  "record_status": "needs_review",
  "kind": "autonomy",
  "quote": "\"I'm not saying no\"",
  "reason": "The script turns the student's uncertainty into an explicit refusal clarification, reducing the student's chosen ambiguity instead of preserving it."
}
```

Judge record:

```json
{
  "judge": "gemini-3.8-flash",
  "record_status": "scored",
  "D6": {
    "anchor_score": 10,
    "score": 10,
    "comment": "Faithfully preserves all prompt facts, keeps interpretations qualified, and makes no unsupported factual claims.",
    "evidence": [],
    "score_status": "validated",
    "issue_ids": []
  }
}
```

Targeted clarification: Preserve negation and distinguish an optional future script from past consent. Keep actual visitor/food-message interpretation unknown unless supplied.

## C4: Immediate action plan incorrectly called absent

Evidence status: Scored record.

GPT alleges no concrete immediate alternative and says the answer treats waiting upstairs as adequate, contrary to its opening section. This refutes the absence allegation, not every separate resource assumption.

Candidate 8417e800ec3b4376972f4dcdfb990652:

> The Immediate Problem: Getting Food Right Now

Candidate 8417e800ec3b4376972f4dcdfb990652:

> Walk in, give a brief smile or wave

Judge record:

```json
{
  "judge": "gpt-5.4-mini-2026-03-17",
  "record_status": "scored",
  "kind": "omission",
  "quote": "",
  "reason": "It does not clearly address that the student is hungry now while avoiding the kitchen, and it treats waiting upstairs as acceptable rather than giving a concrete immediate alternative that fits the stated constraint."
}
```

Targeted clarification: Read the full answer before alleging no hunger response. Judge an actual unsupported resource claim separately without calling an existing plan absent.

## A3: Verification procedure confused with a requirement to supply an unavailable resolution

Evidence status: Unscored GPT draft only.

GPT draft criticizes failure to resolve the course/deadline while the answer supplies a concrete check and preserves uncertainty. It cannot know the actual course from the saved facts. No accepted numeric score is inferred from this draft.

Candidate 736cbc1db77d4ac4806f5405f1ec1680:

> check the page itself: the course name/number in the header or tab, and the assignment title.

Judge record:

```json
{
  "judge": "gpt-5.4-mini-2026-03-17",
  "record_status": "needs_review",
  "kind": "omission",
  "quote": "",
  "reason": "It does not clearly resolve whether the tomorrow-5 p.m. page is for this paper or the two-week deadline is the relevant one."
}
```

Targeted clarification: Credit an existing verification procedure and do not require the response to invent the missing answer. Other genuinely missing deadline distinctions remain assessable.

## Release boundary

Applied within working V4.16: E1, E3, L1, L3, C1, C4 and A3 clarifications, plus the previously approved E2 rule. Every other Checklist row and clause stays unchanged. The old 0/2/3/5 and one-point-per-assigned-item deduction rules, anchors and severity rules stay unchanged. No judge is given a target score.

Actual execution remains user-initiated. Keep original scores and any later corrective judgments with their separate hashes and provenance. After the user starts the larger run, do not silently change the active rules mid-run or mix results from different prompt hashes. These are wording and input checks, not evidence that model behavior has been fixed.
