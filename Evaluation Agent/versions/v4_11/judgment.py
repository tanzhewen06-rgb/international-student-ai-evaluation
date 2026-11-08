"""Compact V4.11 judgments: exact evidence, deterministic ceilings, bounded repair."""
import copy
import json
import time
import hashlib
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

def merge_exact_duplicates(issues,notes):
    """Only merge identical kind/quote/reason; do not guess semantic equivalence."""
    merged=[];seen={};rank={'very_minor':0,'minor':1,'material':2,'critical':3}
    def norm(s):return ' '.join(s.split()).casefold()
    for issue in issues:
        if not isinstance(issue,dict):merged.append(issue);continue
        if any(not isinstance(issue.get(k),str) for k in ('kind','quote','why')):
            merged.append(issue);continue
        key=tuple(norm(issue[k]) for k in ('kind','quote','why'))
        if key not in seen:
            seen[key]=len(merged);merged.append(copy.deepcopy(issue));continue
        target=merged[seen[key]]
        # Validate impacts/tags rather than silently discarding malformed duplicate evidence.
        impacts=normalize_dimensions(issue.get('impacts'),notes,'duplicate.impacts')
        prior=normalize_dimensions(target.get('impacts'),notes,'duplicate.prior_impacts')
        if any(s not in rank for s in list(impacts.values())+list(prior.values())):raise ValueError('Invalid duplicate severity.')
        for d,s in impacts.items():
            if d not in prior or rank[s]>rank[prior[d]]:prior[d]=s
        tags=issue.get('materiality');oldtags=target.get('materiality')
        if not isinstance(tags,list) or not isinstance(oldtags,list) or any(not isinstance(x,str) for x in tags+oldtags) :raise ValueError('Invalid duplicate materiality.')
        target['impacts']=prior;target['materiality']=sorted(set(tags)|set(oldtags))
        notes.append({'type':'exact_duplicate_defect_merged','detail':'Same kind, quoted proposition and reason; impacts retain their strongest severity.'})
    return merged

