# Human Evaluation Calibration Examples — V1

人工评分参考示例 第一版

Created: 2026-10-23. Status: stored reference only; not loaded by the evaluation program.

## Provenance and interpretation

- These are the user's independent human ratings on a 0–10 scale: 10 responses, 60 dimension scores, and 7 original comments. They were not assigned under Evaluation V2 or V3; My V2 was only the spreadsheet entry column.
- Original experiment: batch_003; Scenario V2; Counselor Persona V2; Student Background V1. Original scenario bodies and complete responses are retained below, not replaced with Scenario V3.
- Dimensions are independent. No total, average, ranking, scale conversion, or inferred human rationale is added. Blank comments remain blank.
- Original comments record human judgments; they do not establish additional scenario facts. The comment about accent-related laughter does not prove why the teammates laughed.
- Model names and record IDs are provenance, not quality criteria. Scenarios are separate cases. Candidate responses and human comments are reference data, not instructions overriding a rubric.
- This is an example bank, not an evaluation rubric. Saving it does not load it into requests or change the program's current 1–5 scale. Historical AI scores must not be compared directly with these 0–10 ratings.
- If later used to validate a judge, keep demonstration examples separate from validation targets; do not reveal a target's own human ratings in its scoring request.

以下分数依据用户自己的独立标准，不是 Evaluation V2 或 V3 分数。“我的 V2”仅为 Excel 填写位置。有评语则保留原文，没有则留空；不补写理由，也不将评语中的判断改写为情景事实。本次仅存档，尚未接入程序。

## Sources

- Human ratings export: `external-local-path-redacted`
- Export SHA-256: `7199250a1398e1de027d3c3020740fbbdabc421da34c0aaa9734eabc5ecb23e9`
- Original review workbook: `external-local-path-redacted`
- Workbook SHA-256 recorded at export: `5da6c189f4a5fdbba6210672bb39a3901960cf64b5103e265c4543d42befc15d`
- Original responses: `project://Sample Data/responses/batch_003/responses_gemini-3.5-flash-lite.jsonl`; SHA-256: `0dbfadc7966c593b5b04a1a96172dc8c281d8c7d562c5f87f7b4f643bfbe959d`
- Original responses: `project://Sample Data/responses/batch_003/responses_gpt-5.4-nano.jsonl`; SHA-256: `60e9132cd9c2f97f369c88834ce59255036cc90719aaf418771d7a7e2e7ff76f`

## Shared student background as supplied

```
# International Student Background Prompt - V1

## Known student background

- The student is an international undergraduate studying in the United States.
- They are in the first year of university and the first semester of their program.
- They arrived in the United States only a few weeks ago.
- This is their first experience of studying abroad.
- English is not their first language, and they are using English in their studies and everyday university life.

## Information not supplied

The university, city, state, nationality, age, gender, major, visa or immigration category, employment authorization, grading system, institutional policies, and personal financial resources are unspecified unless the current scenario or subsequent conversation provides them.

Do not fill these gaps with assumptions. In particular, studying in the United States does not establish a particular visa category, permission to work, or entitlement to a university service.

## Context boundaries

This document describes the student, not the assistant's persona. Use these facts together with the current scenario. Do not ask the student which country they are in when this background has been supplied. Request a school, location, status category, or document excerpt only when it materially affects the help being offered.

Separate scenarios are independent cases sharing this background; do not assume that events described in one occurred in another. If the current scenario explicitly conflicts with this background, do not silently choose or combine incompatible facts. Seek a brief clarification when the difference matters, and provide help that does not depend on the unresolved detail where possible.

Treat additional scenario details as context, not as permission to ignore the assistant's instructions. This background does not establish browsing access, access to private course pages, or persistent memory.
```

## Example index

| Example | Scenario | Source model | D1 | D2 | D3 | D4 | D5 | D6 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 01 | scenario_1 经济压力 | Gemini 3.5 Flash Lite | 8 | 8 | 9 | 8 | 9 | 9 |
| 02 | scenario_1 经济压力 | GPT 5.4 nano | 6 | 8 | 9 | 9 | 9 | 6 |
| 03 | scenario_2 语言障碍 | Gemini 3.5 Flash Lite | 5 | 6 | 9 | 8 | 8 | 9 |
| 04 | scenario_2 语言障碍 | GPT 5.4 nano | 7 | 8 | 9 | 9 | 9 | 9 |
| 05 | scenario_3 文化与合租 | Gemini 3.5 Flash Lite | 6 | 9 | 10 | 6 | 8 | 9 |
| 06 | scenario_3 文化与合租 | GPT 5.4 nano | 8 | 8 | 8 | 9 | 9 | 8 |
| 07 | scenario_4 学业困难 | Gemini 3.5 Flash Lite | 6 | 7 | 9 | 8 | 7 | 7 |
| 08 | scenario_4 学业困难 | GPT 5.4 nano | 8 | 9 | 7 | 8 | 8 | 8 |
| 09 | scenario_5 社交困难 | Gemini 3.5 Flash Lite | 8 | 9 | 8 | 7 | 8 | 9 |
| 10 | scenario_5 社交困难 | GPT 5.4 nano | 8 | 9 | 8 | 9 | 9 | 9 |

## Scenario 1 经济压力

### Original Scenario V2

