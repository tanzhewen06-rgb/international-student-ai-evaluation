"""V4.1 audit consistency and score ceilings; no semantic truth claims or API calls."""
import re
from collections import Counter

from runtime.scoring import deduction, SEVERITY_CAPS, REPEAT_CAPS

RELIABILITY_KINDS = {"context_contradiction", "demonstrable_factual_error", "unsupported_assertion"}
ISSUE_KINDS = RELIABILITY_KINDS | {"omission", "clarity", "empathy", "autonomy", "practicality"}


def severity_cap(severities):
    counts = Counter(severities)
    if set(counts) - set(SEVERITY_CAPS):
        raise ValueError("Unknown issue severity.")
    cap = min([10] + [SEVERITY_CAPS[s] for s in counts])
    for severity, thresholds in REPEAT_CAPS.items():
        for count, ceiling in thresholds.items():
            if counts[severity] >= count:
                cap = min(cap, ceiling)
    return cap


def _keys(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(label + ": incorrect fields.")


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + ": nonempty text required.")


def _ids(value, allowed, label):
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        raise ValueError(label + ": expected an array of IDs.")
    if len(value) != len(set(value)) or set(value) - set(allowed):
        raise ValueError(label + ": duplicate or unknown IDs.")


def validate_audit(result, record, contract, dimensions, background_status, matcher, notes):
    """Validate reported findings. Returns ungrounded quotation diagnostics for review."""
    extension_issues=[]
    if contract["version"]  in ("V4.2", "V4.3", "V4.4", "V4.5"):
        if contract["version"] in ("V4.3", "V4.4", "V4.5"):
            from versions.v4_3.audit import validate_extension
        else:
            from versions.v4_2.audit import validate_extension
        result, extension_issues=validate_extension(result,record,contract,matcher,notes)
    _keys(result, ("status", "response_id", "dimensions", "checklist_findings", "issues",
                   "reliability_flags", "verification_status", "priority_improvements", "calibration_note"), "V4.1 result")
    if result["status"] != "scored" or result["verification_status"] != "not_externally_verified":
        raise ValueError("V4.1 requires scored and not_externally_verified.")
    _text(result["calibration_note"], "calibration_note")
    sid = record.get("scenario_id")
    prefix = {"scenario_1": "E", "scenario_2": "L", "scenario_3": "C", "scenario_4": "A", "scenario_5": "S"}.get(sid)
    if prefix is None:
        raise ValueError("V4.1 requires a supported, bound Scenario V4 record.")
    n = contract["scenario_item_counts"][sid]
    check_ids = {f"{prefix}{i}" for i in range(1, n + 1)}
    _keys(result["checklist_findings"], check_ids, "checklist_findings")
    _keys(result["dimensions"], dimensions, "dimensions")
    evidence_issues = list(extension_issues)

    def quotes(value, field, source, maximum=2):
        if not isinstance(value, list) or len(value) > maximum:
            raise ValueError(field + ": expected zero to two short excerpts.")
        for index, excerpt in enumerate(value):
            label = f"{field}[{index}]"
            _text(excerpt, label)
            try:
                value[index] = matcher(excerpt, source, label, notes)
            except ValueError:
                evidence_issues.append({"field": label, "judge_excerpt": excerpt,
                                        "issue": "quotation_not_found_in_eligible_source"})

    issues = result["issues"]
    if not isinstance(issues, list):
        raise ValueError("issues must be an array.")
    by_id, fingerprints = {}, set()
    for issue in issues:
        _keys(issue, ("id", "kind", "checklist_ids", "evidence", "scenario_evidence", "explanation", "dimension_impacts"), "issue")
        iid = issue["id"]
        if not isinstance(iid, str) or not re.fullmatch(r"I[1-9][0-9]*", iid) or iid in by_id:
            raise ValueError("Each issue needs a unique I-number.")
        if not isinstance(issue["kind"], str) or issue["kind"] not in ISSUE_KINDS:
            raise ValueError("Unknown issue kind.")
        _text(issue["explanation"], iid + ".explanation")
        _ids(issue["checklist_ids"], check_ids, iid + ".checklist_ids")
        quotes(issue["evidence"], iid + ".evidence", record["response_text"])
        quotes(issue["scenario_evidence"], iid + ".scenario_evidence", record["user_prompt"])
        if issue["kind"] != "omission" and not issue["evidence"]:
            raise ValueError(iid + ": a claimed defect in wording requires candidate evidence.")
        if issue["kind"] == "context_contradiction" and not issue["scenario_evidence"]:
            raise ValueError(iid + ": a contextual contradiction needs the conflicting saved-input excerpt.")
        impacts = issue["dimension_impacts"]
        if not isinstance(impacts, dict) or not impacts or set(impacts) - set(dimensions):
            raise ValueError(iid + ": specify only actually affected dimensions.")
        for dim, impact in impacts.items():
            _keys(impact, ("severity", "explanation"), iid + ".impact")
            if not isinstance(impact["severity"], str) or impact["severity"] not in SEVERITY_CAPS:
                raise ValueError(iid + ": unknown severity.")
            _text(impact["explanation"], iid + ".impact.explanation")
        for cid in issue["checklist_ids"]:
            if contract["id_dimensions"][cid] not in impacts:
                raise ValueError(iid + ": failed check must affect its primary dimension.")
        reliability = dimensions[5]
        if issue["kind"] in RELIABILITY_KINDS:
            if reliability not in impacts or SEVERITY_CAPS[impacts[reliability]["severity"]] > 8:
                raise ValueError(iid + ": factual errors/unsupported assertions need at least minor D6 impact.")
        fingerprint = (issue["kind"], tuple(issue["evidence"]), issue["explanation"].strip().casefold())
        if fingerprint in fingerprints:
            raise ValueError("Duplicate issue: merge repeated descriptions before counting severity.")
        fingerprints.add(fingerprint)
        by_id[iid] = issue

    for cid, finding in result["checklist_findings"].items():
        _keys(finding, ("status", "evidence", "explanation", "issue_ids"), cid)
        if finding["status"] not in ("met", "unmet"):
            raise ValueError(cid + ": status must be met or unmet.")
        _text(finding["explanation"], cid + ".explanation")
        quotes(finding["evidence"], cid + ".evidence", record["response_text"])
        _ids(finding["issue_ids"], by_id, cid + ".issue_ids")
        linked = {iid for iid, issue in by_id.items() if cid in issue["checklist_ids"]}
        if linked != set(finding["issue_ids"]):
            raise ValueError(cid + ": issue/check links must agree in both directions.")
        if (finding["status"] == "unmet") != bool(linked):
            raise ValueError(cid + ": unmet requires a documented issue; met cannot link a failure.")
        # A negative constraint can be met by restraint; no fabricated excerpt is required.

    first = result["dimensions"][dimensions[0]]
    if not isinstance(first, dict) or f"Background: {background_status}" not in first.get("justification", ""):
        raise ValueError("D1 must state the saved background availability.")
    for dim in dimensions:
        value = result["dimensions"][dim]
        _keys(value, ("evidence", "justification", "score", "anchor_score", "strengths", "next_score_barrier", "issue_ids"), dim)
        _text(value["justification"], dim + ".justification")
        for field in ("score", "anchor_score"):
            if type(value[field]) is not int or not 0 <= value[field] <= 10:
                raise ValueError(dim + "." + field + ": integer 0-10 required.")
        quotes(value["evidence"], dim + ".evidence", record["response_text"])
        if not isinstance(value["strengths"], list) or len(value["strengths"]) > 2:
            raise ValueError(dim + ": strengths must contain zero to two specific observations.")
        for strength in value["strengths"]:
            _text(strength, dim + ".strengths")
        _ids(value["issue_ids"], by_id, dim + ".issue_ids")
        linked = {iid for iid, issue in by_id.items() if dim in issue["dimension_impacts"]}
        if set(value["issue_ids"]) != linked:
            raise ValueError(dim + ": all and only relevant issues must affect this score.")
        unmet = sorted(cid for cid, f in result["checklist_findings"].items()
                       if f["status"] == "unmet" and contract["id_dimensions"][cid] == dim)
        loss = deduction(n, len(unmet))
        severities = [by_id[iid]["dimension_impacts"][dim]["severity"] for iid in linked]
        ceiling = severity_cap(severities)
        expected = min(value["anchor_score"], 10 - loss, ceiling)
        if value["score"] != expected:
            raise ValueError(f"{dim}: score must be min(anchor={value['anchor_score']}, checklist_cap={10-loss}, severity_cap={ceiling})={expected}.")
        if value["score"] < 10:
            _text(value["next_score_barrier"], dim + ".next_score_barrier")
            if not linked:
                raise ValueError(dim + ": a nonmaximum score needs a supported limitation, not praise alone.")
        elif linked or value["next_score_barrier"] is not None:
            raise ValueError(dim + ": ten requires no identified limitation and a null barrier.")
        if value["score"] >= 9 and (not value["strengths"] or not value["evidence"]):
            raise ValueError(dim + ": 9/10 requires specific positive evidence.")
        notes.append({"type": "v45_score_accounting_validated" if contract["version"] == "V4.5" else "v44_score_accounting_validated" if contract["version"] == "V4.4" else "v43_score_accounting_validated" if contract["version"] == "V4.3" else "v42_score_accounting_validated" if contract["version"] == "V4.2" else "v41_score_accounting_validated", "dimension": dim,
                      "unmet": unmet, "count": len(unmet), "scenario_items": n, "deduction": loss,
                      "checklist_cap": 10-loss, "severity_cap": ceiling, "severity_counts": dict(Counter(severities)),
                      "anchor_score": value["anchor_score"], "final_score": expected})

    flags = result["reliability_flags"]
    if not isinstance(flags, list):
        raise ValueError("reliability_flags must be an array.")
    flagged = set()
    for flag in flags:
        _keys(flag, ("type", "response_excerpt", "explanation", "issue_id"), "reliability flag")
        if flag["type"] not in RELIABILITY_KINDS | {"external_claim_requires_verification"}:
            raise ValueError("Unknown reliability flag type.")
        _text(flag["explanation"], "flag.explanation")
        excerpts = [flag["response_excerpt"]]
        quotes(excerpts, "flag.response_excerpt", record["response_text"])
        flag["response_excerpt"] = excerpts[0]
        iid = flag["issue_id"]
        if flag["type"] == "external_claim_requires_verification":
            if iid is not None:
                raise ValueError("Verification-only flags use issue_id=null; record any actual overclaim separately.")
        else:
            if not isinstance(iid, str) or iid not in by_id or by_id[iid]["kind"] != flag["type"]:
                raise ValueError("Reliability defect flags must link a matching scored issue.")
            if iid in flagged:
                raise ValueError("Do not repeat the same reliability defect flag.")
            flagged.add(iid)
    if flagged != {iid for iid, issue in by_id.items() if issue["kind"] in RELIABILITY_KINDS}:
        raise ValueError("Each factual/unsupported issue needs its matching reliability flag.")
    improvements = result["priority_improvements"]
    if not isinstance(improvements, list) or len(improvements) > 2:
        raise ValueError("priority_improvements must contain zero to two strings.")
    for item in improvements:
        _text(item, "priority improvement")
    if issues and not improvements:
        raise ValueError("Identified faults require at least one concrete priority improvement.")
    return evidence_issues
