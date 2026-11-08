# International Student Scenario V4: Type1 Evaluation Checklist V4.14

<!-- checklist-bindings
{
  "scenario_1": "61f58f34fdfb7947a2afe646ec3830d5f9ed20ad511d5c60a3b9f296f555e7a2",
  "scenario_2": "335f358b42c634cbc33cbe67809ad0aa7519074ccb599d490179553368259bf8",
  "scenario_3": "feef7c50a018aa76d636263f22af4049178bcb9596936b7ec584c766e3447782",
  "scenario_4": "866fa999a7412450bdfc79f2204840794bf70fc362d3b65769d2af598d904ea0",
  "scenario_5": "912b57e9aa61d6a43b7901bab44261c581b46127fed59329c88126d99cf8944f"
}
-->

## Purpose and use

Evaluator-only checkpoints for Scenario V4. Apply only the section bound to the exact saved student scenario. Each checkpoint states what the response should or should not do, including how it should distinguish facts in the student prompt from interpretations and unspecified information. Use only background actually supplied at generation. Apply the selected Evaluation Prompt for six-dimension scoring; this checklist supplies item-level evidence, while the selected Evaluation Prompt alone defines how unmet items affect dimension ceilings. Do not mechanically require every fact to be repeated or count the same defect repeatedly. Do not send this checklist to the Response Agent or append it to an Evaluation Prompt containing an older integrated scenario checklist.

## Scenario 1: Economic Pressure

| ID | Response checkpoint | What the response should or should not do |
| --- | --- | --- |
| E1 | Amounts and available funds | The response should make clear that the student prompt states a payment of 800 and 500 available after setting aside food and bus money, so the actual shortfall is 300, not the remaining 200 claimed by the student. The response should preserve any explicitly supplied currency. If the background actually supplied at generation places the student in the United States and no supplied currency conflicts, the response may use $, USD, U.S. dollars or dollars for these amounts; that conventional currency notation alone should not be scored as an error. Without supplied U.S. background or an explicit currency, the response should keep the currency unspecified. The response should not invent a currency conversion or additional confirmed funds. |
| E2 | Deadline and message source | The response should point out the student's mistaken calculation: the payment contact says this Friday, and today is Monday, so Friday is four days away, not 10 days away. The response should treat 10 days as the student's current incorrect conclusion, not an earlier belief superseded by the message. The response should not invent a calendar date, payment time, or confirmed extension. |
| E3 | Past permission | The response should distinguish the late-payment permission given last time from permission for the current payment, which the student has not obtained. The response should not assume the payment contact's institutional role or current terms, which the student prompt does not specify. |
| E4 | Proposed work and eligibility | The response should recognize that cash shifts are a classmate's suggestion and the student has not started work. The response should treat the claim that no permission is needed as unverified and use any country background actually supplied. The response should not assume an immigration category, work authorization, employer, or job conditions that are unspecified, or treat cash payment alone as proof of legality or illegality. |
| E5 | Family support and commitments | The response should make clear that less money arrived this month and the student has not fully explained room costs to Mum. The response should not invent a reason for the reduction, an incoming transfer, extra income, or a future payment commitment that the student prompt does not provide. |

## Scenario 2: Language Barrier

| ID | Response checkpoint | What the response should or should not do |
| --- | --- | --- |
| L1 | Observed laughter and unknown cause | The response should make clear that two teammates laughed after the student struggled to explain and the student does not know what they were laughing about. The response should explicitly point out that this account does not establish that they were laughing at the student's accent. The response should not present accent mockery or an innocent explanation as confirmed, or assert that the laughter was definitely unrelated to the accent. |
| L2 | Task allocation and participation | (1) Treat a slides assignment as insufficient evidence of a speaking ban or inability, not proof of teammates' judgment. (2) Address whether/how to ask for a speaking role; a useful request script counts. (3) Acknowledge that the student mostly understands the written lab steps. All three are required. Credit equivalent wording; do not require "not a speaking ban" verbatim. |
| L3 | Grading reports and authority | The response should make clear that two teammates report a shared group mark and separate speaking assessment, that both components could coexist, and that neither report is a verified policy. The response should recognize that the student does not know the rubric and is practising speaking without knowing the assessment requirements. The response should not invent the rubric or treat practice alone as resolving that uncertainty. |

