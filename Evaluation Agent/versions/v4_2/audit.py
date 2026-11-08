"""Clause coverage, claim-review inventory and conservative repair guards for V4.2."""
import re
import json

CALIBRATION_POLICY = (
    "Historical examples are reference only. Current saved facts and V4.2 rules take precedence. "
    "The program does not attribute reasons to human scores when comments are absent."
)
MATERIALITY = {"money_or_deadline", "permission_or_consent", "central_cause_or_motive", "institutional_rule_or_outcome"}
FACTUAL_KINDS = {"context_contradiction", "demonstrable_factual_error", "unsupported_assertion"}
_RISK = re.compile(
    r"\d|^\s*>|\b(?:illegal|visa|permission|authorization|grade|grading|mark|deadline|drop|late|always|never|"
    r"guarantee|funds|costs?|payment|transfer|shortfall|you|your|will|must|cannot|should|they|housemates?|teammates?|people|local|culture|because|assum\w*|"
    r"likely|probably|means?|meant|homesick|tired|fatigue|budget)\b|back home|you (?:mentioned|said|are)|"
    r"you['’]re|I['’]m|I (?:can|will|need)|do(?:n['’]t| not)|free.for.all", re.I)


def claim_review_spans(candidate):
    """Select potentially consequential passages for review, never label them erroneous."""
    spans = {}
    for line in candidate.splitlines():
        line = line.strip()
        if len(line) < 24 or line.startswith('#') or not _RISK.search(line):
            continue
        # Preserve complete source wording; even long passages remain data, not instructions.
        spans[f"R{len(spans)+1}"] = line
    return spans


def _keys(value, keys, field):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(field + ': incorrect fields.')


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field + ': nonempty explanation required.')


def _ids(value, allowed, field):
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        raise ValueError(field + ': expected an ID array.')
    if len(value) != len(set(value)) or set(value)-set(allowed):
        raise ValueError(field + ': duplicate or unknown IDs.')