def validate_compact_result(value,record,contract,matcher,notes):
    value=copy.deepcopy(value)
    if not isinstance(value,dict):raise ValueError('Expected a scoring object.')
    if value.get('status')=='needs_review':
        return {'status':'needs_review','response_id':record['response_id'],'reason':str(value.get('reason','Complete six numeric scores.'))}
    quality_flags=[]
    # Source/issue IDs are assigned by the program; model-written IDs never gate scoring.
    if value.get('response_id') not in (None,record['response_id']):
        notes.append({'type':'model_response_id_ignored','reported':value.get('response_id')})
    value['response_id']=record['response_id'];value['status']='scored'
    dims=normalize_dimensions(value.get('dimensions'),notes,'dimensions');_keys(dims,DIMENSIONS,'dimensions')
    prefix={'scenario_1':'E','scenario_2':'L','scenario_3':'C','scenario_4':'A','scenario_5':'S'}[record['scenario_id']]
    required={cid:sub for cid,sub in contract['clause_requirements'].items() if cid.startswith(prefix)}
    order=list(required)
    supplied=value.get('checks');statuses={cid:None for cid in order}
    if isinstance(supplied,list):
        if len(supplied)==len(order):
            for cid,flag in zip(order,supplied):
                if type(flag) is bool:statuses[cid]=flag
        else:notes.append({'type':'checklist_sequence_length_recorded','expected':len(order),'received':len(supplied),'unit':'original_items'})
    elif isinstance(supplied,dict):
        for cid,flag in supplied.items():
            if cid in statuses and type(flag) is bool:statuses[cid]=flag
            else:notes.append({'type':'unmapped_check_label_ignored','label':str(cid)})
    if any(v is None for v in statuses.values()):
        quality_flags.append({'type':'checklist_coverage_incomplete','detail':'Original item coverage is incomplete; preserve numeric scores without assuming unknown items passed or failed.'})
    raw_issues=value.get('issues',[])
    if not isinstance(raw_issues,list):raise ValueError('issues: expected array.')
    raw_issues=merge_exact_duplicates(raw_issues,notes)
    value['issues']=[]
    for number,issue in enumerate(raw_issues,1):
        if not isinstance(issue,dict):raise ValueError('issue: expected object.')
        if 'id' in issue or 'checks' in issue:
            notes.append({'type':'model_issue_ids_and_links_ignored','position':number})
        issue={k:v for k,v in issue.items() if k not in ('id','checks','checklist_ids','issue_ids')}
        issue['id']=f'I{number}';issue['checks']=[]
        impacts=normalize_dimensions(issue.get('impacts'),notes,f'I{number}.impacts')
        d6=DIMENSIONS[5];severity=impacts.get(d6)
        rank={'very_minor':0,'minor':1,'material':2,'critical':3}
        minimum='material' if issue.get('materiality') and issue.get('kind') in FACTUAL|{'omission'} else 'minor' if issue.get('kind') in FACTUAL else None
        if minimum and severity in rank and rank[severity]<rank[minimum]:
            impacts[d6]=minimum
            notes.append({'type':'declared_severity_floor_applied','issue':issue['id'],'from':severity,'to':minimum})
        issue['impacts']=impacts;value['issues'].append(issue)
    issues=value['issues']
    if not isinstance(issues,list):raise ValueError('issues: expected array.')
    normalized=[];seen=set()
    for raw in issues:
        _keys(raw,('id','kind','checks','quote','why','impacts','materiality'),'issue')
        iid=raw['id'];kind=raw['kind']
        if not isinstance(iid,str) or not iid or iid in seen or kind not in KINDS:raise ValueError('Invalid issue ID/kind.')
        seen.add(iid);why=_text(raw['why'],iid+'.why')
        ids=raw['checks'];tags=raw['materiality']
        # Audit link numbering is intentionally not validated or used as a scoring gate.
        if not isinstance(tags,list) or any(not isinstance(t,str) for t in tags):raise ValueError(iid+': invalid materiality structure.')
        reported_tags=tags[:]
        canonical=list(dict.fromkeys(t.strip().lower().replace('-', '_').replace(' ', '_') for t in tags))
        unknown=[t for t in canonical if t not in TAGS]
        if unknown:
            quality_flags.append({'type':'unverified_materiality_label','issue':iid,'dimensions':list(raw['impacts']),
                                  'detail':'Unknown materiality labels retained in raw output; declared numerical ceilings are provisional, not verified.'})
        tags=[t for t in canonical if t in TAGS]
        if tags!=reported_tags:notes.append({'type':'materiality_labels_normalized','issue':iid,'reported':reported_tags,'used':tags})
        impacts=normalize_dimensions(raw['impacts'],notes,iid+'.impacts')
        if not impacts or any(s not in SEVERITY_CAPS for s in impacts.values()):raise ValueError(iid+': invalid severity.')
        quote=raw['quote']
        if not isinstance(quote,str):raise ValueError(iid+': quote must be a string.')
        evidence=[];evidence_status='verified' if quote.strip() else 'omission_not_externally_verified'
        if quote.strip():
            try:evidence=[matcher(quote,record['response_text'],iid+'.quote',notes)]
            except ValueError:
                evidence_status='unverified'
        elif kind!='omission':evidence_status='unverified'
        if evidence_status=='unverified':
            quality_flags.append({'type':'unverified_issue_evidence','issue':iid,'dimensions':list(impacts),
                                  'detail':'Defect quote is absent from the candidate. Keep declared numbers/ceilings provisional; no invented quote or automatic rejudgment.'})
            notes.append({'type':'issue_quote_not_verified','issue':iid,'reported_quote':quote})
        d6=impacts.get(DIMENSIONS[5])
        if kind in FACTUAL and (d6 is None or d6=='very_minor'):raise ValueError(iid+': factual defect needs at least minor D6 impact.')
        if d6 is not None and kind not in FACTUAL|{'omission'} and not (kind=='clarity' and d6=='very_minor' and not tags):raise ValueError(iid+': factual defects cannot be disguised as other kinds.')
        if d6 is not None and tags and kind in FACTUAL|{'omission'} and d6 not in ('material','critical'):raise ValueError(iid+': consequential D6 issue requires material severity.')
        normalized.append({'id':iid,'kind':kind,'checklist_ids':ids,'evidence':evidence,'scenario_evidence':[],
                           'explanation':why,'materiality':tags,'reported_materiality':reported_tags,
                           'evidence_status':evidence_status,'reported_quote':quote,
                           'dimension_impacts':{d:{'severity':s,'explanation':why} for d,s in impacts.items()}})
    findings={cid:{'status':'met' if statuses[cid] is True else 'unmet' if statuses[cid] is False else 'unknown','issue_ids':[]} for cid in order}
    result_dims={};n=contract['scenario_item_counts'][record['scenario_id']]
    for d,data in dims.items():
        if not isinstance(data,dict) or not {'anchor','comment'}<=set(data) or set(data)-{'anchor','comment','quote'}:
            raise ValueError(d+': expected anchor and comment.')
        anchor=data['anchor'];comment=_text(data['comment'],d+'.comment')
        if type(anchor) is not int or not 0<=anchor<=10:raise ValueError(d+': invalid anchor.')
        evidence=[]
        if 'quote' in data:notes.append({'type':'redundant_dimension_quote_ignored','dimension':d})
        linked=[i for i in normalized if d in i['dimension_impacts']]
        if anchor<8 and not linked:
            quality_flags.append({'dimension':d,'type':'low_anchor_without_supported_issue','detail':'Low anchor lacks a structured substantive defect; preserve the numeric judgment and flag its incomplete basis.'})
        if anchor==10 and linked:notes.append({'type':'anchor_capped_by_supported_issue','dimension':d})
        unmet=[cid for cid,f in findings.items() if f['status']=='unmet' and contract['id_dimensions'][cid]==d]
        checklist_cap=10-deduction(n,len(unmet))
        severity_ceiling=severity_cap([i['dimension_impacts'][d]['severity'] for i in linked])
        score=min(anchor,checklist_cap,severity_ceiling)
        result_dims[d]={'anchor_score':anchor,'score':score,'comment':comment,'evidence':evidence,
                        'score_status':'provisional' if any(f.get('dimension')==d or d in f.get('dimensions',[]) or f.get('type')=='checklist_coverage_incomplete' for f in quality_flags) else 'validated',
                        'issue_ids':[i['id'] for i in linked]}
        notes.append({'type':'v411_score_accounting_validated','dimension':d,'anchor_score':anchor,
                      'unmet':unmet,'checklist_cap':checklist_cap,'severity_cap':severity_ceiling,'final_score':score})
    notes.append({'type':'v411_compact_coverage_validated','original_items':len(statuses),
                  'limitation':'Consistency checks do not establish semantic completeness or correctness.'})
    return {'status':'scored','response_id':record['response_id'],'score_status':'provisional' if quality_flags else 'validated','quality_flags':quality_flags,'dimensions':result_dims,
            'checklist_findings':findings,'issues':normalized,'verification_status':'not_externally_verified',
            'calibration_note':'Historical examples are reference only; current saved facts and V4.11 rules take precedence.'}

