"""Derive V4.5 bookkeeping (V4.2-V4.4 compatible) and downward ceilings, never create a quality judgment."""
from runtime.scoring import deduction, SEVERITY_CAPS


class ConsistencyIssues(ValueError):
    def __init__(self, issues):
        self.issues=issues
        super().__init__('; '.join(i['field']+': '+i['issue'] for i in issues))


def _ids(value):
    return isinstance(value,list) and all(isinstance(v,str) for v in value)


def derive_fields(result,record,contract,notes):
    """Only derive consequences already declared in clauses/impacts. Never raise a score."""
    if contract.get('version') not in ("V4.2", "V4.3", "V4.4", "V4.5") or not isinstance(result,dict) or result.get('status')!='scored':return
    from runtime.strict_scoring import severity_cap
    findings=result.get('checklist_findings')
    issues=result.get('issues')
    dims=result.get('dimensions')
    if not isinstance(findings,dict) or not isinstance(issues,list) or not isinstance(dims,dict):return
    valid_issues=all(isinstance(i,dict) and isinstance(i.get('id'),str) and isinstance(i.get('dimension_impacts'),dict) for i in issues)
    if not valid_issues:return
    by_id={i['id']:i for i in issues}
    if len(by_id)!=len(issues):return
    for cid,parent in findings.items():
        if not isinstance(parent,dict) or not isinstance(parent.get('clauses'),dict):continue
        children=list(parent['clauses'].values())
        if not children or any(not isinstance(c,dict) or c.get('status') not in ('met','unmet') or not _ids(c.get('issue_ids')) for c in children):continue
        failed=[c for c in children if c['status']=='unmet']
        linked=sorted({iid for c in failed for iid in c['issue_ids']})
        if set(linked)-set(by_id):continue
        if 'status' not in parent or (failed and parent['status']=='met'):
            old=parent.get('status');parent['status']='unmet' if failed else 'met'
            notes.append({'type':'parent_status_derived','check':cid,'reported':old,'derived':parent['status']})
        if 'issue_ids' not in parent or (_ids(parent['issue_ids']) and not set(parent['issue_ids'])-set(linked)):
            if parent.get('issue_ids')!=linked:
                notes.append({'type':'parent_issue_links_derived','check':cid,'reported':parent.get('issue_ids'),'derived':linked})
            parent['issue_ids']=linked
        parent.setdefault('evidence',[])
        parent.setdefault('explanation',f'Program summary: {len(failed)} of {len(children)} clauses unmet; see clause findings.')
    for dim,value in dims.items():
        if not isinstance(value,dict):continue
        expected=[i['id'] for i in issues if dim in i['dimension_impacts']]
        stated=value.get('issue_ids')
        # Missing links can be copied from explicit impacts. Extra conflicting links need judgment.
        if stated is None or (_ids(stated) and not set(stated)-set(expected)):
            if stated!=expected:
                notes.append({'type':'dimension_issue_links_derived','dimension':dim,'reported':stated,'derived':expected})
            value['issue_ids']=expected
        anchor=value.get('anchor_score')
        if type(anchor) is not int or not 0<=anchor<=10:continue
        score_supplied='score' in value
        if 'score' not in value:
            value['score']=anchor
            notes.append({'type':'provisional_score_from_anchor','dimension':dim,'anchor_score':anchor})
        reported=value['score']
        if type(reported) is not int or not 0<=reported<=10:continue
        sid=record.get('scenario_id');n=contract['scenario_item_counts'].get(sid)
        prefix={'scenario_1':'E','scenario_2':'L','scenario_3':'C','scenario_4':'A','scenario_5':'S'}.get(sid)
        if n is None or set(findings)!={f'{prefix}{i}' for i in range(1,n+1)}:continue
        if any(not isinstance(f,dict) or f.get('status') not in ('met','unmet') for f in findings.values()):continue
        severities=[];safe=True
        for i in issues:
            if dim not in i['dimension_impacts']:continue
            impact=i['dimension_impacts'][dim]
            if not isinstance(impact,dict) or not isinstance(impact.get('severity'),str) or impact['severity'] not in SEVERITY_CAPS:
                safe=False;break
            severities.append(impact['severity'])
        if not safe:continue
        k=sum(f['status']=='unmet' and contract['id_dimensions'].get(cid)==dim for cid,f in findings.items())
        checklist_cap=10-deduction(n,k);issue_cap=severity_cap(severities)
        final=min(anchor,checklist_cap,issue_cap)
        if reported>final:
            value['score']=final
            notes.append({'type':'program_score_ceiling_applied','dimension':dim,'reported_score':reported,
                          'score_input_source':'model' if score_supplied else 'anchor_default',
                          'anchor_score':anchor,'checklist_cap':checklist_cap,'severity_cap':issue_cap,'final_score':final})