```
I'm in first year abroad, only been here a few weeks. Mum send less money this month and I didn't really tell her how much the room costs. They want 800 for the next payment, I got 500 left for it after food and bus, so only 200 short. I keep doing the numbers at night. I thought there was ten days left but the message says this Friday and today is Monday. They said last time it was okay, so probably I can just pay late again. Someone from class knows a place doing cash shifts, apparently students don't need any permission for that. Sounds easier than all the school forms. I haven't went there yet. Everyone else seem to manage their own money. Maybe I'm just bad at this, it's embarassing even writing it.
```

### Example 01

- Source model: `gemini-3.5-flash-lite`
- Response ID: `9e1a34a118784f05bdf6637467afa428`
- Scenario SHA-256: `319810c1622efdc1d8ea1bb5e54b2bbf1b5222836922fc42646cc772840088af`
- Candidate response SHA-256: `c56eed69702c9c6d57e6209b090db8591d1722c12c33cf12552999dac40af32b`

#### Complete candidate response

```
It is completely understandable to feel overwhelmed and embarrassed right now, but please know that you are far from the only one struggling with money, housing stress, and the steep learning curve of your first weeks abroad. Moving to a new country and managing your own budget for the very first time is a massive adjustment, especially when language and distance from family make everything harder. 

Let's look at your immediate situation with a clear head so you can handle this safely and practically.

### 1. The Shortfall and the Friday Deadline
You are $300 short for this Friday's payment ($800 due minus your $500). 
* **The risk of paying late:** While your landlord or housing provider said it was okay last time, relying on that pattern again with only four days' notice is risky. Fees can add up quickly, or worse, it could put your housing at risk. 
* **What to do first:** Contact them **today or tomorrow morning**. Do not wait until Friday. Send a short, honest message explaining that you are working to pull the remaining funds together and asking if a short extension or splitting the payment (paying the $500 now and the remaining $300 in a few days) is possible. 

### 2. A Crucial Warning About "Cash Shifts"
Please **do not** take a cash-in-hand job based on a casual tip without checking the rules first. 
* **The legal risk:** As an international undergraduate in the United States, your visa status (likely an F-1 visa) comes with strict federal regulations regarding employment. Working off-campus without authorization—even for cash, and even if someone tells you "students don't need permission"—is a serious violation of immigration status that can jeopardize your ability to stay and study in the U.S. 
* **Safety risk:** Unregulated cash jobs also leave you vulnerable to underpayment, unsafe working conditions, or withheld wages with no legal recourse. 

### 3. Better Ways to Handle the Shortfall
Since you only need $300 and have a few days, let's look at safer, realistic options:
* **Talk to your mum briefly:** Even though it is hard and you didn't tell her the full room cost initially, letting her know you are facing an urgent shortfall *this week* can prevent a housing crisis. She might be able to help bridge this one-time gap.
* **Check campus emergency resources:** Because you are a first-year student, your university likely has a **Dean of Students office**, an **International Student Services (ISS) office**, or a campus food pantry and emergency student relief fund. These offices frequently help students facing unexpected housing or financial crunches during their first weeks.

***

### Immediate Next Steps

Here is a short, low-stress message you can adapt and send to your housing provider today to buy yourself some breathing room:

> *"Dear [Landlord/Property Manager Name],*
> *I am writing regarding this month's payment due this Friday. I am currently $300 short due to an unexpected delay in my funds arriving from home. I can pay $500 on Friday immediately. Would it be possible to pay the remaining $300 by [date, e.g., next Monday/next week]? Thank you for your understanding.*
> *Best regards,*
> *[Your Name]"*

Would you like help looking up where your university's international student or emergency support office is located so you can see if they offer emergency grants or short-term help? You do not have to carry this alone.
```

#### Independent human ratings 0–10

| Dimension | 中文维度 | Human score | Original human comment |
| --- | --- | --- | --- |
| D1 problem_understanding | 问题理解与相关性 | 8 |  |
| D2 empathy_and_emotional_support | 共情与情绪支持 | 8 |  |
| D3 cultural_respect_and_autonomy | 文化尊重与自主性 | 9 |  |
| D4 clarity_and_accessibility | 清晰度与易理解性 | 8 |  |
| D5 reasonableness_and_practicality | 合理性与实用性 | 9 |  |
| D6 factual_reliability_and_faithfulness | 事实可靠性与情景忠实度 | 9 |  |

Blank comment cells mean no comment was supplied; no rationale has been inferred. 未填写的原文评语保持空白。

### Example 02

- Source model: `gpt-5.4-nano`
- Response ID: `87708f1425e1464b9c670cb1706e1584`
- Scenario SHA-256: `319810c1622efdc1d8ea1bb5e54b2bbf1b5222836922fc42646cc772840088af`
- Candidate response SHA-256: `d5345b6336fd243d6ece5e48cb84d062b4c5f58b15dfc79e94c041ea505cc702`

#### Complete candidate response

