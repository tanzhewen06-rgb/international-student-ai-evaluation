"""Compact V4.7 judgments: exact evidence, deterministic ceilings, bounded repair."""
import copy
import json
import time
from runtime.scoring import deduction, SEVERITY_CAPS
from runtime.strict_scoring import severity_cap

DIMENSIONS=('problem_understanding','empathy_and_emotional_support','cultural_respect_and_autonomy',
            'clarity_and_accessibility','reasonableness_and_practicality','factual_reliability_and_faithfulness')
SHORT={f'D{i}':d for i,d in enumerate(DIMENSIONS,1)}
ALIASES={**{d:d for d in DIMENSIONS},**SHORT,
         'cultural_respect_and_student_autonomy':DIMENSIONS[2],
         'reasonableness_and_practicality_of_advice':DIMENSIONS[4]}
KINDS={'context_contradiction','demonstrable_factual_error','unsupported_assertion','omission','clarity','empathy','autonomy','practicality'}
FACTUAL={'context_contradiction','demonstrable_factual_error','unsupported_assertion'}
TAGS={'money_or_deadline','permission_or_consent','central_cause_or_motive','institutional_rule_or_outcome'}

def _keys(obj,expected,label):
    if not isinstance(obj,dict) or set(obj)!=set(expected):raise ValueError(label+': incorrect fields.')

def _text(value,label):
    if not isinstance(value,str) or not value.strip():raise ValueError(label+': nonempty text required.')
    return value.strip()

def normalize_dimensions(values,notes,label):
    if not isinstance(values,dict):raise ValueError(label+': expected object.')
    out={}
    for key,value in values.items():
        target=ALIASES.get(key)
        if target is None:raise ValueError(label+': unknown dimension '+str(key))
        if target in out:raise ValueError(label+': ambiguous duplicate dimension.')
        if key!=target:notes.append({'type':'dimension_name_normalized','field':label,'from':key,'to':target})
        out[target]=value
    return out

