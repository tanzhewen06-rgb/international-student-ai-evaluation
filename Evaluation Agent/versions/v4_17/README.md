# Evaluation V4.17

This release applies independently checked advisory recommendations to V4.16: L1 equivalent-wording credit, relevance-based materiality tags, a targeted factual-kind/impact repair, and nested Markdown quote normalization. The numeric scoring contract remains V4.12. The root entry evaluates the same ten saved answers with the same GPT, Gemini and DeepSeek judges, twice each (60 initial judgments). The Single entry also points to V4.17 and retains its existing selection.

The formula, anchors, item mappings, deductions, severity floors/caps, output schema, field order, model settings, console format and maximum two attempts are unchanged. E1, E2, E3, C4, S4, L3 and the existing consistency rules are retained. Every source scenario and saved answer is unchanged. No new review gate, forced score, automatic semantic relabeling or extra model call is added.

The two shared compatibility helpers have targeted code fixes; they also affect future evaluations using those helpers. Source hashes record this change. Old V4.16 prompt assets and results are not rewritten, and original helper files are backed up before installation. Do not interpret a future replay with changed code hashes as an exact reproduction of the old environment.

The materiality wording does not categorically exempt food, messages or advice: an actual money, deadline, consent, central-cause or institutional premise still receives the applicable tag. The quotation fix removes balanced presentation markers only, preserves original-source character mapping, and does not accept paraphrases, changed pronouns, numbers or negation.

The targeted repair explicitly allows the model to reclassify or withdraw the diagnosed unsupported criticism, while retaining unrelated findings and anchors. It does not force a non-factual criticism into D6, remove genuine arithmetic errors or change how scores are computed. A repeated invalid output remains visibly unscored after the existing bounded repair.

See Advisory_Decisions.md for accepted, narrowed and deferred proposals. Offline checks verify plumbing and evidence handling, not that model judgments have improved. All real model calls remain user-initiated.