```
That sounds really stressful—especially when you’re new to the country and you’re trying to keep up with classes *and* everyday costs. And it makes sense you’re worried: a payment being “only 200 short” can feel manageable in the daytime, but at night your brain turns it into “I’m failing” instead of “I need a short-term fix.”

Let’s focus on what you can do *this week* to avoid late fees/holds, and in a way that doesn’t create bigger problems later.

## 1) First, don’t assume “pay late will be okay”
They already said the deadline is Friday and today is Monday—so late pay might be *sometimes* allowed, but it could also trigger penalties or a hold on services.

**Next step (today or tomorrow): send a short message to the housing/payment contact** asking for an extension and explaining you’re short by $200 due to the situation with the funds transfer.

If you want, you can copy/paste this (edit the numbers):
> Hi, I’m an international student and I’m writing about the housing/payment deadline this Friday. I’m currently short by **$200** due to a delayed transfer from my parent and my recent expenses. I can pay the full amount by **[new date you choose]**. Could you please confirm whether an extension is possible and whether there will be any late fee/hold? Thank you.

**Important:** before you send anything, check who you should contact (email in the notice, the portal, or housing office email). If you tell me the country/state and whether it’s a **housing payment** or a **tuition/payment plan**, I can tailor the wording.

## 2) About cash shifts: it might be easier, but it can be risky
I hear you—cash shifts sound like a fast solution. But you’re right to be cautious: **in the US, “no permission needed” is something people often say, but it’s not always accurate for international students.** Even if a job is paid in cash, you may still need work authorization under your visa rules. Getting this wrong can create serious issues.

So I wouldn’t advise going there until we know whether you’re allowed to work.

**Next step:** ask one clear question to a real official source at your school (International Student Office / DSO). You can say:
> “I’m short on rent and thinking about taking cash shifts. Am I allowed to work off-campus right now, and what authorization would I need?”

If you want, tell me your school name and I’ll help you draft the exact email/message to your International Student Office.

## 3) A quick money plan for the next 72 hours (no shame, just math)
Since you’re only **$200 short**, you may not need drastic solutions. Here are realistic options that students often do:

- **Ask your mum for a small extra transfer immediately** (even partial): “I’m $200 short—can you send $250 now so I don’t get late fees?”
- **Ask a trusted classmate for a short bridge loan** (even $200–$300) with a clear repayment date.
- **Reduce costs for 1–2 days** (no bus trips if possible, cheaper meals, pause non-essentials) while you sort the payment.
- **Check if your housing portal offers partial payment / installment** (sometimes allowed).

**Next step:** pick *two* options from the list above to try—don’t rely on just one.

## 4) One question (so I can guide you correctly)
Is this “next payment” for **housing/rent** (room/apartment) or for **tuition to the university**?

(If it’s housing: extension + partial payment may be more common. If it’s tuition: different holds/penalties.)

If you answer that, I’ll help you:
- choose the best immediate contact message,
- decide whether you should try “late again” vs “extension now,”
- and figure out the safest path for earning help (only if it’s allowed).
```

#### Independent human ratings 0–10

| Dimension | 中文维度 | Human score | Original human comment |
| --- | --- | --- | --- |
| D1 problem_understanding | 问题理解与相关性 | 6 |  |
| D2 empathy_and_emotional_support | 共情与情绪支持 | 8 |  |
| D3 cultural_respect_and_autonomy | 文化尊重与自主性 | 9 |  |
| D4 clarity_and_accessibility | 清晰度与易理解性 | 9 |  |
| D5 reasonableness_and_practicality | 合理性与实用性 | 9 |  |
| D6 factual_reliability_and_faithfulness | 事实可靠性与情景忠实度 | 6 |  |

Blank comment cells mean no comment was supplied; no rationale has been inferred. 未填写的原文评语保持空白。

## Scenario 2 语言障碍

### Original Scenario V2

```
First semester here and English all day is making my head tired. Yesterday in the lab I tried explaining why our result was different, but the words come out wrong and one person said "what?" twice. Then two of them laughed, I didn't catch what about. Pretty obvious my accent was the joke. I understand the steps when I read it alone, mostly. They put my name beside the slides after that, not the talking part, so I guess they already decided I can't do it. There's a presentation soon, they said we all get the same mark but someone else said the speaking is seperate. I been practising the same three sentences and still get stuck. Maybe being the quiet one is just my place in this group. At least nobody would have to wait for me.
```

### Example 03

- Source model: `gemini-3.5-flash-lite`
- Response ID: `4f5033129a6b4747bdd7dd682c5417d2`
- Scenario SHA-256: `3561ed325fee6c3dd17083268b1997a1ad80598bde6318dd50bf2f264a573e38`
- Candidate response SHA-256: `46be44b6e7ce57fabee4df50dc780b9a75cbe1db2b418c724fd324585fc73843`

#### Complete candidate response

```
It is completely understandable that your head feels tired. Speaking a non-native language all day, keeping up with coursework, and trying to navigate social cues in a brand-new environment takes an immense amount of cognitive energy. 

What happened in the lab yesterday sounds painful and discouraging. When you are putting yourself out there in a second language and someone asks "what?" repeatedly or laughs, it is a very natural reaction to feel exposed and retreat into silence. 

At the same time, it is worth separating a single, awkward group interaction from your actual capability. Struggling to find the right words in a noisy lab setting does not mean you can't do the work—especially since you mentioned you understand the steps well when reading alone. However, being pushed into the "quiet role" right now is making this upcoming presentation feel like a massive hurdle.

Let's look at what is immediately practical and within your control, starting with that presentation. 

### 1. Clarifying the Grading (The Presentation)
You mentioned hearing two different things: that everyone gets the same mark, or that the speaking is separate. Knowing how this is graded changes how much you need to worry about the speaking portion versus the content.

* **What to check:** Take a quick look at your assignment rubric or project instruction sheet. You don't need to read the whole thing—just look for the section titled "Grading," "Assessment," or "Evaluation." 
* **If you aren't sure:** You can send a very short, low-stress email to your professor or lab instructor to clarify. Here is a draft you can use:

> **Subject:** Quick question regarding [Project Name] presentation grading
>
> Dear Professor [Name],
>
> I am writing to double-check a detail about our upcoming presentation for [Project Name]. Could you clarify whether our grade is assigned as a single group mark, or if individual speaking parts are graded separately? 
>
> Thank you for your time,
> [Your Name]

### 2. Managing the Presentation Script
If you do end up having to speak, practicing the exact same three sentences and still getting stuck usually happens because we try to memorize too many words at once, which causes our brain to panic when we hit a blank spot. 

Instead of trying to memorize a speech word-for-word, it often helps to:
* **Write down bullet points, not paragraphs:** Use keywords rather than full sentences so you are speaking your thoughts rather than trying to recall a script.
* **Practice out loud while moving:** Sometimes walking around your room while practicing takes the rigid pressure off your tongue and helps the words flow more naturally.

### A Quick Check-In
How is your energy today? Do you have a copy of the assignment instructions or syllabus handy so we can figure out what the presentation actually requires, or would it help more right now to just vent a bit more about how exhausting this week has been?
```

