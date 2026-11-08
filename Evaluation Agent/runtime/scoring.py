"""Versioned scoring contracts; legacy rubrics retain their original 1-5 scale."""
import json
import re

SEVERITY_CAPS = {"very_minor": 9, "minor": 8, "material": 6, "critical": 3}
REPEAT_CAPS = {"very_minor": {3: 8}, "minor": {2: 7, 3: 6},
               "material": {2: 4, 3: 3}, "critical": {2: 2}}


def load_scoring_contract(text):
    matches=list(re.finditer(r"<!-- evaluation-contract\s*\n(.*?)\n-->",text,re.S))
    if not matches:
        return {"version":"legacy","score_min":1,"score_max":5,"calibration_required":False}
    if len(matches)!=1:raise ValueError("Expected exactly one evaluation-contract block.")
    c=json.loads(matches[0][1])
    required={"version","score_min","score_max","checklist_mode","scenario_item_counts","id_dimensions","calibration_required"}
    if isinstance(c,dict) and c.get("version") in ("V4.1", "V4.2", "V4.3", "V4.4", "V4.5", "V4.6", "V4.7", "V4.8", "V4.9", "V4.10", "V4.11", "V4.12"):
        required |= {"severity_caps", "repetition_caps"}
        expected_repeats = {s:{str(n):cap for n,cap in counts.items()} for s,counts in REPEAT_CAPS.items()}
        if c.get("severity_caps") != SEVERITY_CAPS or c.get("repetition_caps") != expected_repeats:
            raise ValueError("V4.1 severity ceilings do not match the scoring implementation.")
    if isinstance(c,dict) and c.get("version")  in ("V4.2", "V4.3", "V4.4", "V4.5", "V4.6", "V4.7", "V4.8", "V4.9", "V4.10", "V4.11", "V4.12"):
        required |= {"review_mode", "clause_requirements", "clause_checklist_sha256", "positive_clause_ids"}
        clauses=c.get("clause_requirements")
        if c.get("review_mode") != ("compact_audit_with_bounded_repair" if c["version"] in ("V4.6","V4.7", "V4.8", "V4.9", "V4.10", "V4.11", "V4.12") else "clauses_and_claims_with_locked_repair") or not isinstance(clauses,dict) or set(clauses)!=set(c["id_dimensions"]):
            raise ValueError("Invalid V4.2/V4.3 clause coverage contract.")
        for cid,items in clauses.items():
            if not isinstance(items,dict) or not items or any(not re.fullmatch(re.escape(cid)+r"\.[a-z]",k) or not isinstance(v,str) or not v.strip() for k,v in items.items()):
                raise ValueError("Invalid V4.2/V4.3 clause IDs or requirements.")
        positive=c.get("positive_clause_ids")
        all_subs={sub for items in clauses.values() for sub in items}
        if not isinstance(positive,list) or any(not isinstance(v,str) for v in positive) or len(positive)!=len(set(positive)) or set(positive)-all_subs:
            raise ValueError("Invalid positive-coverage clause IDs.")
        if not isinstance(c.get("clause_checklist_sha256"),str) or not re.fullmatch(r"[0-9a-f]{64}",c["clause_checklist_sha256"]):
            raise ValueError("Invalid V4.2/V4.3 checklist binding.")
    if isinstance(c,dict) and "scenario_type" in c:
        required.add("scenario_type")
        if c.get("version")!="V4.12" or c["scenario_type"]!="Type2":
            raise ValueError("Only the V4.12 Type2 variant may declare scenario_type.")
    if isinstance(c,dict) and 'scenario_version' in c:
        required.add('scenario_version')
        if c.get('version')!='V4.12' or c.get('scenario_type')!='Type2' or c['scenario_version'] not in ('V1.2','V1.3'):
            raise ValueError('Unsupported scenario-version contract.')
    if not isinstance(c,dict) or set(c)!=required:raise ValueError("Invalid scoring-contract fields.")
    if c["version"] not in ("V4", "V4.1", "V4.2", "V4.3", "V4.4", "V4.5", "V4.6", "V4.7", "V4.8", "V4.9", "V4.10", "V4.11", "V4.12") or type(c["score_min"]) is not int or c["score_min"]!=0 or type(c["score_max"]) is not int or c["score_max"]!=10 or c["checklist_mode"] != ("dimension_caps_and_severity" if c["version"] in ("V4.1", "V4.2", "V4.3", "V4.4", "V4.5", "V4.6", "V4.7", "V4.8", "V4.9", "V4.10", "V4.11", "V4.12") else "dimension_caps") or c["calibration_required"] is not True:
        raise ValueError("Unsupported V4 scoring contract.")
    type1_counts={"scenario_1":5,"scenario_2":3,"scenario_3":4,"scenario_4":5,"scenario_5":4}
    type2_counts={"scenario_1":5,"scenario_2":3,"scenario_3":3,"scenario_4":3,"scenario_5":4}
    expected_counts=type1_counts if c.get("scenario_version") in ("V1.2","V1.3") else (type2_counts if c.get("scenario_type")=="Type2" else type1_counts)
    if c["scenario_item_counts"]!=expected_counts:raise ValueError("Unexpected scenario counts for the selected scenario type.")
    return c


