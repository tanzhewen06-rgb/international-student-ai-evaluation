# Response Agent: Change Log

## 2026-10-26 — batch_005: two models, three repeats

- One main() execution runs gpt-6.1-sol and gemini-3.8-flash for five scenarios x three repeats each, 30 answers total. Subsequent runs append under new generation run IDs.
- Preserve Counselor V2, Background V1, Scenario V4 and existing client parameters; verify official model IDs without generation calls.
- Evaluation main() reads both complete batch_005 files using V4.3 and reports repeats.

This document records prompt changes and their implementation status. It complements the program README rather than replacing it. [Chinese edition](CHANGELOG.zh-CN.md).

Version numbers belong to individual files. Counselor V2, Scenario V2, and Background V1 are separate components, not a single synchronized release.

## Current inventory and selection

| Component | Available files | Current status |
| --- | --- | --- |
| Counselor persona | [V1](prompts/international_student_counselor_prompt_en%20V1.md), [V2](prompts/international_student_counselor_prompt_en%20V2.md) | `main.py` now selects V2. The legacy loader fallback remains V1. |
| Student scenarios | [V1](prompts/international_student_scenario_prompts%20V1.md), [V2](prompts/international_student_scenario_prompts%20V2.md), [V3](prompts/international_student_scenario_prompts%20V3.md), [V4](prompts/international_student_scenario_prompts%20V4.md) | `main.py` selects reviewed V4 for batch_004; V1-V3 remain available. |
| Student background | [V1](prompts/international_student_background_prompt_en%20V1.md) | Enabled in `main.py`; sent and saved for every selected scenario. |

Scenario V3 and reviewed Scenario V4 are available. No Counselor V3 or Background V2 has been created.

## Counselor V1 to V2

V1 establishes a warm, respectful international-student adviser, with emotional support, practical assistance, factual caution, autonomy, and tool-use boundaries. It already discourages questionnaires and vague referrals. However, its listening-versus-advice question can allow an answer to stop after reassurance and an offer of future help.

V2 starts from the complete V1 text. Changes are concentrated in the following sections:

| Section | V1 behavior or emphasis | V2 change |
| --- | --- | --- |
| 2. Understanding the user | Use available conversational background and ask essential questions. | Explicitly use a supplied student background; do not repeat known country or institution questions. A school name is not a prerequisite for general help. Unknown visa categories and policies remain unknown. |
| 3.2. Academics and Research | Offer academic assistance and follow integrity requirements. | Ask for the smallest relevant excerpt when the answer depends on a syllabus, grading breakdown, assignment criteria, deadline notice, or feedback. Explain what can be analyzed; do not routinely demand a whole document. |
| 4. Identifying the current need | Distinguish listening, explanation, decisions, and practical help; ask a preference question when unclear. | Recognize an implicit request in a concrete difficulty even without a direct question. Give brief emotional acknowledgment, a grounded preliminary explanation, and a manageable immediate step when feasible. Do not require grammar correction. |
| 4. Clarifying preferences | Offer to listen or work out a next step. | Reserve that preference question for genuine ambiguity, rather than making it the default gate to all practical assistance. Respect an explicit listening-only request. |
| 4. Usable deliverables | Avoid stopping at generic referrals; provide useful materials. | Do the useful part now when possible instead of only offering future help. Match the output to the bottleneck; emails are one option alongside explanations, calculations, rehearsal techniques, and targeted document review. |
| 8. Quality self-check | Check relevance, reliability, practical usefulness, and autonomy. | Explicitly check implicit needs and whether immediate help was supplied rather than only reassurance, background questions, or an offer to help later. |

V2 retains uncertainty, student choice, proportionate emotional support, academic integrity, and existing professional and tool-use boundaries. It does not require an action plan in every conversation, invent a hidden request, assume internet access, or turn every concern into an email.

## Student Background V1: new component

The shared profile specifies an international undergraduate in the United States, in the first semester of the first year, newly arrived a few weeks ago, studying abroad for the first time, with English as an additional language.

The university, city, state, nationality, age, gender, major, visa category, work authorization, grading rules, institutional policies, and financial resources are not filled in. Each scenario supplies its own additional facts. Separate scenarios are independent cases, not automatically a continuous conversation or one accumulated personal history.

This profile is distinct from the assistant persona and from the evaluator's checklist. Creating a file alone does not inject it into requests. The current main entry point now explicitly loads and sends this profile; persistent memory and browsing are not added.

## Scenario V1 to V2

The five topics remain economic pressure, language barriers, cultural adjustment, studying, and socializing. The content changes substantially, not merely in wording:

