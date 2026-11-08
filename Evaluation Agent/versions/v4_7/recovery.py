"""Traceable numeric completion; never overwrite original scores or invent missing anchors."""
from pathlib import Path
import copy
from runtime import portable_json as json

def compatible(a,b):
    keys=('score_min','score_max','scenario_item_counts','id_dimensions','severity_caps','repetition_caps','clause_requirements')
    return all(a.get(k)==b.get(k) for k in keys)

def previous_compatible_score(root,record,contract,judge,calibration):
    from runtime.scoring import load_scoring_contract
    for mf in sorted(Path(root).rglob('manifest.json'),key=lambda p:p.stat().st_mtime,reverse=True):
        try:
            m=json.loads(mf.read_text(encoding='utf-8-sig'))
            if m.get('evaluator_model')!=judge or m.get('calibration_sha256')!=(calibration['sha256'] if calibration else None):continue
            old=load_scoring_contract((mf.parent/'rubric.md').read_text(encoding='utf-8-sig'))
            if not compatible(old,contract):continue
            file=mf.parent/m['result_file']
            if not file.is_file():continue
            for line in file.read_text(encoding='utf-8-sig').splitlines():
                row=json.loads(line)
                if row.get('response_id')!=record['response_id'] or row.get('status')!='scored':continue
                if row.get('score_status')=='provisional':continue
                from runtime.agent import canonical_hash
                if row.get('source_sha256')!=canonical_hash(record):continue
                dims=copy.deepcopy(row['dimensions'])
                for d in dims.values():d['comment']=d.get('comment') or d.get('justification','历史已验证评分。').split('\n')[0]
                return {'status':'scored','response_id':record['response_id'],'score_status':'provisional',
                        'dimensions':dims,'issues':copy.deepcopy(row.get('issues',[])),
                        'checklist_findings':copy.deepcopy(row.get('checklist_findings',{})),
                        'verification_status':'not_externally_verified',
                        'quality_flags':[{'type':'previous_compatible_judgment_reused','source_run':str(mf.parent),'source_version':m.get('rubric_version'),'detail':'No new score was fabricated; prior same-answer, same-judge, compatible-rule score is provisional.'}]}
        except (ValueError,KeyError,OSError):continue
    return None