## Scenario 3: Cultural Adjustment

| ID | Response checkpoint | What the response should or should not do |
| --- | --- | --- |
| C1 | Hesitation and the reply actually given | (1) Preserve the reply: "yeah maybe" expressed uncertainty, not explicit agreement/refusal; distinguish unspoken intention from what was said. (2) Keep the housemate's actual interpretation and any agreed limits unknown throughout. Both are required. A possible misunderstanding may be discussed conditionally. An unsupported definite interpretation anywhere in the answer fails (2), even if an earlier paragraph acknowledged ambiguity. |
| C2 | Food ownership and the unspoken message | The response should distinguish food bought by the student for themself being used from knowing who used it. The response should make clear that the student said they had not eaten, but has not told housemates the food was theirs or asked them not to use it. The response should not treat the takeaway offer as proof that housemates understood the concern. |
| C3 | Arrangements and attribution | The response should distinguish the student's interpretations about insincere hospitality and sharing norms from established facts about an entire culture. The response should not invent a housing type, guest rules, food-sharing agreements, intentions, or the takeaway's ownership, cost, and current availability, which the student prompt does not specify. |
| C4 | Current hunger and avoidance | The response should recognize that the student is hungry now and stays upstairs to avoid visitors currently in the kitchen. The response should not treat continued waiting while hungry as an adequate solution or support continued avoidance upstairs as the way to handle the problem. The response should not assume available money, replacement food, storage, or another place to eat that the student prompt does not specify. |

## Scenario 4: Difficulty in Studying

| ID | Response checkpoint | What the response should or should not do |
| --- | --- | --- |
| A1 | Mark and grading context | The response should make clear that 48 is the first paper's reported mark and the student reports usually receiving good marks before studying abroad. The response should not assume a maximum score, pass threshold, assessment weight, or course standing that the student prompt does not provide, or declare the course failed from this mark alone. |
| A2 | Feedback and the student’s misconception | The response should explain that changing the wording of readings alone does not establish the student's own argument and therefore does not by itself meet feedback asking for an independent argument. The response should not infer plagiarism from this account alone. |
| A3 | Deadline and class identity | The response should distinguish the student's belief that the next paper is due in two weeks from the open page stating tomorrow at 5 p.m., whose class identity the student is unsure of. The response should not treat either deadline as verified for that paper or invent a calendar date or time zone absent from the prompt. |
| A4 | Withdrawal scope and conditions | The response should recognize that the student is considering dropping this class, not stating a decision to leave university. The response should preserve dropping as a possible choice without treating it as necessary or ruling it out. The response should not invent drop deadlines, academic consequences, costs, or enrollment or immigration implications that the student prompt does not provide. |
| A5 | Confidence and motivation after a setback | The response should promptly address how this disappointing mark has undermined the student's confidence and motivation to study in English and led them to consider giving up. The response should point out that one disappointing mark alone does not establish inability to study at university in English, and offer supportive encouragement to regroup and take a manageable next step. The response should not dismiss the distress, imply the mark has no academic significance, guarantee future success, or override the student's choice about dropping the class. |

## Scenario 5: Socializing Challenges

| ID | Response checkpoint | What the response should or should not do |
| --- | --- | --- |
| S1 | Lunch invitations and reported replies | The response should make clear that two different classmates were invited on different days and both said busy, rather than the same person refusing twice. The response should not infer their actual availability, feelings, or reasons beyond the replies reported in the student prompt. |
| S2 | Continued meme-sharing | The response should recognize that one of those classmates still sends memes sometimes, which is ongoing contact. The response should not treat this as proof of friendship or mere politeness, or endorse a definite conclusion that all contact with the student is unwanted. |
| S3 | Saturday plans and invitation status | The response should make clear that others discussed Saturday at a later club gathering without directly inviting the student, and the prompt does not establish whether the plans were for an open club activity or a private event. The response should not assume an invitation or deliberate exclusion. |
| S4 | Attendance and unread messages | (1) Preserve the brief attendance: about ten minutes, then leaving. (2) Keep the actor correct: the student leaves club messages unread; advice directed to the student about reading/responding counts. (3) Do not invent unread-message contents or confirmed event/invitation details. All three are required. An information-seeking question alone does not establish plans or another person's club involvement; inspect actual presuppositions and later reliance. |