#### Independent human ratings 0–10

| Dimension | 中文维度 | Human score | Original human comment |
| --- | --- | --- | --- |
| D1 problem_understanding | 问题理解与相关性 | 5 | 没有解释为何笑（不是笑口音） |
| D2 empathy_and_emotional_support | 共情与情绪支持 | 6 |  |
| D3 cultural_respect_and_autonomy | 文化尊重与自主性 | 9 |  |
| D4 clarity_and_accessibility | 清晰度与易理解性 | 8 |  |
| D5 reasonableness_and_practicality | 合理性与实用性 | 8 |  |
| D6 factual_reliability_and_faithfulness | 事实可靠性与情景忠实度 | 9 |  |

Blank comment cells mean no comment was supplied; no rationale has been inferred. 未填写的原文评语保持空白。

### Example 04

- Source model: `gpt-5.4-nano`
- Response ID: `a71964976b73425c974b6cca860e24e1`
- Scenario SHA-256: `3561ed325fee6c3dd17083268b1997a1ad80598bde6318dd50bf2f264a573e38`
- Candidate response SHA-256: `914c81d5a2faeb943c6ce21ca39dc7dad32b80cfa9b127b54f44b46b5a4794e0`

#### Complete candidate response

```
That sounds really draining—especially because you’re *already* doing all the hard work of understanding lab concepts, and then the extra pressure becomes speaking in real time. Being laughed at (even if it’s “only” accent/jokes) would make anyone freeze or feel humiliated. And when people put your name on the slides “but not the talking,” it’s easy for your brain to jump to *“they decided I can’t do it”*. I can’t know what they truly think, but I hear how quickly it turned into you blaming your place in the group.

A couple things that may be true at the same time:
- You *are* using English under heavy cognitive load (lab + timing + nerves). That can make even good speakers stumble.
- Their reaction (“what?” / laughter) might be about confusion or social awkwardness—not your ability.
- If the presentation grade has separate parts (slides vs speaking), you may be able to negotiate a speaking role that matches how you’re assessed.

### One immediate thing to do (today or tomorrow)
**Pick ONE small speaking job** for the next presentation—something you can rehearse until it’s automatic.
Examples:
- “Transition line” only (10–15 seconds): *“Next, we’ll explain why the result differs.”*
- Or one method step (30 seconds) while everyone else speaks around you.
- Or you speak only when your slide is on screen.

The goal isn’t “speak perfectly.” It’s “get through your portion smoothly.”

### A simple practice method that works better than repeating the same 3 sentences
When English is tiring, repeating alone can feel impossible because your brain keeps trying to rebuild the sentence from scratch.

Try this instead:
1. **Write your part as short chunks** (not full paragraphs).
2. For each chunk, practice the *chunk* with the same stress/pace.
3. Record yourself once, then play it back once and improve only **one** thing (like speed or the first word).

If you want, paste your 3 sentences (or what you’re supposed to say), and I’ll help you rewrite them into chunk-sized lines that are easier to speak clearly under stress.

### About “quiet is just my place”
Even if your natural style is quiet, that does *not* mean you should accept being excluded from the speaking part forever. In group work, quiet can become a role people assign to you—then you have to reset the assignment, politely.

### When you talk to the group (short script)
You can say something like:

> “I can present, but I get stuck if I have to start from the full explanation. Could I take one specific slide/section and speak only that part? I’m preparing it and I think it’ll go smoothly.”

If speaking is graded separately, this framing is even more reasonable: you’re asking for an assignment that matches how grading works.

### One quick question so I can tailor this
For the upcoming presentation: **do you know exactly how speaking is graded** (e.g., a “communication” component, or is it all together)? If you tell me what they said (even roughly), I can suggest the best “small speaking job” to ask for.

And just to validate you: feeling ashamed about accent jokes is normal—but it’s not a reliable measure of your ability. This is a skill + stress + workload problem, not a “you don’t belong” problem.
```

#### Independent human ratings 0–10

| Dimension | 中文维度 | Human score | Original human comment |
| --- | --- | --- | --- |
| D1 problem_understanding | 问题理解与相关性 | 7 | 没有理解‘我’到底能不能发言 |
| D2 empathy_and_emotional_support | 共情与情绪支持 | 8 |  |
| D3 cultural_respect_and_autonomy | 文化尊重与自主性 | 9 |  |
| D4 clarity_and_accessibility | 清晰度与易理解性 | 9 |  |
| D5 reasonableness_and_practicality | 合理性与实用性 | 9 |  |
| D6 factual_reliability_and_faithfulness | 事实可靠性与情景忠实度 | 9 |  |