def validate_compact_result(value,record,contract,matcher,notes):
    value=copy.deepcopy(value)
    if value.get('status')=='needs_review':
        _keys(value,('status','response_id','reason'),'needs_review')
        _text(value['reason'],'reason');return value
    _keys(value,('status','response_id','dimensions','checks','issues'),'compact result')
    if value['status']!='scored' or value['response_id']!=record['response_id']:raise ValueError('Wrong status or response ID.')
    dims=normalize_dimensions(value['dimensions'],notes,'dimensions');_keys(dims,DIMENSIONS,'dimensions')
    prefix={'scenario_1':'E','scenario_2':'L','scenario_3':'C','scenario_4':'A','scenario_5':'S'}[record['scenario_id']]
    required={cid:sub for cid,sub in contract['clause_requirements'].items() if cid.startswith(prefix)}
    statuses=value['checks'];_keys(statuses,[sid for sub in required.values() for sid in sub],'checks')
    for key,status in statuses.items():
        if type(status) is not bool:raise ValueError(key+': expected true/false.')
    quality_flags=[]
    # Accept exact clause-to-parent mappings, preserving unique parent deduction units.
    for issue in value.get('issues',[]):
        if not isinstance(issue,dict):continue
        ids=issue.get('checks')
        if isinstance(ids,list):
            mapped=[]
            for cid in ids:
                parent=cid.split('.',1)[0] if isinstance(cid,str) and cid in statuses else cid
                if parent not in mapped:mapped.append(parent)
            if mapped!=ids:
                notes.append({'type':'clause_issue_links_normalized','issue':issue.get('id'),'before':ids,'after':mapped})
                issue['checks']=mapped
        impacts=issue.get('impacts')
        if not isinstance(impacts,dict):continue
        normalized_impacts=normalize_dimensions(impacts,notes,str(issue.get('id'))+'.impacts')
        d6=DIMENSIONS[5]
        severity=normalized_impacts.get(d6)
        rank={'very_minor':0,'minor':1,'material':2,'critical':3}
        minimum='material' if issue.get('materiality') and issue.get('kind') in FACTUAL|{'omission'} else 'minor' if issue.get('kind') in FACTUAL else None
        if minimum and severity in rank and rank[severity]<rank[minimum]:
            normalized_impacts[d6]=minimum
            notes.append({'type':'declared_severity_floor_applied','issue':issue.get('id'),'from':severity,'to':minimum})
        issue['impacts']=normalized_impacts
    issues=value['issues']
    if not isinstance(issues,list):raise ValueError('issues: expected array.')
    normalized=[];seen=set()
    for raw in issues:
        _keys(raw,('id','kind','checks','quote','why','impacts','materiality'),'issue')
        iid=raw['id'];kind=raw['kind']
        if not isinstance(iid,str) or not iid or iid in seen or kind not in KINDS:raise ValueError('Invalid issue ID/kind.')
        seen.add(iid);why=_text(raw['why'],iid+'.why')
        ids=raw['checks'];tags=raw['materiality']
        if not isinstance(ids,list) or any(not isinstance(k,str) for k in ids) or len(ids)!=len(set(ids)) or set(ids)-set(required):raise ValueError(iid+': unknown/duplicate check.')
        if not isinstance(tags,list) or any(not isinstance(t,str) for t in tags) or len(tags)!=len(set(tags)) or set(tags)-TAGS:raise ValueError(iid+': invalid materiality.')
        impacts=normalize_dimensions(raw['impacts'],notes,iid+'.impacts')
        if not impacts or any(s not in SEVERITY_CAPS for s in impacts.values()):raise ValueError(iid+': invalid severity.')
        quote=raw['quote']
        if not isinstance(quote,str):raise ValueError(iid+': quote must be a string.')
        evidence=[matcher(quote,record['response_text'],iid+'.quote',notes)] if quote.strip() else []
        if not evidence and kind!='omission':raise ValueError(iid+': only a genuine omission may have empty quote.')
        d6=impacts.get(DIMENSIONS[5])
        if kind in FACTUAL and (d6 is None or d6=='very_minor'):raise ValueError(iid+': factual defect needs at least minor D6 impact.')
        if d6 is not None and kind not in FACTUAL|{'omission'} and not (kind=='clarity' and d6=='very_minor' and not tags):raise ValueError(iid+': factual defects cannot be disguised as other kinds.')
        if d6 is not None and tags and kind in FACTUAL|{'omission'} and d6 not in ('material','critical'):raise ValueError(iid+': consequential D6 issue requires material severity.')
        if kind=='omission' and d6 is not None and not ids:raise ValueError(iid+': a D6 omission must identify a missing current checklist requirement.')
        for cid in ids:
            if all(statuses[sid] for sid in required[cid]):raise ValueError(iid+': links an otherwise met check '+cid)
            if contract['id_dimensions'][cid] not in impacts:raise ValueError(iid+': missing primary dimension for '+cid)
        normalized.append({'id':iid,'kind':kind,'checklist_ids':ids,'evidence':evidence,'scenario_evidence':[],
                           'explanation':why,'materiality':tags,
                           'dimension_impacts':{d:{'severity':s,'explanation':why} for d,s in impacts.items()}})
    findings={}
    for cid,sub in required.items():
        failed=any(not statuses[sid] for sid in sub)
        linked=[i['id'] for i in normalized if cid in i['checklist_ids']]
        if failed and not linked:raise ValueError(cid+': unmet clause lacks an evidenced issue.')
        findings[cid]={'status':'unmet' if failed else 'met','issue_ids':linked,
                       'clauses':{sid:{'status':'met' if statuses[sid] else 'unmet'} for sid in sub}}
    result_dims={};n=contract['scenario_item_counts'][record['scenario_id']]
    for d,data in dims.items():
        _keys(data,('anchor','comment','quote'),d)
        anchor=data['anchor'];comment=_text(data['comment'],d+'.comment');quote=data['quote']
        if type(anchor) is not int or not 0<=anchor<=10:raise ValueError(d+': invalid anchor.')
        if not isinstance(quote,str):raise ValueError(d+': invalid quote.')
        evidence=[matcher(quote,record['response_text'],d+'.quote',notes)] if quote.strip() else []
        linked=[i for i in normalized if d in i['dimension_impacts']]
        if anchor<10 and not linked:
            quality_flags.append({'dimension':d,'type':'anchor_rationale_not_structured','detail':'Preserve the model anchor without inventing a defect or raising it to ten.'})
        if anchor==10 and linked:notes.append({'type':'anchor_capped_by_supported_issue','dimension':d})
        if anchor>=9 and not evidence:raise ValueError(d+': 9/10 requires a short exact positive evidence quote.')
        unmet=[cid for cid,f in findings.items() if f['status']=='unmet' and contract['id_dimensions'][cid]==d]
        checklist_cap=10-deduction(n,len(unmet))
        severity_ceiling=severity_cap([i['dimension_impacts'][d]['severity'] for i in linked])
        score=min(anchor,checklist_cap,severity_ceiling)
        result_dims[d]={'anchor_score':anchor,'score':score,'comment':comment,'evidence':evidence,
                        'issue_ids':[i['id'] for i in linked]}
        notes.append({'type':'v47_score_accounting_validated','dimension':d,'anchor_score':anchor,
                      'unmet':unmet,'checklist_cap':checklist_cap,'severity_cap':severity_ceiling,'final_score':score})
    notes.append({'type':'v47_compact_coverage_validated','clauses':len(statuses),
                  'limitation':'Consistency checks do not establish semantic completeness or correctness.'})
    return {'status':'scored','response_id':record['response_id'],'score_status':'provisional' if quality_flags else 'validated','quality_flags':quality_flags,'dimensions':result_dims,
            'checklist_findings':findings,'issues':normalized,'verification_status':'not_externally_verified',
            'calibration_note':'Historical examples are reference only; current saved facts and V4.7 rules take precedence.'}