| Topic | V1 | V2 |
| --- | --- | --- |
| Economic pressure | Consistent amounts and a ten-day deadline; previous spending cuts and job applications. | An incorrect shortfall, competing deadline information, an assumed repeat extension, and an unverified cash-work claim. |
| Language barrier | Difficulty entering fast discussion despite preparation and language practice. | Ambiguous laughter, inferred exclusion through task allocation, uncertain presentation grading, and withdrawal from speaking. |
| Cultural adjustment | Indirect concerns about overnight guests and disrupted sleep. | Ambiguous permission, food ownership and sharing, cultural generalization, and hiding while hungry. |
| Studying | Difficulty moving from source summary to argument despite rereading instructions. | A mark without grading context, paraphrasing mistaken for argument, conflicting deadlines, and pressure to affirm leaving. |
| Socializing | Loneliness despite invitations, events, and joining a club. | Two busy classmates interpreted as rejection, discounted meme-sharing, uncertain event access, unread messages, and pressure to endorse withdrawal. |

V1 explicitly asks what the student could do. V2 relies more on narrated distress and implied help-seeking, with imperfect English and unsupported student interpretations. Grammar and spelling test faithful understanding; they are not proofreading tasks.

## File naming and historical compatibility

The legacy Counselor filename ending in `Version 1.md` is renamed to `international_student_counselor_prompt_en V1.md`. Its contents are preserved byte for byte. The loader points to the renamed V1, and its fallback version labels use `V1`.

Historical experiment headers and results are not rewritten. Because filenames and version labels are part of saved provenance, even this naming cleanup can make an existing response file incompatible with new appends. Select a new batch before the next generation run; do not change old headers to bypass that protection. Existing answers remain available for evaluation.

## Implemented supporting changes without a prompt-version increment

- Prompt Markdown files are grouped in `prompts/`.
- The scenario is selected by filename in `main.py`; its actual filename, text, and version are recorded.
- Compact JSONL storage format v2 stores shared context once and reconstructs complete records. This storage version is distinct from Scenario V2 and does not by itself reduce API input tokens.

## 2026-10-21: third-test wiring and Change Log naming

- Renamed the former prompt-version README files to `CHANGELOG.en.md` and `CHANGELOG.zh-CN.md`, preserving bilingual history and updating links.
- Selected Counselor V2, Background V1, Scenario V2, and batch_003 in the main entry point. Model selection remains gpt-5.4-nano.
- Added filename settings for persona and background, optional background disabling, and a preview mode without API calls or experiment writes.
- Send the profile in each user message before the unchanged scenario. Save its exact text, filename, version, and hash in an optional compact-format metadata group; decoding reconstructs the complete message. Old no-background files remain readable.
- Save the actual selected persona filename/version. Reject appends when the profile or other conditions differ.
- Updated formal evaluation input validation to use the same saved prefix and background hash. The existing scenario checklist binding remains valid because the scenario body itself is unchanged.

## Current evaluation status

The evaluator currently selects Evaluation V2 with external Scenario V2 Checklist V1 for batch_003; the previously selected V3 remains available. See the Evaluation Agent's [Change Log](../Evaluation%20Agent/CHANGELOG.en.md). New generation inputs differ in both persona and background from batch_002, so a comparison is not an isolated background-only experiment.

## 2026-10-22: Scenario V3 added

Added `international_student_scenario_prompts V3.md` alongside V1 and V2. The five scenario IDs, order, and topics are retained. V3 clarifies people, event order, sources, and the immediate need while retaining the arithmetic error, deadline conflicts, unsupported student interpretations, and material unknowns. The academic case now explicitly concerns dropping one class; its page states tomorrow at 5 p.m. rather than an unspecified 5. The language case leaves the laughter motive unknown and distinguishes task allocation from an established speaking ban.

The paired evaluator-only supplement is `international_student_scenario_V3_checklist V3.md`; its exact-text bindings are refreshed. Current main selections, Counselor V2, Background V1, historical batches, and human-review files are unchanged. Use a new batch for V3; do not pair the new checklist with batch_003 or append V3 scenarios to old batches. No generation or scoring API was called.

## 2026-10-26: Reviewed Scenario V4 installed

Installed the user-approved `international_student_scenario_prompts V4.md` from the desktop review folder without changing its bytes. All five scenarios are single paragraphs. V4 revises the financial shortfall wording and makes ten days the student's current incorrect calculation from Monday to this Friday; revises the language and cultural cases; and removes the academic case's explicit statement that the page has not been checked. Laughter remains of unknown cause.

Use the paired Scenario V4 Checklist V4 with newly generated answers in a new batch, for example batch_004. Keep Counselor V2, Background V1, model settings, and other conditions fixed initially if comparing the scenario revision. Main selections, historical batches, and all older prompts are unchanged. No generation or evaluation API was called.

## 2026-10-26: batch_004 connected directly to main

main.py selects Scenario V4 and batch_004 with Counselor V2 and Background V1. Calling main() runs both configured models in sequence; passing model_name selects a single model. The file entry calls main() directly. PREVIEW_ONLY or main(preview=True) provides a no-call preview. After generation, the user runs Evaluation Agent/main.py separately. The unrequested root CMD/Python launchers and their guide were removed from the project. Historical data remain unchanged; wiring was verified without live model calls.