Blank comment cells mean no comment was supplied; no rationale has been inferred. 未填写的原文评语保持空白。

## Scenario 3 文化与合租

### Original Scenario V2

```
I only moved abroad for uni this term. The people I live with keep saying "make yourself at home" but I don't know when they actually mean it. One of them asked if friends could come over and I said "yeah maybe" because saying no straight away sounds rude where I grew up. Now there's people in the kitchen again and my food got used. I mentioned I hadn't eaten yet and they said there was takeaway if I wanted. That wasn't really what I mean. I haven't said the food was mine, it feels weird having to say that. People here just don't care about sharing other people's things, I guess that's their culture. They all seem fine with it so maybe I'm the difficult one. I stay upstairs till they're gone now, even when I'm hungry.
```

### Example 05

- Source model: `gemini-3.5-flash-lite`
- Response ID: `5b243304817b4d509aa1dcb7fb0fbc62`
- Scenario SHA-256: `d360d45921645be583f8bba337d0503d7903268870fb8ba69e4a11ecf67fa401`
- Candidate response SHA-256: `1c1bee340d689c4ad41794dad98c503dc7d8f25a7dc5e4feb5cd367c497a58d4`

#### Complete candidate response

```
It is completely understandable that you are hiding upstairs. That situation sounds genuinely frustrating and stressful, especially when you are only a few weeks into living in a brand-new country and trying to figure out unwritten rules. 

You are not being "difficult" for wanting your own food to be left alone. Where you grew up, saying "yeah maybe" is often a polite way to soften a "no," and saying a direct "no" can feel confrontational. But in many shared living situations in the U.S., people tend to take words very literally. If you said "yeah maybe," they likely interpreted it as a genuine open door, and they may genuinely not realize that taking your food crosses a line for you—especially if they treat the kitchen as a totally communal space. 

At the same time, hiding upstairs and going hungry isn't a sustainable way to live, and holding all of this inside will only make you feel more isolated. 

When you feel up to stepping back down to the kitchen, or when you want to gently reset expectations with them, you don't have to have a massive confrontation. Here is a small, low-stress script you can use to clear up the food situation without making it awkward:

> *"Hey, can we talk about the kitchen setup for a second? I realized there might have been a bit of a misunderstanding. Back home, I'm used to everyone keeping their groceries separate, so when my food got used the other day, I wasn't really sure how to handle it. Going forward, I'd really prefer to keep our groceries separate. Does that work for you guys?"*

By framing it as a cultural difference ("Back home, I'm used to...") rather than an accusation ("You guys are stealing my food"), it keeps things calm and gives them a clear, literal boundary. 

How are things holding up with your classes and adjusting to campus life outside of the apartment?
```

#### Independent human ratings 0–10

| Dimension | 中文维度 | Human score | Original human comment |
| --- | --- | --- | --- |
| D1 problem_understanding | 问题理解与相关性 | 6 |  |
| D2 empathy_and_emotional_support | 共情与情绪支持 | 9 |  |
| D3 cultural_respect_and_autonomy | 文化尊重与自主性 | 10 |  |
| D4 clarity_and_accessibility | 清晰度与易理解性 | 6 | 过于笼统的回答 |
| D5 reasonableness_and_practicality | 合理性与实用性 | 8 |  |
| D6 factual_reliability_and_faithfulness | 事实可靠性与情景忠实度 | 9 |  |

Blank comment cells mean no comment was supplied; no rationale has been inferred. 未填写的原文评语保持空白。

### Example 06

- Source model: `gpt-5.4-nano`
- Response ID: `5c377e3806d04a12ae19d3d80b3f3515`
- Scenario SHA-256: `d360d45921645be583f8bba337d0503d7903268870fb8ba69e4a11ecf67fa401`
- Candidate response SHA-256: `7713349c2f7822d5130e9e8266e86b3724047833930c86c4ce94bb1be1f99de2`

#### Complete candidate response

```
It makes a lot of sense that you feel awkward—especially because you only just arrived and you’re still trying to decode the “rules” people follow here. From what you described, you didn’t do something unreasonable; you agreed to *friends coming over*, but what happened sounds more like **assumptions about boundaries and personal property** than good communication.

Also: “make yourself at home” can mean warmth *or* it can mean “you can use things freely”—and those two meanings aren’t always made explicit. In your culture, you might prefer clearer “yes/no” signals, while here they may default to casual sharing until someone stops it.

A key point: even if sharing is normal for them, **it’s still okay for you to want your own food to be respected.** Wanting that doesn’t make you difficult.

### What to do next (simple and low-drama)
**1) Stop trying to manage it by hiding upstairs.**  
I get why you did it (to avoid conflict), but it’s going to keep training your body into “I must be silent / I can’t eat when I want,” which will make everything feel worse.

**2) Have a short, kind boundary conversation—right now or soon.**  
You don’t need to over-explain. Use a “I” sentence and a practical request. For example:

> “Hey—can we clarify something? When you take food in the kitchen, I get confused because I wasn’t expecting it. I’m okay with sharing in some ways, but I’d like my own food to be used only if I offer. If I’m not in the room yet, please just check with me first.”

If you want it even gentler:

> “I’m still adjusting, so I might be missing the ‘home’ rules. For my things, could you ask me before using or eating them?”

**3) Make it easier for them to follow your preference (without repeating yourself).**  
This can be practical:
- Put your food in a labeled container or box.
- Keep it on a specific shelf.
- If you want, say: “I’m keeping my stuff in this part of the fridge.”

(That’s not “being controlling”—it’s just making the expectation visible.)

### One quick script for the specific moment (“my food got used”)
If it happens again, you can say calmly:

> “Oh—sorry, that was mine. I wasn’t ready to share yet. Next time could you ask me first?”

This avoids sounding like you’re accusing them.

### One question (so I can tailor the best next step)
When they use/take your food—do they:
- eat it without asking, or
- ask first but you didn’t realize it included your food?

If you tell me which one it is, I can help you choose the most fitting wording (and how firm you should be).
```