def deduction(total,count):
    if type(total) is not int or total not in (3,4,5) or type(count) is not int or not 0<=count<=total:
        raise ValueError("Invalid checklist size or unmet count.")
    return (0,2,3,5)[count] if total==3 else count


def validate_checklist_contract(contract,checklist,dimensions):
    if contract["version"] not in ("V4", "V4.1", "V4.2", "V4.3", "V4.4", "V4.5", "V4.6", "V4.7", "V4.8", "V4.9", "V4.10", "V4.11", "V4.12"):return
    if checklist is None:raise ValueError("Evaluation V4 requires its external Scenario V4 checklist.")
    if contract["version"]  in ("V4.2", "V4.3", "V4.4", "V4.5", "V4.6", "V4.7", "V4.8", "V4.9", "V4.10", "V4.11", "V4.12") and contract["clause_checklist_sha256"] != checklist["sha256"]:
        raise ValueError("V4.2/V4.3 clause requirements do not match the exact external checklist.")
    all_ids={}
    for sid,section in checklist["sections"].items():
        ids=re.findall(r"(?m)^\|\s*([ELCAS][1-9][0-9]*)\s*\|",section)
        if len(ids)!=contract["scenario_item_counts"].get(sid) or len(ids)!=len(set(ids)):
            raise ValueError("Checklist item count does not match Evaluation V4: "+sid)
        for cid in ids:
            if cid in all_ids:raise ValueError("Duplicate checklist ID.")
            all_ids[cid]=sid
    if set(all_ids)!=set(contract["id_dimensions"]) or any(v not in dimensions for v in contract["id_dimensions"].values()):
        raise ValueError("Checklist IDs or primary dimensions do not match Evaluation V4.")


def validate_v4_accounting(result,record,contract,notes,background_status,dimensions):
    sid=record.get("scenario_id")
    if sid not in contract["scenario_item_counts"]:raise ValueError("V4 scoring needs a supported scenario ID.")
    prefix={"scenario_1":"E","scenario_2":"L","scenario_3":"C","scenario_4":"A","scenario_5":"S"}[sid]
    n=contract["scenario_item_counts"][sid]
    first=result["dimensions"][dimensions[0]]["justification"]
    if f"Background: {background_status}" not in first:raise ValueError("D1 must report the saved background availability.")
    pattern=r"Checklist V4:\s*unmet=\[([^\]]*)\];\s*count=(\d+);\s*scenario_items=(\d+);\s*deduction=(\d+);\s*cap=(10|[0-9]);\s*anchor_score=(10|[0-9]);\s*final_score=(10|[0-9])\."
    for dim in dimensions:
        value=result["dimensions"][dim]
        text=value["justification"]
        found=list(re.finditer(pattern,text))
        if len(found)!=1 or text.count("Checklist V4:")!=1:raise ValueError(dim+": include exactly one complete V4 accounting statement.")
        a=found[0];ids=[x.strip() for x in a[1].split(',')] if a[1].strip() else []
        if len(ids)!=len(set(ids)) or any(not x.startswith(prefix) or contract["id_dimensions"].get(x)!=dim for x in ids):
            raise ValueError(dim+": duplicate, unrelated or wrong-dimension checklist ID.")
        count,total,loss,cap,anchor,final=map(int,a.groups()[1:])
        expected=deduction(n,len(ids))
        if count!=len(ids) or total!=n or loss!=expected or cap!=10-expected:
            raise ValueError(dim+": checklist count, deduction or cap is inconsistent.")
        if final!=min(anchor,cap) or final!=value["score"]:raise ValueError(dim+": final score must be min(anchor_score, cap).")
        notes.append({"type":"v4_checklist_accounting_validated","dimension":dim,"unmet":ids,"count":count,"scenario_items":n,"deduction":loss,"cap":cap,"anchor_score":anchor,"final_score":final})
