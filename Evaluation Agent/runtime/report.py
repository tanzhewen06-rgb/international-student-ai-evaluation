"""Create readable reports from saved judgments, without model requests."""

import argparse
from html import escape
from runtime import portable_json as json
from pathlib import Path
from runtime.paths import AGENT_ROOT, EVALUATIONS_ROOT, relocated_path, portable_path
import re

from runtime.scoring import load_scoring_contract


DIMENSIONS = (
    ("problem_understanding", "Understanding", "Problem Understanding and Response Relevance"),
    ("empathy_and_emotional_support", "Empathy", "Empathy and Emotional Support"),
    ("cultural_respect_and_autonomy", "Culture and Autonomy", "Cultural Respect and Student Autonomy"),
    ("clarity_and_accessibility", "Clarity", "Clarity and Accessibility"),
    ("reasonableness_and_practicality", "Practicality", "Reasonableness and Practicality of Advice"),
    ("factual_reliability_and_faithfulness", "Reliability", "Factual Reliability and Contextual Faithfulness"),
)


def _json_lines(path):
    if not path.exists():
        return []
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if line.strip():
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {path.name}, line {number}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"Expected an object in {path.name}, line {number}")
            rows.append(row)
    return rows


def _anchors(path):
    """Read anchors from this run's exact saved rubric rather than today's file."""
    text = path.read_text(encoding="utf-8-sig")
    # V3 also numbers its evidence rules; anchor lookup must stay in the score tables.
    dimension_section = re.search(r"(?ms)^## Evaluation Dimensions and Score Anchors\s*\n(.*?)(?=^## |\Z)", text)
    if dimension_section:
        text = dimension_section[1]
    anchors = {}
    for number, (key, _, _) in enumerate(DIMENSIONS, 1):
        section = re.search(rf"(?ms)^### {number}\. .*?(?=^### \d+\.|^## |\Z)", text)
        if section:
            anchors[key] = {
                int(match[0]): match[1].strip()
                for match in re.findall(r"(?m)^\|\s*(10|[0-9])\s*\|\s*(.*?)\s*\|\s*$", section[0])
            }
    return anchors


def _cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def _block(text):
    return "\n".join("> " + line for line in str(text).splitlines())


def _paragraph(text):
    return "<p>" + escape(str(text)).replace("\n", "<br>") + "</p>"