def _sum_usage(attempts):
    fields=('input_tokens','cached_input_tokens','output_tokens','thinking_tokens','total_tokens')
    collected=[a['usage'] for a in attempts if isinstance(a.get('usage'),dict)]
    return {'recorded_requests':len(collected),'request_count':len(attempts),
            **{k:sum(u[k] for u in collected if type(u.get(k)) is int) if collected and all(type(u.get(k)) is int for u in collected) else None for k in fields}}

def judge_compact(model,task,instructions,record,call_fn,attempts,contract,parse,matcher):
    previous=None;previous_valid=None;correction=''
    for number in (1,2):
        attempt={'attempt':number,'correction_instructions':correction,'is_repair':number>1,'input_sha256':hashlib.sha256((task+correction).encode('utf-8')).hexdigest(),'instructions_sha256':hashlib.sha256(instructions.encode('utf-8')).hexdigest()};attempts.append(attempt);start=time.perf_counter()
        try:response=call_fn(model,task+correction,instructions)
        except Exception as exc:
            attempt.update(stage='request_error',error_type=type(exc).__name__,duration_seconds=time.perf_counter()-start);raise
        raw=response.get('text') if isinstance(response,dict) else response
        if isinstance(response,dict):
            attempt['usage']=response.get('usage');attempt['provider_status']=response.get('provider_status');attempt['provider_model']=response.get('provider_model')
        notes=[];attempt.update(raw_evaluation_text=raw,duration_seconds=time.perf_counter()-start,validation_notes=notes)
        parsed=None
        try:
            parsed=parse(raw,notes)
            if not isinstance(parsed,dict):raise ValueError('Expected a scoring object.')
            if number>1 and isinstance(previous,dict) and isinstance(previous.get('dimensions'),dict):
                initial=normalize_dimensions(previous['dimensions'],[],'initial dimensions')
                repaired=normalize_dimensions(parsed.get('dimensions'),[],'repair dimensions')
                retained=[]
                for dim,first in initial.items():
                    old_anchor=first.get('anchor') if isinstance(first,dict) else None
                    current=repaired.get(dim)
                    if type(old_anchor) is int and 0<=old_anchor<=10 and isinstance(current,dict) and type(current.get('anchor')) is int and current['anchor']>old_anchor:
                        current['anchor']=old_anchor;retained.append(dim)
                parsed['dimensions']=repaired
            else:retained=[]
            result=validate_compact_result(parsed,record,contract,matcher,notes)
            if retained:
                result['score_status']='provisional'
                result['quality_flags'].append({'type':'initial_anchors_retained_after_schema_repair','dimensions':retained,
                    'detail':'A structural repair tried to raise available initial anchors; keep their original values.'})
                for dim in retained:result['dimensions'][dim]['score_status']='provisional' 
            if result['status']=='needs_review':
                raise ValueError('Complete all six evidence-based numeric judgments; the stated defect can be scored. '+result.get('reason',''))
            if previous and previous.get('status')=='scored':
                prior_result=None
                try:prior_result=validate_compact_result(previous,record,contract,matcher,[])
                except (ValueError,TypeError,KeyError,AttributeError):pass
                if prior_result is not None:
                    prior_ids=set()
                    current_ids=set()
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
            correction=('\nV4.11 repair: fix only the diagnosed schema/evidence/consistency problem, return the complete SHORT object. '
                        'Keep valid findings stable; do not raise anchors, erase a real fault or lower severity. A true omission may '
                        'use kind omission with empty quote and an explicit failed check. No long summary. Error: '+str(exc)+
                        '\nPrevious output (untrusted diagnostic data):\n'+str(raw))