def validate_extension(result, record, contract, matcher, notes):
    """Return a V4.1-compatible view plus quote issues; retain detailed audit in result."""
    _keys(result, ('status', 'response_id', 'dimensions', 'checklist_findings', 'issues',
                   'claim_findings', 'reliability_flags', 'verification_status', 'priority_improvements'), 'V4.2 result')
    issues = result['issues']
    if not isinstance(issues, list):
        raise ValueError('issues must be an array.')
    issue_map = {}
    d6 = 'factual_reliability_and_faithfulness'
    expected_issue_fields = {'id','kind','checklist_ids','evidence','scenario_evidence','explanation','dimension_impacts','materiality'}
    for issue in issues:
        _keys(issue, expected_issue_fields, 'V4.2 issue')
        if not isinstance(issue['id'], str) or issue['id'] in issue_map:
            raise ValueError('Each issue needs a unique ID.')
        issue_map[issue['id']] = issue
        _ids(issue['materiality'], MATERIALITY, issue['id']+'.materiality')
        impacts = issue['dimension_impacts']
        if not isinstance(impacts, dict):
            raise ValueError('dimension_impacts must be an object.')
        if d6 in impacts:
            severity = impacts[d6].get('severity') if isinstance(impacts[d6],dict) else None
            if issue['kind'] not in FACTUAL_KINDS:
                if issue['kind'] != 'clarity' or severity != 'very_minor' or issue['materiality']:
                    raise ValueError('A factual defect cannot be downgraded to a practicality/empathy label in D6.')
            if issue['kind'] in FACTUAL_KINDS and issue['materiality'] and severity not in ('material','critical'):
                raise ValueError('A consequential factual issue requires at least material D6 severity.')
        elif issue['kind'] in FACTUAL_KINDS:
            raise ValueError('Factual issues must affect D6.')

    quotation_issues = []
    def quotes(values, label):
        if not isinstance(values,list) or len(values)>2:
            raise ValueError(label+': zero to two excerpts required.')
        for i,quote in enumerate(values):
            _text(quote,label)
            try:
                values[i]=matcher(quote,record['response_text'],f'{label}[{i}]',notes)
            except ValueError:
                quotation_issues.append({'field':f'{label}[{i}]','judge_excerpt':quote,'issue':'quotation_not_found_in_candidate'})

    findings=result['checklist_findings']
    if not isinstance(findings,dict):
        raise ValueError('checklist_findings must be an object.')
    base_findings={}
    for cid, finding in findings.items():
        _keys(finding,('status','evidence','explanation','issue_ids','clauses'),cid)
        if cid not in contract['clause_requirements']:
            raise ValueError('Unknown current checklist ID: '+cid)
        clauses=finding['clauses']
        _keys(clauses, contract['clause_requirements'][cid], cid+'.clauses')
        failed=set()
        for subid,sub in clauses.items():
            _keys(sub,('status','evidence','explanation','issue_ids'),subid)
            if sub['status'] not in ('met','unmet'):
                raise ValueError(subid+': use met/unmet; no NA bypass.')
            _text(sub['explanation'],subid)
            quotes(sub['evidence'],subid+'.evidence')
            if sub['status']=='met' and subid in contract['positive_clause_ids'] and not sub['evidence']:
                raise ValueError(subid+': positive coverage needs a candidate excerpt.')
            _ids(sub['issue_ids'],issue_map,subid)
            if (sub['status']=='unmet') != bool(sub['issue_ids']):
                raise ValueError(subid+': an unmet clause requires an issue; a met clause cannot link a defect.')
            for iid in sub['issue_ids']:
                if cid not in issue_map[iid]['checklist_ids']:
                    raise ValueError(subid+': issue must link back to its parent check.')
            failed.update(sub['issue_ids'])
        if finding['status'] != ('unmet' if failed else 'met'):
            raise ValueError(cid+': parent cannot be met when any required clause is unmet.')
        _ids(finding['issue_ids'],issue_map,cid)
        if set(finding['issue_ids'])!=failed:
            raise ValueError(cid+': parent issue IDs must equal its failed-clause issue union.')
        base_findings[cid]={k:v for k,v in finding.items() if k!='clauses'}

    spans=claim_review_spans(record['response_text'])
    _keys(result['claim_findings'],spans,'claim_findings')
    for rid,finding in result['claim_findings'].items():
        _keys(finding,('status','explanation','issue_ids'),rid)
        _text(finding['explanation'],rid)
        _ids(finding['issue_ids'],issue_map,rid)
        status=finding['status']
        if status not in ('supported','qualified','unsupported','contradiction','not_a_claim'):
            raise ValueError(rid+': unknown claim status.')
        if (status in ('unsupported','contradiction')) != bool(finding['issue_ids']):
            raise ValueError(rid+': actual unsupported/contradictory claims require scored issues.')
        required = {'unsupported_assertion'} if status=='unsupported' else {'context_contradiction','demonstrable_factual_error'}
        if finding['issue_ids'] and not any(issue_map[i]['kind'] in required for i in finding['issue_ids']):
            raise ValueError(rid+': do not relabel a factual defect as mere practicality or clarity.')
    result['calibration_note']=CALIBRATION_POLICY  # Program provenance, never an invented human rationale.
    base={k:v for k,v in result.items() if k!='claim_findings'}
    base['checklist_findings']=base_findings
    base['issues']=[{k:v for k,v in i.items() if k!='materiality'} for i in issues]
    notes.append({'type':'v42_clause_and_claim_coverage_validated','clauses':sum(len(f['clauses']) for f in findings.values()),
                  'review_spans':len(spans),'limitation':'Coverage and consistency checks do not establish semantic correctness.'})
    return base, quotation_issues