def _audit_details(row, contract):
    if contract["version"] not in ("V4.1", "V4.2", "V4.3", "V4.4", "V4.5"):
        return [], ""
    from runtime.strict_scoring import severity_cap
    from runtime.scoring import deduction
    findings, issues = row["checklist_findings"], row["issues"]
    md = ["### " + contract["version"] + " Checklist Audit", "", "| Check | Result | Linked issues | Evidence and finding |", "| --- | --- | --- | --- |"]
    html = '<h3>' + contract['version'] + ' Checklist Audit</h3>'
    for cid, finding in findings.items():
        text = finding["explanation"]
        evidence = finding["evidence"]
        md.append(f"| {_cell(cid)} | {_cell(finding['status'])} | {_cell(', '.join(finding['issue_ids']))} | {_cell(text + ' ' + ' / '.join(evidence))} |")
        html += '<details><summary>' + escape(cid + ': ' + finding['status']) + '</summary>' + _paragraph(text)
        html += ''.join('<blockquote>' + _paragraph(e) + '</blockquote>' for e in evidence) + '</details>'
    if contract["version"]  in ("V4.2", "V4.3", "V4.4", "V4.5"):
        md += ["", "### Clause Coverage", "", "| Clause | Requirement | Result | Finding |", "| --- | --- | --- | --- |"]
        html += '<h3>Clause Coverage</h3>'
        for cid, finding in findings.items():
            for subid, sub in finding['clauses'].items():
                requirement=contract['clause_requirements'][cid][subid]
                md.append(f"| {_cell(subid)} | {_cell(requirement)} | {_cell(sub['status'])} | {_cell(sub['explanation'])} |")
                html += '<details><summary>' + escape(subid + ': ' + sub['status']) + '</summary>' + _paragraph(requirement) + _paragraph(sub['explanation'])
                html += ''.join('<blockquote>'+_paragraph(q)+'</blockquote>' for q in sub['evidence']) + '</details>'
        md += ["", "### Claim Review", ""]
        html += '<h3>Claim Review</h3>'
        for rid, finding in row['claim_findings'].items():
            span=row.get('claim_review_spans',{}).get(rid,'Source span not recorded.')
            text=rid + ': ' + finding['status'] + ' — ' + finding['explanation']
            md += [text, '', _block(span), '']
            html += '<details><summary>'+escape(text)+'</summary>'+_paragraph(span)+'</details>'
    md += ["", "### Independent Issues and Severity", ""]
    html += '<h3>Independent Issues and Severity</h3>'
    for issue in issues:
        impacts = '; '.join(dim + ': ' + impact['severity'] + ' — ' + impact['explanation'] for dim, impact in issue['dimension_impacts'].items())
        title = issue['id'] + ' / ' + issue['kind'] + ' / ' + ', '.join(issue['checklist_ids']) + (' / materiality: ' + ', '.join(issue.get('materiality',[])) if contract['version'] in ("V4.2", "V4.3", "V4.4", "V4.5") else '')
        md += ['**' + title + '**', '', _block(issue['explanation']), '', _block(impacts), '']
        html += '<p><strong>' + escape(title) + '</strong></p>' + _paragraph(issue['explanation']) + _paragraph(impacts)
        for label, excerpts in (("Candidate", issue['evidence']), ("Saved input", issue['scenario_evidence'])):
            for excerpt in excerpts:
                md += [label + ':', '', _block(excerpt), '']
                html += '<p>' + label + '</p><blockquote>' + _paragraph(excerpt) + '</blockquote>'
    if not issues:
        md += ['No issues recorded.', '']
        html += _paragraph('No issues recorded.')
    md += ['### Score Ceilings', '', '| Dimension | Anchor | Checklist ceiling | Severity ceiling | Final |', '| --- | ---: | ---: | ---: | ---: |']
    html += '<h3>Score Ceilings</h3>'
    n = len(findings)
    for dim, short, _ in DIMENSIONS:
        d = row['dimensions'][dim]
        k = sum(f['status'] == 'unmet' and contract['id_dimensions'][cid] == dim for cid, f in findings.items())
        checklist_cap = 10 - deduction(n, k)
        severities = [i['dimension_impacts'][dim]['severity'] for i in issues if dim in i['dimension_impacts']]
        ceiling = severity_cap(severities)
        if d['score'] != min(d['anchor_score'], checklist_cap, ceiling):
            raise ValueError(dim + ': saved score disagrees with recorded audit.')
        md.append(f"| {short} | {d['anchor_score']} | {checklist_cap} | {ceiling} | {d['score']} |")
        text = f"{short}: min(anchor {d['anchor_score']}, checklist {checklist_cap}, severity {ceiling}) = {d['score']}"
        html += _paragraph(text)
    md += ['', 'Calibration: ' + _cell(row['calibration_note']), '']
    html += '<h3>Calibration</h3>' + _paragraph(row['calibration_note'])
    return md, html