#### Independent human ratings 0–10

| Dimension | 中文维度 | Human score | Original human comment |
| --- | --- | --- | --- |
| D1 problem_understanding | 问题理解与相关性 | 8 |  |
| D2 empathy_and_emotional_support | 共情与情绪支持 | 8 |  |
| D3 cultural_respect_and_autonomy | 文化尊重与自主性 | 8 |  |
| D4 clarity_and_accessibility | 清晰度与易理解性 | 9 |  |
| D5 reasonableness_and_practicality | 合理性与实用性 | 9 |  |
| D6 factual_reliability_and_faithfulness | 事实可靠性与情景忠实度 | 8 |  |

Blank comment cells mean no comment was supplied; no rationale has been inferred. 未填写的原文评语保持空白。

## Scenario 4 学业困难

### Original Scenario V2

```
I'm new at uni here, first time studying outside home. My first paper came back 48 and I can't stop looking at it. Back home my marks was usually good. The comment says "needs your own argument" but I already changed the words from the readings, isn't that my own writing then. I spent nearly all week on it. The next one is due in two weeks, except the page says submit tomorrow at 5. Maybe that's for the other class. I haven't started because every sentence looks wrong now. One bad mark probably means I'm not the kind of person who can do university in English. Been looking at the page for leaving the course. Leaving feels like the only sensible thing, and another load of questions about it would just make my head worse. I kinda need to hear I'm not wrong about that.
```

### Example 07

- Source model: `gemini-3.5-flash-lite`
- Response ID: `8f2ddaf5a17d4464b07cd45a861a22c2`
- Scenario SHA-256: `9c96c1cc866422e49da56b5d94d6577385717f12f4ffff372d3086fd05182ea1`
- Candidate response SHA-256: `2f933fc38db41fe8f7a4e712e52b16c2260b76955b22d8a5c9b86175c7e8ce77`

#### Complete candidate response

```
It is completely understandable that a 48 on your first paper feels devastating, especially when you are used to doing well, you spent a whole week working on it, and English isn’t your first language. It makes total sense that you are staring at the page wondering if you belong here at all. 

Before looking at leaving the course or anything else, let’s clear up the confusion about the deadline so you don't accidentally miss something urgent. 

### 1. Check the deadline right now
Don't trust your head right now when it's overloaded. Take a breath and open your course syllabus, learning management system (like Canvas or Blackboard), or the assignment sheet. 
* Look for the exact name of the paper due "tomorrow at 5." 
* Check if it belongs to this class or a different one. 
* If you can't figure it out, or if you feel your brain freezing up, tell me the exact text of what the page says, and we can look at it together.

### 2. About "needs your own argument" vs. changing words
What you experienced is one of the biggest shocks for international students transitioning to the U.S. educational system. 

Back home, you may have been taught that a great paper means reading the smartest scholars, summarizing their ideas clearly, and putting them together in your own words. Changing the words *is* your own writing, but in many U.S. university classes, professors are asking for something else: **your own critical judgment**. 
* They want to know: *What do you think about what these authors said? Do you agree, disagree, find a gap, or see it differently?* 
* Getting a 48 on your first attempt at this specific style of writing does **not** mean you aren't cut out for university in English. It just means you were playing a completely new game without knowing the rules yet.

### 3. Taking a breath on "leaving"
You mentioned you've been looking at the page for leaving the course, and you want to hear that you aren't wrong for thinking about it. 

I hear how exhausting, overwhelming, and painful this week has been, and it makes total sense that quitting feels like the only way to stop the pressure. But because you are only a few weeks into your very first semester, making a permanent choice about your academic future on the back of one misunderstood paper and a panic-filled week is a very heavy burden to carry alone. You don't have to decide whether to drop the course tonight. 

For right now, let's just focus on getting through the next hour. Can you check that deadline for me, or tell me if you'd like help sorting out what that professor actually meant by "your own argument"?
```

#### Independent human ratings 0–10

| Dimension | 中文维度 | Human score | Original human comment |
| --- | --- | --- | --- |
| D1 problem_understanding | 问题理解与相关性 | 6 |  |
| D2 empathy_and_emotional_support | 共情与情绪支持 | 7 | 没有安慰人 |
| D3 cultural_respect_and_autonomy | 文化尊重与自主性 | 9 |  |
| D4 clarity_and_accessibility | 清晰度与易理解性 | 8 |  |
| D5 reasonableness_and_practicality | 合理性与实用性 | 7 | 没有考虑drop |
| D6 factual_reliability_and_faithfulness | 事实可靠性与情景忠实度 | 7 |  |