def collect_gaps(result,record,contract,dimensions,matcher,notes):
    """Collect independent incomplete judgments/citations together for one targeted repair."""
    gaps=[]
    def gap(field,issue):gaps.append({'field':field,'issue':issue})
    findings=result.get('checklist_findings',{})
    issues=result.get('issues',[])
    dims=result.get('dimensions',{})
    if not isinstance(findings,dict) or not isinstance(issues,list) or not isinstance(dims,dict):return gaps
    by_id={i['id']:i for i in issues if isinstance(i,dict) and isinstance(i.get('id'),str)}
    for iid,issue in by_id.items():
        impacts=issue.get('dimension_impacts',{})
        if not isinstance(impacts,dict):continue
        ids=issue.get('checklist_ids',[])
        if _ids(ids):
            for cid in ids:
                primary=contract['id_dimensions'].get(cid)
                if primary and primary not in impacts:
                    gap(iid+'.dimension_impacts','Failed check '+cid+' requires an explicit severity and consequence for its primary dimension '+primary+'. Do not guess a severity from the final score.')
    for dim in dimensions:
        value=dims.get(dim)
        if not isinstance(value,dict):continue
        linked=[iid for iid,i in by_id.items() if isinstance(i.get('dimension_impacts'),dict) and dim in i['dimension_impacts']]
        stated=value.get('issue_ids',[])
        if _ids(stated) and set(stated)-set(linked):
            gap(dim+'.issue_ids','Dimension links '+str(sorted(set(stated)-set(linked)))+' conflict with the issue impact map. Supply the actual impact/severity if justified, or return needs_review; do not erase the stated concern or raise the score.')
        score=value.get('score')
        if type(score) is int and score<10 and not linked:
            gap(dim,'Nonmaximum anchor lacks a structured supporting issue. Inspect the existing justification and next_score_barrier; if a real omission/defect supports them, record it with evidence and severity. Do not invent a flaw or raise to ten. Otherwise return needs_review.')
    for rid,f in result.get('claim_findings',{}).items() if isinstance(result.get('claim_findings'),dict) else []:
        if not isinstance(f,dict) or not _ids(f.get('issue_ids')):continue
        kinds={by_id[i].get('kind') for i in f['issue_ids'] if i in by_id and isinstance(by_id[i].get('kind'),str)}
        if f.get('status')=='unsupported' and f['issue_ids'] and 'unsupported_assertion' not in kinds:
            gap(rid,'Unsupported status must link an unsupported_assertion issue; distinguish unsupported from contradicted using current evidence.')
        if f.get('status')=='contradiction' and f['issue_ids'] and not kinds&{'context_contradiction','demonstrable_factual_error'}:
            gap(rid,'Contradiction status must link an actual contradiction/factual error; distinguish unknown from false without reclassifying a real issue merely to pass.')
    # Locate all quote problems before spending the one repair on only the first schema error.
    def quotes(values,label,source):
        if not isinstance(values,list):return
        for index,quote in enumerate(values):
            if not isinstance(quote,str) or not quote.strip():continue
            try:values[index]=matcher(quote,source,f'{label}[{index}]',notes)
            except ValueError:gap(f'{label}[{index}]','Quotation not found in its eligible source; use exact contiguous source wording or explain a genuine omission.')
    for dim,v in dims.items():
        if isinstance(v,dict):quotes(v.get('evidence'),dim+'.evidence',record['response_text'])
    for cid,f in findings.items():
        if not isinstance(f,dict):continue
        quotes(f.get('evidence'),cid+'.evidence',record['response_text'])
        for subid,c in f.get('clauses',{}).items() if isinstance(f.get('clauses'),dict) else []:
            if isinstance(c,dict):quotes(c.get('evidence'),subid+'.evidence',record['response_text'])
    for iid,i in by_id.items():
        quotes(i.get('evidence'),iid+'.evidence',record['response_text'])
        quotes(i.get('scenario_evidence'),iid+'.scenario_evidence',record['user_prompt'])
    for index,flag in enumerate(result.get('reliability_flags',[]) if isinstance(result.get('reliability_flags'),list) else []):
        if isinstance(flag,dict) and isinstance(flag.get('response_excerpt'),str):
            value=[flag['response_excerpt']];quotes(value,f'flag[{index}]',record['response_text']);flag['response_excerpt']=value[0]
    return gaps


def annotate_final_scores(result,notes):
    for note in notes:
        if note.get('type')!='program_score_ceiling_applied':continue
        value=result['dimensions'][note['dimension']]
        explanation=(f"Program finalization: final score {note['final_score']} = min(anchor {note['anchor_score']}, "
                     f"checklist ceiling {note['checklist_cap']}, severity ceiling {note['severity_cap']}). "
                     f"Provisional value {note['reported_score']} (source: {note.get('score_input_source','model')}); this calculation controls the final score.")
        value['justification']+='\n\n'+explanation
        if note['final_score']==min(note['checklist_cap'],note['severity_cap']) and note['final_score']<10:
            value['next_score_barrier']=(f"Program-computed ceiling blocks score {note['final_score']+1}: "
                                         f"checklist ceiling {note['checklist_cap']}, severity ceiling {note['severity_cap']}; "
                                         f"impacting issues: {', '.join(value['issue_ids'])}. "
                                         "The model's original boundary wording is retained in the raw attempt log.")