def write_reports(run_dir, destination=None):
    """Write Markdown and standalone HTML reports for one saved evaluation run."""
    run_dir = relocated_path(run_dir).resolve()
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8-sig"))
    if manifest.get('rubric_version')=='V4.12':
        from versions.v4_12.report import write_compact
        return write_compact(run_dir,destination)
    if manifest.get('rubric_version')=='V4.11':
        from versions.v4_11.report import write_compact
        return write_compact(run_dir,destination)
    if manifest.get('rubric_version')=='V4.10':
        from versions.v4_10.report import write_compact
        return write_compact(run_dir,destination)
    if manifest.get('rubric_version')=='V4.9':
        from versions.v4_9.report import write_compact
        return write_compact(run_dir,destination)
    if manifest.get('rubric_version')=='V4.8':
        from versions.v4_8.report import write_compact
        return write_compact(run_dir,destination)
    if manifest.get('rubric_version')=='V4.7':
        from versions.v4_7.report import write_compact
        return write_compact(run_dir,destination)
    if manifest.get('rubric_version')=='V4.6':
        from versions.v4_6.report import write_compact
        return write_compact(run_dir,destination)
    result_path = (run_dir / manifest["result_file"]).resolve()
    if result_path.parent != run_dir:
        raise ValueError("The result file must be inside the selected run folder.")
    rows = _json_lines(result_path)
    review = _json_lines(run_dir / "needs_review.jsonl")
    errors = _json_lines(run_dir / "errors.jsonl")
    anchors = _anchors(run_dir / "rubric.md")
    saved_contract = load_scoring_contract((run_dir / "rubric.md").read_text(encoding="utf-8-sig"))
    scale = manifest.get("score_scale", {"min": saved_contract["score_min"], "max": saved_contract["score_max"]})
    minimum, maximum = scale["min"], scale["max"]
    if scale != {"min": saved_contract["score_min"], "max": saved_contract["score_max"]}:
        raise ValueError("Manifest score scale does not match the saved rubric.")
    selected = manifest["selected_response_ids"]
    by_id = {}
    for row in rows:
        response_id = row["response_id"]
        if row.get("status") != "scored" or response_id in by_id or response_id not in selected:
            raise ValueError("Result IDs or statuses do not match the run manifest.")
        for key, _, _ in DIMENSIONS:
            score = row["dimensions"][key]["score"]
            if type(score) is not int or not minimum <= score <= maximum:
                raise ValueError(f"A dimension score is missing or outside {minimum} to {maximum}.")
        by_id[response_id] = row
    rows = [by_id[response_id] for response_id in selected if response_id in by_id]
    pending = [response_id for response_id in selected if response_id not in by_id]
    judge = manifest["evaluator_model"]
    round_id = manifest["evaluation_round_id"]
    notice = "Excerpts, justifications and improvements retain the judge's original wording. Rubric anchors come from this run's snapshot. The next-score anchor is a comparison aid, not an explicit explanation from the judge of the boundary between scores."
    checklist_file = manifest.get("checklist_file")
    checklist_notice = (
        f"Checklist: {checklist_file}. Each answer received the common guidance and its matching scenario section. "
        "The complete supplement is saved as checklist.md; checkpoint findings appear in the judge's existing rationales and flags."
        if checklist_file else "Checklist: no supplement recorded for this run."
    )
    if manifest.get("checklist_mode") == "integrated":
        checklist_notice = (
            "Checklist V2 is integrated in the saved V3 rubric. Only applicable general and matching scenario items "
            "are to be assessed. Its exact section is saved as checklist.md; the judge's rationales include unmet IDs, "
            "counts, caps, anchor scores, and final scores. Program checks verify the declared arithmetic and ID mappings, "
            "not the substantive completeness or correctness of the judgment."
        )
    if saved_contract["version"] in ("V4.1", "V4.2", "V4.3", "V4.4", "V4.5"):
        checklist_notice = "Evaluation V4.1: every matching check has an explicit finding. Independent issues link to affected dimensions and severity ceilings; final = min(anchor, checklist ceiling, severity ceiling). These checks validate reported evidence and consistency, not whether the judge found every substantive defect."
        notice = "Scores, evidence, strengths and next-score barriers retain the judge's wording. Counts and ceilings are checked by the program; the six dimensions remain independent."
    if saved_contract["version"]  in ("V4.2", "V4.3", "V4.4", "V4.5"):
        checklist_notice = f"Evaluation {saved_contract['version']}: all parent checks and required clauses are audited, alongside selected consequential source passages. Original row-based deductions and severity ceilings apply. Upward score changes or weakened findings during repair require review. Coverage checks do not establish semantic correctness."
        notice += " The calibration note is a fixed program policy, not a model-generated explanation of historical human reasons."
        if manifest.get("score_computation") == "program_minimum_from_anchor_and_audit":
            notice = "Final scores and aggregate links are computed by the program from model anchors and audit findings. Evidence and quality judgments retain the model wording; program notes control any arithmetic disagreement. Original provisional scores and boundary wording remain in raw attempt logs. The calibration note is a fixed program policy."
    reference_notice = (f"Human reference: {manifest['calibration_file']}. The complete Markdown was supplied to every judge request and saved as calibration.md. These historical personal labels are calibration aids, not held-out validation." if manifest.get("calibration_file") else "Human calibration reference: none.")
    if manifest.get('calibration_mode')=='one_short_example_per_scenario':
        reference_notice = (f"Human reference: {manifest['calibration_file']}. Each request receives only one matching short historical example; the compact bank is saved as calibration.md. Scores label the original complete answers, not the excerpts. Explicit human preferences are integrated into the rubric; historical examples are not held-out validation.")
    notice += f" Score scale: {minimum}-{maximum}. " + reference_notice
    status = f"Selected: {len(selected)}; validated judgments saved: {len(rows)}; review records: {len(review)}; error records: {len(errors)}."
    md = ["# Evaluation Report", "", f"Judge: `{judge}`  |  Round: `{round_id}`", "", status, "", checklist_notice, "", notice,
          "", "The six dimensions are reported separately, without a total or average. The HTML report provides collapsible answer and dimension details.", "",
          "## Scores by Dimension", "",
          "| Answer ID | Scenario | Repeat | " + " | ".join(name for _, name, _ in DIMENSIONS) + " |",
          "| --- | --- | ---: | " + " | ".join("---:" for _ in DIMENSIONS) + " |"]
    html_rows, articles = [], []
    for number, row in enumerate(rows, 1):
        response_id = row["response_id"]
        scenario = row.get("source_metadata", {}).get("scenario_name") or row.get("source_metadata", {}).get("scenario_id") or "Not recorded"
        repeat = row.get("source_metadata", {}).get("repeat_index", "—")
        scores = [row["dimensions"][key]["score"] for key, _, _ in DIMENSIONS]
        md.append(f"| {_cell(response_id)} | {_cell(scenario)} | {_cell(repeat)} | " + " | ".join(str(score) for score in scores) + " |")
        html_rows.append(f'<tr><td><a href="#answer-{number}" data-answer="answer-{number}">{escape(response_id)}</a></td>'
                         f'<td>{escape(scenario)}</td><td>{escape(str(repeat))}</td>' + "".join(f'<td><span class="score {'low' if score <= (2 if maximum == 5 else 4) else 'middle' if score <= (3 if maximum == 5 else 6) else 'high'}">{score}</span></td>' for score in scores) + '</tr>')
    for number, row in enumerate(rows, 1):
        response_id = row["response_id"]
        md += ["", f"## Answer {response_id}", ""]
        threshold = 3 if maximum == 5 else 6
        low = [short for key, short, _ in DIMENSIONS if row["dimensions"][key]["score"] <= threshold]
        focus = "Focus on: " + ", ".join(low) if low else f"All dimensions received at least {threshold + 1}/{maximum}."
        repeat_context="Repeat: " + str(row.get("source_metadata",{}).get("repeat_index","—")) + " | Generation run: " + str(row.get("source_metadata",{}).get("run_id","Not recorded"))
        md += [focus, "", repeat_context, ""]
        cards = []
        for key, _, title in DIMENSIONS:
            dimension = row["dimensions"][key]
            score = dimension["score"]
            evidence = dimension["evidence"]
            reason = dimension["justification"]
            current = anchors.get(key, {}).get(score)
            next_anchor = anchors.get(key, {}).get(score + 1)
            md += [f"### {title}: {score}/{maximum}", "", "**Evidence quoted from the answer**", ""]
            if evidence:
                for excerpt in evidence:
                    md += [_block(excerpt), ""]
            else:
                md += ["No excerpt supplied; the justification may identify an omission.", ""]
            if saved_contract["version"] in ("V4.1", "V4.2", "V4.3", "V4.4", "V4.5"):
                detail = "Strengths: " + "; ".join(dimension["strengths"]) + "\nNext-score barrier: " + (dimension["next_score_barrier"] or "None: maximum score.") + "\nLinked issues: " + ", ".join(dimension["issue_ids"])
                reason += "\n\n" + detail
            md += ["**Scoring rationale**", "", _block(reason), ""]
            evidence_html = "".join("<blockquote>" + _paragraph(excerpt) + "</blockquote>" for excerpt in evidence) or _paragraph("No excerpt supplied; the justification may identify an omission.")
            standards_html = ""
            if current:
                md += [f"**Rubric anchor for score {score}**", "", _block(current), ""]
                standards_html += f'<p class="label">Rubric anchor for score {score}</p>' + _paragraph(current)
            if next_anchor:
                md += [f"**Next-score anchor ({score + 1}, for comparison)**", "", _block(next_anchor), ""]
                standards_html += f'<p class="label">Next-score anchor ({score + 1}, for comparison)</p>' + _paragraph(next_anchor)
            cards.append(f'<details class="dimension"><summary><span class="score {'low' if score <= (2 if maximum == 5 else 4) else 'middle' if score <= (3 if maximum == 5 else 6) else 'high'}">{score}/{maximum}</span> {title}</summary>'
                         '<div class="body"><p class="label">Evidence quoted from the answer</p>' + evidence_html +
                         '<p class="label">Scoring rationale</p><div class="reason">' + _paragraph(reason) + '</div>' +
                         '<details class="standards"><summary>Compare rubric anchors</summary>' + standards_html + '</details></div></details>')
        audit_md, audit_html = _audit_details(row, saved_contract)
        md += audit_md
        improvements = row.get("priority_improvements", [])
        md += ["### Priority Improvements", ""]
        md += [f"- {_cell(item)}" for item in improvements] if improvements else ["The judge supplied no improvement priorities."]
        improvements_html = '<ul>' + ''.join('<li>' + escape(item) + '</li>' for item in improvements) + '</ul>' if improvements else _paragraph("The judge supplied no improvement priorities.")
        flags = row.get("reliability_flags", [])
        md += ["", "### Reliability Flags", ""]
        flags_html = ""
        for flag in flags:
            md += [f"- Type: `{flag['type']}`", "", _block(flag["response_excerpt"]), "", _block(flag["explanation"]), ""]
            flags_html += '<p><code>' + escape(flag["type"]) + '</code></p><blockquote>' + _paragraph(flag["response_excerpt"]) + '</blockquote>' + _paragraph(flag["explanation"])
        if not flags:
            md += ["The judge recorded no reliability concerns. This does not establish that external facts were verified.", ""]
            flags_html = _paragraph("The judge recorded no reliability concerns. This does not establish that external facts were verified.")
        md += [f"External verification status: `{row.get('verification_status', 'Not recorded')}`.", ""]
        articles.append(f'<details class="answer" id="answer-{number}"><summary><strong>{escape(response_id)}</strong>'
                        f'<span class="focus">{escape(focus)}</span></summary><div class="body">' + _paragraph(repeat_context) + ''.join(cards) +
                        audit_html + '<h3>Priority Improvements</h3>' + improvements_html + '<h3>Reliability Flags</h3>' + flags_html +
                        '<p class="muted">External verification status: ' + escape(row.get("verification_status", "Not recorded")) + '</p></div></details>')
    md += ["", "## Sources and Run Completeness", "", f"- Raw result file: `{result_path.name}`",
           f"- Raw result path: `{result_path}`", "- Scoring standard: this run's `rubric.md` snapshot.",
           "- This report organizes saved final judgments, omits duplicated raw output and retry logs, and makes no model requests."]
    if review:
        md += ["", "## Judgments Requiring Review", ""]
        for item in review:
            reason=item.get('reason','Unresolved evidence; inspect needs_review.jsonl.')
            md += ["- " + _cell(item['response_id']) + ": " + _cell(reason)]
    if pending:
        md += ["- Answers without a validated final judgment: " + ", ".join(f"`{item}`" for item in pending) + "."]
    if review or errors:
        md += ["- Check this run's `needs_review.jsonl` or `errors.jsonl` for unresolved items; these are excluded from the score table."]
    html = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Evaluation Report</title><style>