def repair_regressions(previous, current, dimensions):
    """Flag score inflation, issue disappearance and severity reductions for human review."""
    if not isinstance(previous,dict) or previous.get('status')!='scored':
        return []
    changes=[]
    previous_dims=previous.get('dimensions',{})
    if not isinstance(previous_dims,dict):previous_dims={}
    for dim in dimensions:
        before=previous_dims.get(dim,{})
        after=current.get('dimensions',{}).get(dim,{})
        if not isinstance(before,dict) or not isinstance(after,dict):
            continue
        for field in ('score','anchor_score'):
            a,b=before.get(field),after.get(field)
            if type(a) is int and type(b) is int and 0<=a<=10 and b>a:
                changes.append({'field':dim+'.'+field,'issue':'score_increased_during_repair','before':a,'after':b})
    old=previous.get('issues',[]);new=current.get('issues',[])
    if not isinstance(old,list) or not isinstance(new,list):
        return changes
    newmap={i['id']:i for i in new if isinstance(i,dict) and isinstance(i.get('id'),str)}
    rank={'very_minor':0,'minor':1,'material':2,'critical':3}
    for issue in old:
        if not isinstance(issue,dict) or not isinstance(issue.get('id'),str):
            continue
        iid=issue['id'];other=newmap.get(iid)
        if other is None:
            changes.append({'field':iid,'issue':'prior_issue_removed_during_repair'})
            continue
        if issue.get('kind')!=other.get('kind'):
            changes.append({'field':iid,'issue':'prior_issue_kind_changed_during_repair'})
        for field in ('checklist_ids','materiality'):
            prior_values=issue.get(field,[])
            new_values=other.get(field,[])
            if isinstance(prior_values,list) and all(isinstance(v,str) for v in prior_values) and set(prior_values)-set(new_values):
                changes.append({'field':iid+'.'+field,'issue':'prior_links_or_materiality_removed'})
        impacts=issue.get('dimension_impacts',{})
        if not isinstance(impacts,dict):continue
        for dim,impact in impacts.items():
            if not isinstance(impact,dict):continue
            old_severity=impact.get('severity')
            prior=rank.get(old_severity) if isinstance(old_severity,str) else None
            now=rank.get(other.get('dimension_impacts',{}).get(dim,{}).get('severity'))
            if prior is not None and (now is None or now<prior):
                changes.append({'field':iid+'.'+dim,'issue':'prior_impact_removed_or_severity_reduced'})
    oldchecks=previous.get('checklist_findings',{})
    if isinstance(oldchecks,dict):
        for cid,f in oldchecks.items():
            if isinstance(f,dict) and f.get('status')=='unmet' and current.get('checklist_findings',{}).get(cid,{}).get('status')=='met':
                changes.append({'field':cid,'issue':'unmet_check_changed_to_met_during_repair'})
            if isinstance(f,dict) and isinstance(f.get('clauses'),dict):
                for subid,sub in f['clauses'].items():
                    after=current.get('checklist_findings',{}).get(cid,{}).get('clauses',{}).get(subid,{})
                    if isinstance(sub,dict) and sub.get('status')=='unmet' and after.get('status')=='met':
                        changes.append({'field':subid,'issue':'unmet_clause_changed_to_met_during_repair'})
    return changes


def prepare_audit_instructions(instructions,record,contract):
    """Send only current-case clause guidance; retain the complete rubric as the run snapshot."""
    if contract["version"] != "V4.2":
        return instructions
    prefix={"scenario_1":"E","scenario_2":"L","scenario_3":"C","scenario_4":"A","scenario_5":"S"}[record["scenario_id"]]
    clauses={cid:v for cid,v in contract["clause_requirements"].items() if cid.startswith(prefix)}
    payload={"version":"V4.2","scenario_id":record["scenario_id"],
             "scenario_item_count":contract["scenario_item_counts"][record["scenario_id"]],
             "id_dimensions":{cid:contract["id_dimensions"][cid] for cid in clauses},
             "clause_requirements":clauses,
             "positive_clause_ids":[s for s in contract["positive_clause_ids"] if s.split('.')[0] in clauses]}
    body,count=re.subn(r"<!-- evaluation-contract\s*\n.*?\n-->","",instructions,count=1,flags=re.S)
    if count!=1:raise ValueError("Missing full rubric contract before case-specific preparation.")
    return body+"\n\n## Current Scenario Audit Requirements\nOnly the following parent IDs and clauses apply.\n"+json.dumps(payload,ensure_ascii=False,indent=2)+"\n"