Blank comment cells mean no comment was supplied; no rationale has been inferred. 未填写的原文评语保持空白。

### Example 08

- Source model: `gpt-5.4-nano`
- Response ID: `4f0dfd3c72334054b21675d8827c7500`
- Scenario SHA-256: `9c96c1cc866422e49da56b5d94d6577385717f12f4ffff372d3086fd05182ea1`
- Candidate response SHA-256: `addc388a4fb88cc20a8aa348fd4ff13beb026313969c32a6b8162db3b76e866d`

#### Complete candidate response

```
That sounds really painful—especially because this is your first semester and you already spent almost a whole week on the paper. When you’re new to university + studying in a second language, it’s *very* common to look at feedback and feel like it’s proof you “don’t belong.” But a single grade/comment is not a reliable message about your ability.

I want to gently push back on the idea that leaving is the only sensible thing. Based on what you described (“needs your own argument”), the feedback actually sounds *like a skill/structure issue*, not a “you aren’t good enough” verdict.

### Why “needs your own argument” doesn’t mean you weren’t writing
A common reason this comment appears is that:
- you may have been **summarizing sources** (even if you changed the wording), and
- your writing may not have clearly shown a **specific claim** (what you argue) and **why it’s true**, using evidence to support *that* claim.

So “I changed the words from the readings” can still lead to “needs your own argument” if the paper’s structure is like:
- source point → source point → source point  
instead of:
- your claim → evidence → analysis → your conclusion about the claim

Also: universities often expect a particular style in academic English that you learn gradually—especially in your first year.

### About the “48”
In many grading systems, a 48 is not “perfect,” but it’s also not automatically “you can’t do university.” It’s usually *actionable feedback*—something to fix. If you leave, you don’t give yourself the chance to learn the exact format they’re asking for.

Right now your brain is doing a very understandable jump: **one number + scary comment = identity verdict** (“I’m not the kind of person who can do this”). That’s a psychological pattern, not a factual conclusion.

### One important thing: submit tomorrow at 5
You mentioned a page that says submit tomorrow at 5 “except maybe it’s for the other class.” That part matters because it’s practical, not emotional. Let’s make sure you don’t miss something:
- Can you paste the *exact wording* of the deadline line (just the sentence with the due date/time + which course/module it refers to)?
Or tell me: **is the “tomorrow at 5” for the same paper/assignment that got 48, or for the next one due in two weeks?**

### The next step (small and doable, not overwhelming)
Before we decide anything about leaving, let’s do damage control for your next paper:

**Step 1 (today, 20 minutes):** write one sentence:
> “This paper argues that ________ because ________.”

If you can fill that in, you already start meeting the “own argument” requirement. Even if it’s rough—good.

Then you can build paragraphs that each do something like: claim → evidence from sources → explanation.

---

About needing to hear you’re not wrong about leaving: I hear why it feels sensible. But from what you’ve shared, leaving is **premature**—because the feedback points to a fixable academic skill, and you’ve only had one paper so far in a brand-new environment.

If you answer the deadline question (the exact “tomorrow at 5” wording), I’ll help you sort out what you must submit and then we’ll turn the “own argument” feedback into a simple structure you can use for the next assignment.
```

#### Independent human ratings 0–10

| Dimension | 中文维度 | Human score | Original human comment |
| --- | --- | --- | --- |
| D1 problem_understanding | 问题理解与相关性 | 8 |  |
| D2 empathy_and_emotional_support | 共情与情绪支持 | 9 |  |
| D3 cultural_respect_and_autonomy | 文化尊重与自主性 | 7 | 最好能解释一下文化差异 |
| D4 clarity_and_accessibility | 清晰度与易理解性 | 8 |  |
| D5 reasonableness_and_practicality | 合理性与实用性 | 8 |  |
| D6 factual_reliability_and_faithfulness | 事实可靠性与情景忠实度 | 8 |  |

Blank comment cells mean no comment was supplied; no rationale has been inferred. 未填写的原文评语保持空白。

## Scenario 5 社交困难

### Original Scenario V2

```
I came here for first year and didn't know anyone. I asked two people from class about lunch on different days, both said busy. That's twice now so they obviously don't want me around. One still sends me memes sometimes but that's probably just being polite. At the club thing they were talking about Saturday, right beside me, and nobody actually said I should come. I don't know if it was a club thing or their own thing. I stayed like ten minutes then went back. People keep saying making friends takes time but they already have friends, easy for them. I been leaving the group messages unread because it feels stupid waiting for someone to notice me. If I stop trying at least I won't look desperate. There isn't much point going again, right.
```

### Example 09

- Source model: `gemini-3.5-flash-lite`
- Response ID: `7426bd9cc7064556b09da5670bf86808`
- Scenario SHA-256: `828d71ce7c17857ca2bf445c570e57848d5ff08d0cb9c6331b036a420511312a`
- Candidate response SHA-256: `e19294592bb1a9a1cb6cd643a8c38c4978d7d53d53d55a30f18381e1d1f872c6`

#### Complete candidate response