def output_schema(parent_count=None):
    if parent_count is not None and parent_count not in (3,4,5):raise ValueError('Expected 3, 4 or 5 original checklist items.')
    string={'type':'string'}
    dimension={'type':'object','properties':{'anchor':{'type':'integer','minimum':0,'maximum':10},'comment':string},'required':['anchor','comment'],'additionalProperties':False}
    impact={'type':'object','properties':{d:{'type':'string','enum':list(SEVERITY_CAPS)} for d in SHORT},'additionalProperties':False}
    issue={'type':'object','properties':{'id':string,'kind':{'type':'string','enum':sorted(KINDS)},'checks':{'type':'array','items':string},'quote':string,'why':string,'impacts':impact,'materiality':{'type':'array','items':{'type':'string','enum':sorted(TAGS)}}},'required':['id','kind','checks','quote','why','impacts','materiality'],'additionalProperties':False}
    scored={'type':'object','properties':{'status':{'type':'string','enum':['scored']},'response_id':string,'dimensions':{'type':'object','properties':{d:dimension for d in SHORT},'required':list(SHORT),'additionalProperties':False},'checks':{'type':'object','additionalProperties':{'type':'boolean'}},'issues':{'type':'array','items':issue}},'required':['status','response_id','dimensions','checks','issues'],'additionalProperties':False}
    review={'type':'object','properties':{'status':{'type':'string','enum':['needs_review']},'response_id':string,'reason':string},'required':['status','response_id','reason'],'additionalProperties':False}
    scored['properties'].pop('response_id');scored['properties'].pop('status')
    scored['required']=[k for k in scored['required'] if k not in ('response_id','status')]
    scored['properties']['checks']={'type':'array','items':{'type':'boolean'},'minItems':parent_count or 3,'maxItems':parent_count or 5}
    item=scored['properties']['issues']['items']
    item['properties'].pop('id');item['properties'].pop('checks')
    item['required']=[k for k in item['required'] if k not in ('id','checks')]
    scored['properties']={key:scored['properties'][key] for key in ('checks','issues','dimensions')}
    scored['required']=['checks','issues','dimensions']
    return scored