:root{font-family:system-ui,"Segoe UI",sans-serif;color:#172b3a;background:#f3f6fa;line-height:1.65}
body{max-width:1120px;margin:auto;padding:32px 24px 72px}h1{font-size:32px;margin-bottom:4px}h2{margin-top:30px}h3{font-size:17px}
.muted,.focus{color:#526375}.intro{background:white;border:1px solid #dce4ed;border-radius:14px;padding:18px 22px}
.table-wrap{overflow:auto;background:white;border:1px solid #dce4ed;border-radius:14px}table{border-collapse:collapse;width:100%;white-space:nowrap}
th,td{padding:13px 14px;text-align:center;border-bottom:1px solid #e8edf3}th{font-size:13px;color:#536577;background:#f8fafc}td:first-child,td:nth-child(2){text-align:left}
a{color:#1466a7}.score{font-size:14px;font-weight:750;display:inline-block;min-width:30px;padding:2px 8px;border-radius:8px;color:#253954;background:#e6edf6}
.low{background:#fbe3de;color:#9c3023}.middle{background:#fff0c8;color:#7e5800}.high{background:#e1f0eb;color:#236249}
.answer{margin-top:16px;border:1px solid #dce4ed;background:white;border-radius:12px;scroll-margin-top:20px}.answer>summary{padding:18px 20px}
summary{cursor:pointer}.focus{font-size:13px;margin-left:20px;white-space:normal;display:inline-block}.body{padding:0 20px 20px}
.dimension{border-top:1px solid #e4eaf0}.dimension>summary{padding:14px 0;font-weight:650}.dimension .body{padding:0 4px 18px}
.label{font-size:13px;font-weight:750;color:#526375;margin-bottom:7px}blockquote{margin:8px 0 16px;border-left:3px solid #b3c2d2;padding:1px 16px;background:#f8fafc}
.reason{border-radius:8px;background:#edf4fc;padding:1px 16px}.standards{background:#f8fafc;border-radius:8px;padding:10px 14px;margin-top:16px;font-size:14px}
.standards summary{color:#526375}code{overflow-wrap:anywhere}footer{margin-top:32px;color:#526375;font-size:13px;overflow-wrap:anywhere}
@media(max-width:650px){body{padding:18px 12px}.focus{display:block;margin:8px 0 0}.body{padding:0 14px 16px}}
</style></head><body>'''
    html += '<h1>Evaluation Report</h1><p class="muted">Judge: ' + escape(judge) + ' · Six dimensions reported separately</p>'
    html += '<div class="intro">' + _paragraph(status) + _paragraph(checklist_notice) + _paragraph(notice) + _paragraph("Click an answer ID in the table to expand that answer. Open a dimension to inspect its score, excerpts and justification. Select Compare rubric anchors to see the current and next-score requirements.") + '</div>'
    html += '<h2>Scores by Dimension</h2><div class="table-wrap"><table><thead><tr><th>Answer ID</th><th>Scenario</th><th>Repeat</th>' + ''.join('<th>' + name + '</th>' for _, name, _ in DIMENSIONS) + '</tr></thead><tbody>' + ''.join(html_rows) + '</tbody></table></div>'
    html += ''.join(articles)
    if review:
        html += '<h2>Judgments Requiring Review</h2>'
        for item in review:
            html += _paragraph(item['response_id'] + ': ' + item.get('reason','Unresolved evidence; inspect needs_review.jsonl.'))
    if pending:
        html += _paragraph("Answers without a validated final judgment: " + ", ".join(pending))
    html += '<footer>This report calculates no total or average and makes no model requests.<br>Round: ' + escape(round_id) + '<br>Raw results: ' + escape(str(portable_path(result_path))) + '</footer>'
    html += '''<script>document.querySelectorAll('[data-answer]').forEach(link=>link.addEventListener('click',()=>{const answer=document.getElementById(link.dataset.answer);answer.open=true;}));</script></body></html>'''
    destination = Path(destination).resolve() if destination else run_dir
    destination.mkdir(parents=True, exist_ok=True)
    markdown_path = destination / "report.md"
    html_path = destination / "report.html"
    markdown_path.write_text("\n".join(md).rstrip() + "\n", encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")
    return markdown_path, html_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", nargs="?", help="Run folder; omit to use the newest manifest.")
    args = parser.parse_args()
    if args.run_dir:
        run_dir = Path(args.run_dir)
    else:
        candidates = list(EVALUATIONS_ROOT.rglob("manifest.json"))
        if not candidates:
            raise SystemExit("No saved evaluation runs were found.")
        run_dir = max(candidates, key=lambda path: path.stat().st_mtime_ns).parent
    for path in write_reports(run_dir):
        print(f"Readable report: {path}")


if __name__ == "__main__":
    main()