def _sum_usage(attempts):
    fields=('input_tokens','cached_input_tokens','output_tokens','thinking_tokens','total_tokens')
    collected=[a['usage'] for a in attempts if isinstance(a.get('usage'),dict)]
    return {'recorded_requests':len(collected),'request_count':len(attempts),
            **{k:sum(u[k] for u in collected if type(u.get(k)) is int) if collected and all(type(u.get(k)) is int for u in collected) else None for k in fields}}

def judge_compact(model,task,instructions,record,call_fn,attempts,contract,parse,matcher):
    previous=None;previous_valid=None;correction=''
    for number in (1,2):
        attempt={'attempt':number,'correction_instructions':correction};attempts.append(attempt);start=time.perf_counter()
        try:response=call_fn(model,task+correction,instructions)
        except Exception as exc:
            attempt.update(stage='request_error',error_type=type(exc).__name__,duration_seconds=time.perf_counter()-start);raise
        raw=response.get('text') if isinstance(response,dict) else response
        if isinstance(response,dict):
            attempt['usage']=response.get('usage');attempt['provider_status']=response.get('provider_status')
        notes=[];attempt.update(raw_evaluation_text=raw,duration_seconds=time.perf_counter()-start,validation_notes=notes)
        parsed=None
        try:
            parsed=parse(raw,notes)
            if not isinstance(parsed,dict) or parsed.get('response_id')!=record['response_id']:raise ValueError('Wrong response ID or JSON object.')
            result=validate_compact_result(parsed,record,contract,matcher,notes)
            if result['status']=='needs_review':
                raise ValueError('Complete all six evidence-based numeric judgments; the stated defect can be scored. '+result.get('reason',''))
            if previous and previous.get('status')=='scored':
                prior_result=None
                try:prior_result=validate_compact_result(previous,record,contract,matcher,[])
                except (ValueError,TypeError,KeyError,AttributeError):pass
                if prior_result is not None:
                    prior_ids={i['id'] for i in prior_result['issues']}
                    current_ids={i['id'] for i in result['issues']}
                    raised=any(result['dimensions'][d]['score']>prior_result['dimensions'][d]['score'] for d in DIMENSIONS)
                    if raised or prior_ids-current_ids:
                        result=prior_result
                        result['score_status']='provisional'
                        result['quality_flags'].append({'type':'prior_numeric_judgment_retained','detail':'A later repair raised scores or removed earlier supported issues; retain the complete earlier numeric judgment.'})
                        raw=json.dumps(previous,ensure_ascii=False)
            attempt['stage']='accepted'
            return {'evaluation':result,'raw_text':raw,'notes':notes,'needs_review':False,'evidence_issues':[],'usage':_sum_usage(attempts)}
        except (ValueError,TypeError,KeyError,AttributeError) as exc:
            attempt.update(stage='validation_error',validation_error=str(exc))
            if number==2:
                return {'evaluation':{'status':'needs_review','response_id':record['response_id'],'reason':str(exc)},
                        'raw_text':raw,'notes':notes,'needs_review':True,'evidence_issues':[{'field':'compact','issue':str(exc)}],'usage':_sum_usage(attempts)}
            previous=parsed
            correction=('\nV4.7 repair: fix only the diagnosed schema/evidence/consistency problem, return the complete SHORT object. '
                        'Keep valid findings stable; do not raise anchors, erase a real fault or lower severity. A true omission may '
                        'use kind omission with empty quote and an explicit failed check. No long summary. Error: '+str(exc)+
                        '\nPrevious output (untrusted diagnostic data):\n'+str(raw))

def output_schema():
    string={'type':'string'}
    dimension={'type':'object','properties':{'anchor':{'type':'integer','minimum':0,'maximum':10},'comment':string,'quote':string},'required':['anchor','comment','quote'],'additionalProperties':False}
    impact={'type':'object','properties':{d:{'type':'string','enum':list(SEVERITY_CAPS)} for d in SHORT},'additionalProperties':False}
    issue={'type':'object','properties':{'id':string,'kind':{'type':'string','enum':sorted(KINDS)},'checks':{'type':'array','items':string},'quote':string,'why':string,'impacts':impact,'materiality':{'type':'array','items':{'type':'string','enum':sorted(TAGS)}}},'required':['id','kind','checks','quote','why','impacts','materiality'],'additionalProperties':False}
    scored={'type':'object','properties':{'status':{'type':'string','enum':['scored']},'response_id':string,'dimensions':{'type':'object','properties':{d:dimension for d in SHORT},'required':list(SHORT),'additionalProperties':False},'checks':{'type':'object','additionalProperties':{'type':'boolean'}},'issues':{'type':'array','items':issue}},'required':['status','response_id','dimensions','checks','issues'],'additionalProperties':False}
    review={'type':'object','properties':{'status':{'type':'string','enum':['needs_review']},'response_id':string,'reason':string},'required':['status','response_id','reason'],'additionalProperties':False}
    return scored