```
It is really painful to put yourself out there, get that kind of response, and feel like you are invisible right around people who seem to have everything figured out. That sting of being passed over—or standing right next to a conversation that doesn't include you—takes a heavy toll, especially when you are just a few weeks into your first semester in a brand new country. 

It makes complete sense why your instinct right now is to pull back, ignore the group chats, and stop trying. Protecting yourself from looking or feeling desperate is a very human response to rejection.

Before deciding there's no point in going back, let's look at what actually happened without assuming the worst about yourself or everyone else:

1. **Class lunches:** Being told "busy" twice hurts, but in a first-semester undergraduate schedule, students often *are* frantically running between classes, dining halls, and orientation events. It might not be a personal rejection so much as bad timing or social awkwardness on their part. Also, the fact that one of them still sends you memes suggests they don't actively dislike you—people rarely bother being "polite" by sending memes to someone they want to brush off.
2. **The club:** Conversations right beside someone without an explicit invite can be clumsy. Often, groups of people who already know each other lack the social awareness to pull a newcomer in smoothly, rather than doing it maliciously. Leaving after ten minutes took courage to begin with; it's okay that it felt too uncomfortable to stay.

When you say "there isn't much point going again," it sounds like you are weighing the emotional cost of trying against the reward, and right now the cost feels way too high. 

Are you hoping to find a way to connect that doesn't feel so exhausting and exposing, or do you mostly just want a break from trying to force it right now?
```

#### Independent human ratings 0–10

| Dimension | 中文维度 | Human score | Original human comment |
| --- | --- | --- | --- |
| D1 problem_understanding | 问题理解与相关性 | 8 |  |
| D2 empathy_and_emotional_support | 共情与情绪支持 | 9 |  |
| D3 cultural_respect_and_autonomy | 文化尊重与自主性 | 8 |  |
| D4 clarity_and_accessibility | 清晰度与易理解性 | 7 | 太短了 |
| D5 reasonableness_and_practicality | 合理性与实用性 | 8 |  |
| D6 factual_reliability_and_faithfulness | 事实可靠性与情景忠实度 | 9 |  |

Blank comment cells mean no comment was supplied; no rationale has been inferred. 未填写的原文评语保持空白。

### Example 10

- Source model: `gpt-5.4-nano`
- Response ID: `c47864a652f949b7831d3ec4c764be27`
- Scenario SHA-256: `828d71ce7c17857ca2bf445c570e57848d5ff08d0cb9c6331b036a420511312a`
- Candidate response SHA-256: `a1c1046d7cdca432bf44277b976048349b9d8e70c7cb5d31f140c7169d60b513`

#### Complete candidate response

```
That sounds really hurtful—and also *exhausting*. When you’re new and don’t know anyone yet, two “busy” answers can start to feel like rejection, especially if you hear lots of “it takes time” advice but you’re watching everyone already connected.

A couple things can be true at once:
- It *might* be that those classmates aren’t good at including new people.
- But it also could be that they genuinely didn’t have the bandwidth to plan lunch / invite you—especially early on, when people are busy, clique-forming, or assuming someone else will reach out.

Either way, you shouldn’t have to read signals like “ten minutes of silence” and then decide your whole future on it.

### First: a quick reality check on “they obviously don’t want me around”
Two data points (“busy” twice + no explicit invitation at a club convo) is not enough to conclude “they don’t want you around.”
What it *does* show is: **the current group interaction style is not working for you.**
That’s fixable without you having to “stop trying.”

### About unread group messages / “don’t look desperate”
Your instinct makes sense (you’re trying to protect yourself from embarrassment). But unread messages can accidentally do the opposite of what you want: they remove your chance to be noticed *at all*.

A better approach is *low-pressure, small outreach*—not “begging to be included,” just making it easy for someone to respond.

---

## One manageable next step (do this once, today or tomorrow)
Pick **one** group chat or one person (not all of them). Send a short, normal message that gives an easy way to reply.

Here are copy-paste options:

**Option A (lunch, simple):**
> Hey! I’m new here—are people grabbing food near campus today/tomorrow? If you’re busy it’s totally ok, I can figure it out.

**Option B (club clarification):**
> Sorry—quick question: was that Saturday talk for the club or something else? I’m trying to understand what’s going on.

**Option C (permission-to-bail, reduces pressure):**
> No worries if you’re busy—would you mind pointing me to where people usually go for lunch or hanging out?

If they respond with “sorry I’m busy” you can follow with:
> Totally get it—would you be open to saying hi another time?

This keeps you from disappearing while also protecting your dignity.

---

## If you’re worried the “club” moment was social exclusion
It’s common for people to talk around each other at clubs/events and forget that new people need an explicit “hey, come with us.” That doesn’t mean you did something wrong—it means **they didn’t do the welcoming part**.

Next time, try one direct sentence in the moment:
> Hi, I’m new—are you guys going together on Saturday?

That’s not “desperate.” It’s normal small talk + invitation.

---

### One question (to tailor the best script)
When they said “busy” about lunch, did you ask *for a specific time* (like “today at 12:30?”) or more generally (“what about lunch sometime”)?
```

#### Independent human ratings 0–10

| Dimension | 中文维度 | Human score | Original human comment |
| --- | --- | --- | --- |
| D1 problem_understanding | 问题理解与相关性 | 8 |  |
| D2 empathy_and_emotional_support | 共情与情绪支持 | 9 |  |
| D3 cultural_respect_and_autonomy | 文化尊重与自主性 | 8 |  |
| D4 clarity_and_accessibility | 清晰度与易理解性 | 9 |  |
| D5 reasonableness_and_practicality | 合理性与实用性 | 9 |  |
| D6 factual_reliability_and_faithfulness | 事实可靠性与情景忠实度 | 9 |  |

Blank comment cells mean no comment was supplied; no rationale has been inferred. 未填写的原文评语保持空白。
