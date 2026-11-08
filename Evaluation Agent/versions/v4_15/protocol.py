from pathlib import Path
import hashlib
import json
import re

from runtime.agent import DIMENSIONS, student_background_context, _match_excerpt
from runtime.checklist import load_checklist, prepare_checklist
from runtime.calibration import load_calibration

VERSION = 'V4.15'
FLOW_REVISION = 'dimension_ordered'
STAGES = ('independent', 'factual', 'understanding')
STAGE_DIMENSIONS = {'independent': ['D2', 'D3', 'D4', 'D5'], 'factual': ['D6'], 'understanding': ['D1']}
ASPECTS = {'factual': 'reliability', 'understanding': 'understanding'}
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
sha_text = lambda s: hashlib.sha256(s.encode('utf-8')).hexdigest()

def section(text, start, end):
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError('Evaluation Prompt headings must occur exactly once.')
    return text.split(start, 1)[1].split(end, 1)[0].strip()

def load_protocol(rubric_file, checklist_file, calibration_file):
    text = Path(rubric_file).read_text(encoding='utf-8-sig')
    matches = re.findall(r'<!-- evaluation-contract\s*\n(.*?)\n-->', text, re.S)
    if len(matches) != 1:
        raise ValueError('Select one master Evaluation Prompt contract.')
    contract = json.loads(matches[0])
    checklist = load_checklist(checklist_file)
    calibration = load_calibration(calibration_file)
    if calibration is None or calibration.get('mode') != 'principles_only':
        raise ValueError('Select the existing principles-only calibration reference.')
    if (contract['version'] != VERSION or contract['workflow_revision'] != FLOW_REVISION
            or contract['checklist_sha256'] != checklist['sha256']):
        raise ValueError('Select matching dimension-ordered V4.15 inputs.')
    if (contract['dimension_order'] != ['D2', 'D3', 'D4', 'D5', 'D6', 'D1']
            or contract['stage_dimensions'] != STAGE_DIMENSIONS
            or contract['checklist_dimensions'] != ['D1', 'D6'] or contract['max_attempts_per_stage'] != 4):
        raise ValueError('Unexpected V4.15 flow or scoring rule.')
    for n in (3, 4, 5):
        if contract['checklist_score_table'][str(n)] != [(20 * (n - k) + n) // (2 * n) for k in range(n + 1)]:
            raise ValueError('Prompt deduction table differs from the program.')
    orders = {}
    for sid, body in checklist['sections'].items():
        ids = re.findall(r'(?m)^\|\s*([ELCAS][1-9][0-9]*)\s*\|', body)
        if len(ids) != contract['scenario_item_counts'][sid] or len(ids) != len(set(ids)):
            raise ValueError('Unexpected original Checklist item count.')
        orders[sid] = ids
    if {i for ids in orders.values() for i in ids} != set(contract['screening_requirements']):
        raise ValueError('Each Checklist item needs dimension-specific guidance.')
    headings = ['## Phase A: Independent dimensions', '## Phase B: Factual reliability',
                '## Phase C: Problem understanding', '## Score computation']
    instructions = {name: section(text, headings[i], headings[i + 1]) for i, name in enumerate(STAGES)}
    common = section(text, '## Shared judging rules', headings[0])
    anchors = section(text, '## Evaluation Dimensions and Score Anchors', '## Explicit Human Preferences')
    blocks = re.split(r'(?m)(?=^### [1-6]\. )', anchors)[1:]
    if len(blocks) != 6:
        raise ValueError('Keep all six original anchor tables.')
    for name in STAGES:
        instructions[name] = common + '\n\n' + instructions[name] + '\n\n' + '\n\n'.join(blocks[int(d[1:]) - 1].strip() for d in STAGE_DIMENSIONS[name])
    return {'contract': contract, 'checklist': checklist, 'orders': orders,
            'rubric_sha256': sha(rubric_file), 'calibration': calibration, 'phase_instructions': instructions}

def context(record):
    return {'response_id': record['response_id'], 'saved_student_background': student_background_context(record),
            'saved_scenario': record['scenario_prompt'], 'candidate_response': record['response_text']}

def phase_request(protocol, record, phase):
    if phase not in STAGES:
        raise ValueError('Select a declared evaluation phase.')
    task = {'saved_input': context(record), 'human_derived_preferences': protocol['calibration']['principles']}
    instructions = protocol['phase_instructions'][phase]
    if phase in ASPECTS:
        supplement = prepare_checklist(protocol['checklist'], record)
        aspect = ASPECTS[phase]
        task['items_in_output_order'] = [{'item': cid, 'requirement': protocol['contract']['screening_requirements'][cid][aspect]}
                                        for cid in protocol['orders'][record['scenario_id']]]
        task['checklist_use'] = {'dimension': STAGE_DIMENSIONS[phase][0], 'aspect': aspect}
        instructions += '\n\n' + supplement['instructions']
    else:
        prepare_checklist(protocol['checklist'], record)
    return json.dumps(task, ensure_ascii=False), instructions

def boolean(value):
    if type(value) is bool:
        return value
    if isinstance(value, str) and value.strip().lower() in ('true', 'false', 'met', 'unmet'):
        return value.strip().lower() in ('true', 'met')
    raise ValueError('Each Checklist aspect needs a boolean judgment.')

def parse_object(text):
    flags = []
    def pairs(values):
        obj = {}
        for key, value in values:
            if key in obj:
                if obj[key] != value:
                    raise ValueError('Conflicting duplicate JSON key: ' + key)
                flags.append({'type': 'identical_duplicate_key_merged', 'field': key})
            obj[key] = value
        return obj
    cleaned = text.strip()
    if cleaned.startswith('```') and cleaned.endswith('```'):
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)[:-3].strip()
    value = json.loads(cleaned, object_pairs_hook=pairs, parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Invalid JSON number.')))
    if not isinstance(value, dict):
        raise ValueError('Expected one JSON object.')
    return value, flags

def validate_phase(value, protocol, record, phase):
    keys = STAGE_DIMENSIONS[phase]
    dimensions = value.get('dimensions')
    if not isinstance(dimensions, dict) or set(dimensions) != set(keys):
        raise ValueError('Return only these dimension keys in this phase: ' + ', '.join(keys))
    result = {'dimensions': {}}
    flags = []
    for key in keys:
        name = DIMENSIONS[int(key[1:]) - 1]
        data = dimensions[key]
        if not isinstance(data, dict):
            raise ValueError('Each dimension must be an object.')
        score = data.get('anchor')
        if isinstance(score, str) and re.fullmatch(r'(?:10|[0-9])(?:\.0+)?', score.strip()):
            score = int(float(score))
        if type(score) is float and score.is_integer():
            score = int(score)
        if type(score) is not int or not 0 <= score <= 10:
            raise ValueError(key + ' requires an integer from zero through ten.')
        comment = data.get('comment', '')
        if not isinstance(comment, str) or not comment.strip():
            comment = ''
            flags.append({'type': 'dimension_comment_missing', 'dimension': name})
        result['dimensions'][name] = {'anchor_score': score, 'comment': comment}
    if phase == 'independent':
        if set(value) != {'dimensions'}:
            raise ValueError('Independent dimensions do not return Checklist data or other dimensions.')
        return result, flags
    ids = protocol['orders'][record['scenario_id']]
    checks = value.get('checks')
    if not isinstance(checks, list) or len(checks) != len(ids):
        raise ValueError(f'This dimension requires exactly {len(ids)} ordered Checklist judgments.')
    name = DIMENSIONS[int(keys[0][1:]) - 1]
    findings = {}
    for cid, item in zip(ids, checks):
        if not isinstance(item, dict):
            raise ValueError('Each Checklist judgment must be an object.')
        met = boolean(item.get('met'))
        reason, evidence = item.get('reason', ''), item.get('evidence', '')
        reason = reason if isinstance(reason, str) else ''
        evidence = evidence if isinstance(evidence, str) else ''
        if not reason.strip():
            flags.append({'type': 'checklist_basis_missing', 'item': cid, 'dimension': name})
        normalizations = []
        if evidence.strip():
            try:
                evidence = _match_excerpt(evidence, record['response_text'], cid + '.evidence', normalizations)
            except ValueError:
                flags.append({'type': 'checklist_quote_unverified', 'item': cid, 'dimension': name, 'reported_quote': evidence})
        findings[cid] = {'met': met, 'reason': reason, 'evidence': evidence, 'evidence_normalizations': normalizations}
    n = len(ids)
    unmet = sum(not item['met'] for item in findings.values())
    result['checklist'] = {'dimension': keys[0], 'aspect': ASPECTS[phase], 'findings': findings,
                           'item_count': n, 'unmet_count': unmet, 'checklist_score': protocol['contract']['checklist_score_table'][str(n)][unmet]}
    return result, flags

def final_dimensions(results, flags):
    ratings = {name: rating for phase in STAGES for name, rating in results[phase]['dimensions'].items()}
    caps = {DIMENSIONS[int(STAGE_DIMENSIONS[phase][0][1:]) - 1]: results[phase]['checklist']['checklist_score'] for phase in ASPECTS}
    return {name: {**ratings[name], 'checklist_cap': caps.get(name),
            'score': min(ratings[name]['anchor_score'], caps[name]) if name in caps else ratings[name]['anchor_score'],
            'score_status': 'provisional' if any(f.get('dimension') == name for f in flags) else 'validated', 'issue_ids': []}
            for name in DIMENSIONS}

def schema(stage, n):
    keys = STAGE_DIMENSIONS[stage]
    dimension = {'type': 'object', 'properties': {'anchor': {'type': 'integer', 'minimum': 0, 'maximum': 10}, 'comment': {'type': 'string'}},
                 'required': ['anchor', 'comment'], 'additionalProperties': False}
    fields = {key: dimension for key in keys}
    dimensions = {'type': 'object', 'properties': fields, 'required': keys, 'additionalProperties': False}
    properties = {}
    if stage in ASPECTS:
        row = {'type': 'object', 'properties': {'met': {'type': 'boolean'}, 'reason': {'type': 'string'}, 'evidence': {'type': 'string'}},
               'required': ['met', 'reason', 'evidence'], 'additionalProperties': False}
        properties['checks'] = {'type': 'array', 'items': row, 'minItems': n, 'maxItems': n}
    properties['dimensions'] = dimensions
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}
