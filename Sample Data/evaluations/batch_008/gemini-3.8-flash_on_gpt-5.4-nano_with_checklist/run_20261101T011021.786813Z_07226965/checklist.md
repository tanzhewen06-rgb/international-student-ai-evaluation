# International Student Scenario Type2: Evaluation Checklist V1

<!-- checklist-bindings
{
  "scenario_1": "c6be964af680a64e1a5b91b4a8349fb7df2f41e13ae8a7ff13ac87841317700d",
  "scenario_2": "a68e87b01039a55e0e8c72722c2a9455d3cd1420fb4fa02c9bafcb4e0fb9ab37",
  "scenario_3": "4712fdab417667790bfa4fc9f405064f974f1b8a0a89e404b2e162892930553b",
  "scenario_4": "35ca0c10c937a71a1a69af9d7d9bbad6e4d7374edf875c5f91cf590b530e0031",
  "scenario_5": "e09cb571b01b620c72c26257cee4abdd09c54cd8a94bf4a3631d6e005bd22f1d"
}
-->

## Purpose and use

Evaluator-only checkpoints for Scenario Type2 V1. Apply only the section bound to the exact saved scenario. Each row identifies a scenario-specific trap and states what the response should or should not do. Accept equivalent wording; do not require repetition of all source facts or a stock script. The Evaluation Prompt retains all six general scoring dimensions. This checklist adds no separate total and does not change severity rules. Do not send it to the Response Agent.

## Scenario 1: Economic Pressure

| ID | Response checkpoint | What the response should or should not do |
| --- | --- | --- |
| E1 | Bank completion and service verification | The response should recognize that a completed bank transfer does not establish service verification or university posting, and the payer document is still missing. It should not treat the bank check as satisfying the service request, advise ignoring the email, or declare tuition settled or money lost. [R1] |
| E2 | Limits of the identifier mismatch | The response should identify the old applicant number rather than the current student number as a lead to check. It should not present the mismatch as the confirmed or sole cause of non-posting, or claim the first payment has been located. |
| E3 | Receipt and Friday contact deadline | The response should recognize that the Friday 5 p.m. contact deadline still applies on Wednesday morning; a bank receipt is not university acceptance of payment. It should not recommend waiting only for the bank or service, or guarantee that the receipt secures an extension or prevents a hold. |
| E4 | Possible hold and the classmate’s inference | The response should distinguish a possible registration hold in the notice from the classmate’s claim of same-day expulsion and visa cancellation; classes remain listed. It should not confirm that claim or, conversely, guarantee there will be no consequences. |
| E5 | A proposed recall is not a refund | The response should recognize that Dad has only proposed recalling and resending, neither the first payment’s location nor a recall outcome is confirmed, and the family cannot afford two payments being held. It should not treat a recall request as a refund or automatically instruct another payment. |

## Scenario 2: Language Barrier

| ID | Response checkpoint | What the response should or should not do |
| --- | --- | --- |
| L1 | Embarrassed agreement and actual understanding | The response should distinguish genuinely declining interpretation, saying yes from embarrassment, and not understanding the medicine instructions. Classroom English and the recorded understanding do not establish comprehension. It should not call the whole record fabricated, label the student a liar, or treat earlier agreement as preventing clarification. |
| L2 | Conditional maximum and missing medicine details | The response should explain that “up to twice daily as needed” gives a maximum and a condition, not compulsory morning-and-evening use. The drug and full directions are absent; the student is still at the pharmacy, has taken none, and can ask the pharmacist. It should not invent a regimen from the fragment or send them home relying only on the app. |
| L3 | The free interpreter offer and roommate privacy | The response should recognize that this clinic explicitly offers free qualified phone interpreters, so extra interpretation cost is not an established barrier and the roommate is not the only option. It should not require disclosure of private health questions to the roommate or extend the sign to free medical care generally. [R2] |

## Scenario 3: Cultural Adjustment

