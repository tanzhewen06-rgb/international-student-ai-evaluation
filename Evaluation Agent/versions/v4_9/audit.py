"""Prepare parent-item guidance and an exact output count for V4.9."""
import json,re

def prepare_audit_instructions(instructions,record,contract):
    prefix={'scenario_1':'E','scenario_2':'L','scenario_3':'C','scenario_4':'A','scenario_5':'S'}[record['scenario_id']]
    items=[{'item':cid,'requirements':list(sub.values())} for cid,sub in contract['clause_requirements'].items() if cid.startswith(prefix)]
    count=contract['scenario_item_counts'][record['scenario_id']]
    if len(items)!=count:raise ValueError('Original checklist count mismatch before request.')
    body,n=re.subn(r'<!-- evaluation-contract\s*\n.*?\n-->','',instructions,count=1,flags=re.S)
    if n!=1:raise ValueError('Expected one saved scoring contract.')
    return body+'\n\n## Current Original Checklist Items\nRead all requirements within each item; return one boolean per item, in this order.\n<checklist_output_count>'+str(count)+'</checklist_output_count>\n'+json.dumps(items,ensure_ascii=False,separators=(',',':'))+'\n'