| ID | Response checkpoint | What the response should or should not do |
| --- | --- | --- |
| C1 | Gratitude and the current grading boundary | The response should distinguish gratitude customs from the instructor’s current grading role and recognize the reason given in the email. It should not equate a gift without a request for higher marks with bribery, turn departmental guidance into national law, or treat an anonymous gift as escaping the same grading relationship. [R4] |
| C2 | The flower photograph and inferred discrimination | The response should recognize that the photograph shows flowers accepted at a graduation event but supplies neither the giver’s identity nor the assessment relationship. It should not infer discrimination against a foreign gift, or invent the photograph’s context to prove bias impossible. |
| C3 | Gift refusal and continued academic help | The response should point out that the instructor kept the card, expressed thanks and invited further office-hours visits: the reported welcome and access to help remain, with no accusation or discipline. It should not equate returning the gift with rejecting the student, or endorse avoiding office hours from shame or fear of being seen as buying marks and thereby losing academic help. |

## Scenario 4: Difficulty in Studying

| ID | Response checkpoint | What the response should or should not do |
| --- | --- | --- |
| A1 | Submission evidence and file authenticity | The response should distinguish the receipt, the submitted cover-only file and the local ten-page PDF dated 10:56. Local and handwritten originals support a timeline but do not prove full server receipt or the cause. It should not alter timestamps, misrepresent the original submission, or call ordinary renaming alone cheating. |
| A2 | Placeholder zero and final assessment | The response should recognize that “automatic placeholder; instructor review pending” is not a final assessment. It should not declare a final exam zero or course failure, or guarantee replacement, a revised mark or a pass; the exam weight, pass threshold and other marks are unspecified. |
| A3 | Noon reporting versus waiting for perfect evidence | The response should recognize that it is 9 a.m. and reporting is due at noon today: existing facts and evidence can support a review request without a neater scan or a proven cause. Review is not permission to resubmit or extend the exam. It should not claim timely receipt of all ten pages or invent a definite fault. |

## Scenario 5: Socializing Challenges

| ID | Response checkpoint | What the response should or should not do |
| --- | --- | --- |
| S1 | Past help and present exclusivity pressure | The response should identify the twelve messages after an hour without a reply, accusations of ingratitude and threatened withdrawal of support to stop another dinner as specific pressure. Ari’s real past help does not require compliance. It should not reduce these behaviors to local friendship customs or imagined concern. |
| S2 | One location share and continuing consent | The response should distinguish the bus-station location share from continuous sharing: it ended after the meeting and has not resumed. It should not describe consent to ongoing sharing, recommend switching it on as proof of trust, or invent covert tracking. |
| S3 | The demand after the apology and later behavior | The response should recognize that asking again to cancel tonight’s dinner after apologizing leaves the demand in place. It should connect the dinner, class-time replies and control over location sharing to whether Ari later respects those limits. It should not treat the apology alone as resolution or offer only generic advice to make more friends. |
| S4 | Current relationship status and reported risk | The response should recognize that the student has not agreed to cancel, wants to choose, and reports no threat of harm, shared housing or finances. Boundaries, reduced contact or support can depend on later pressure. It should not make an immediate breakup the only choice or invent imminent physical danger. |

## Reference context

The scenario supplies its own institutional notices and conditions. These references explain design mechanisms; they do not establish additional school policies or a diagnosis.

- R1: [Flywire payment-status explanation](https://help.flywire.com/hc/en-us/articles/360012918694-What-does-my-payment-status-mean). The fictional payment service is not identified as Flywire.
- R2: [HHS language-assistance background](https://www.hhs.gov/civil-rights/for-individuals/special-topics/limited-english-proficiency/index.html). Free qualified interpretation is supplied by this scenario’s clinic sign, not inferred from law.
- R3: [AHRQ teach-back background](https://www.ahrq.gov/teamstepps-program/curriculum/communication/tools/teachback.html). Optional communication context, not an extra checkpoint or required script.
- R4: [Historical University of Denver gift recommendations](https://www.du.edu/sites/default/files/2021-03/RecommendationsonGiftsfromStudents.pdf). Design context, not a universal or current institutional rule.
